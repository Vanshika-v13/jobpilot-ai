import logging
from datetime import datetime, timezone
from urllib.parse import quote

from playwright.async_api import async_playwright
from tools.utils import random_delay
from core.config import settings

logger = logging.getLogger(__name__)

# Primary & fallback CSS selectors verified for Internshala listing cards
INTERNSHALA_CARD_SELECTORS = [
    "div.individual_internship",
    "div.container-fluid.individual_internship",
    "div[data-href]",
    "div.internship_meta",
]

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/122.0.0.0 Safari/537.36"
)

def build_internshala_url(role: str, location: str) -> str:
    """
    Constructs a search URL for Internshala internships/jobs.

    Uses Internshala's keyword search path (``keywords-<term>``) combined
    with the ``-in-<location>`` suffix.  This ensures free-text queries
    like "python developer" are sent to the server as a keyword filter
    rather than being treated as a (non-existent) category slug, which
    Internshala silently ignores and falls back to generic results.
    """
    role_slug = role.strip().lower().replace(" ", "-") if role else ""
    loc_slug = location.strip().lower().replace(" ", "-") if location else ""

    if role_slug and loc_slug:
        return f"https://internshala.com/internships/keywords-{quote(role_slug)}-in-{quote(loc_slug)}/"
    elif role_slug:
        return f"https://internshala.com/internships/keywords-{quote(role_slug)}/"
    elif loc_slug:
        return f"https://internshala.com/internships/matching-preference-in-{quote(loc_slug)}/"
    return "https://internshala.com/internships/"

async def scrape_internshala(role: str, location: str, max_results: int = 20) -> list[dict]:
    """
    Scrapes raw job/internship listings from Internshala matching role and location.
    
    Returns a list of dicts:
    [
        {
            "source": "internshala",
            "raw_html": "<div class='individual_internship'>...</div>",
            "url": "https://internshala.com/internship/detail/...",
            "scraped_at": "2026-07-25T17:20:00Z"
        }
    ]
    """
    results = []
    search_url = build_internshala_url(role, location)
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=settings.headless)
            context = await browser.new_context(
                user_agent=USER_AGENT,
                viewport={"width": 1280, "height": 800}
            )
            page = await context.new_page()
            
            # Apply rate limiting delay before navigation
            await random_delay(1.5, 3.5)
            
            logger.info(f"Navigating to Internshala search URL: {search_url}")
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            
            # Additional small delay for DOM elements to stabilize
            await random_delay(1.0, 2.0)
            
            # Find listing cards
            card_elements = []
            for selector in INTERNSHALA_CARD_SELECTORS:
                elements = await page.query_selector_all(selector)
                if elements:
                    card_elements = elements
                    break
            
            for el in card_elements[:max_results]:
                try:
                    raw_html = await el.inner_html()
                    
                    # Extract detail URL if present
                    data_href = await el.get_attribute("data-href")
                    if not data_href:
                        anchor = await el.query_selector("a.view_detail_button, a.job-title-href, a[href*='/detail/']")
                        if anchor:
                            data_href = await anchor.get_attribute("href")
                    
                    if data_href and not data_href.startswith("http"):
                        full_url = f"https://internshala.com{data_href}"
                    elif data_href:
                        full_url = data_href
                    else:
                        full_url = search_url
                        
                    results.append({
                        "source": "internshala",
                        "raw_html": raw_html.strip(),
                        "url": full_url,
                        "scraped_at": datetime.now(timezone.utc).isoformat()
                    })
                except Exception as el_err:
                    logger.warning(f"Error parsing Internshala card element: {el_err}")
                    continue
                    
            await browser.close()
    except Exception as e:
        logger.error(f"Error scraping Internshala ({search_url}): {e}")
        return []
        
    return results
