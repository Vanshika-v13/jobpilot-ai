import json
import logging
from datetime import datetime, timezone
from urllib.parse import quote, urlencode

import httpx
from tools.utils import random_delay

logger = logging.getLogger(__name__)

# Unstop public search API endpoint (powers the Angular SPA frontend)
UNSTOP_API_URL = "https://unstop.com/api/public/opportunity/search-new"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)


def build_unstop_url(role: str, location: str) -> str:
    """
    Constructs a human-readable search URL for Unstop jobs (used for
    the ``url`` fallback when a listing has no ``seo_url``).
    """
    role_encoded = quote(role.strip())
    location_encoded = quote(location.strip())

    params = []
    if role_encoded:
        params.append(f"searchTerm={role_encoded}")
    if location_encoded:
        params.append(f"location={location_encoded}")

    query_str = "&".join(params)
    if query_str:
        return f"https://unstop.com/jobs?{query_str}"
    return "https://unstop.com/jobs"


def _build_api_params(role: str, location: str, per_page: int) -> dict:
    """Build query parameters for the Unstop public search API."""
    params: dict = {
        "opportunity": "jobs",
        "oppstatus": "open",
        "per_page": per_page,
        "page": 1,
    }
    if role.strip():
        params["searchTerm"] = role.strip()
    if location.strip():
        params["city"] = location.strip()
    return params


def _extract_salary(job_detail: dict) -> str | None:
    """Build a human-readable salary string from the API's jobDetail block."""
    if not job_detail.get("show_salary"):
        return None
    min_sal = job_detail.get("min_salary")
    max_sal = job_detail.get("max_salary")
    currency = job_detail.get("currency", "")
    pay_in = job_detail.get("pay_in", "")
    if min_sal is None and max_sal is None:
        return None
    symbol = "₹" if "rupee" in currency else currency
    parts = []
    if min_sal is not None:
        parts.append(str(min_sal))
    if max_sal is not None and max_sal != min_sal:
        parts.append(str(max_sal))
    salary = f"{symbol}{' - '.join(parts)}"
    if pay_in:
        salary += f" ({pay_in})"
    return salary


def _extract_listing(item: dict, search_url: str) -> dict:
    """
    Convert a single Unstop API item into a normalised result dict.

    Because Unstop returns structured JSON (not raw HTML), the result
    includes ``"structured": True`` and pre-extracted top-level fields
    (title, company, location, salary, skills, description) so the
    Extraction Agent can skip LLM parsing and apply direct field mapping.

    The full API blob is still available in ``raw_html`` (serialised
    JSON) for any downstream consumer that needs additional fields.
    """
    # Canonical URL
    seo_url = item.get("seo_url", "")
    public_url = item.get("public_url", "")
    if seo_url:
        full_url = seo_url
    elif public_url:
        full_url = f"https://unstop.com/{public_url}"
    else:
        full_url = search_url

    # Pre-extract structured fields for direct mapping
    organisation = item.get("organisation", {})
    job_detail = item.get("jobDetail", {})
    locations = job_detail.get("locations", [])
    if not locations:
        # Fallback to the locations array at the item level
        locations = [loc.get("city", "") for loc in item.get("locations", []) if loc.get("city")]
    skills = [s.get("skill_name", s.get("skill", ""))
              for s in item.get("required_skills", [])]

    return {
        "source": "unstop",
        "structured": True,
        "title": item.get("title", ""),
        "company": organisation.get("name", ""),
        "location": ", ".join(locations) if locations else "",
        "salary": _extract_salary(job_detail),
        "skills": skills,
        "description": item.get("details", ""),
        "raw_html": json.dumps(item, ensure_ascii=False),
        "url": full_url,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


async def scrape_unstop(role: str, location: str, max_results: int = 20) -> list[dict]:
    """
    Fetches job/internship listings from Unstop's public search API.

    Uses the same JSON endpoint that powers the Unstop Angular frontend,
    bypassing the need for browser-based DOM scraping entirely.

    Returns a list of dicts (note ``structured: True`` — unlike
    Internshala/Wellfound, the fields are already extracted):
    [
        {
            "source": "unstop",
            "structured": true,
            "title": "Backend Developer",
            "company": "Acme Corp",
            "location": "Bangalore",
            "salary": "₹20000 - 30000 (monthly)",
            "skills": ["Python", "Django"],
            "description": "<p>Full JD HTML...</p>",
            "raw_html": "<full API JSON blob>",
            "url": "https://unstop.com/jobs/...",
            "scraped_at": "2026-07-25T17:20:00+00:00"
        }
    ]
    """
    results: list[dict] = []
    search_url = build_unstop_url(role, location)

    try:
        # Rate-limit: polite delay before hitting the API
        await random_delay(1.0, 2.5)

        params = _build_api_params(role, location, per_page=max_results)
        api_url = f"{UNSTOP_API_URL}?{urlencode(params)}"

        logger.info(f"Fetching Unstop API: {api_url}")

        async with httpx.AsyncClient(
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "application/json",
                "Referer": "https://unstop.com/jobs",
            },
            timeout=30.0,
            follow_redirects=True,
        ) as client:
            resp = await client.get(api_url)
            resp.raise_for_status()
            # Explicitly set UTF-8 encoding before .json() — httpx's
            # auto-detection can misinterpret multi-byte chars (e.g. ₹)
            # when the server omits charset in Content-Type.
            resp.encoding = "utf-8"
            payload = resp.json()

        # The API wraps listings in  data -> data  (paginated Laravel response)
        items = payload.get("data", {}).get("data", [])

        if not items:
            logger.warning("Unstop API returned 0 listings for query: "
                           f"role={role!r}, location={location!r}")
            return []

        for item in items[:max_results]:
            try:
                results.append(_extract_listing(item, search_url))
            except Exception as item_err:
                logger.warning(f"Error processing Unstop API item: {item_err}")
                continue

    except Exception as e:
        logger.error(f"Error fetching Unstop API ({search_url}): {e}")
        return []

    logger.info(f"Unstop: fetched {len(results)} listings")
    return results
