"""
Ranking Agent — Phase 4
Scores and explains job relevance against a user profile.
"""

from __future__ import annotations

import re
from typing import Any

from agents.llm_provider import get_llm
from prompts.ranking_prompt import RANKING_PROMPT

# ---------------------------------------------------------------------------
# Skill normalisation
# ---------------------------------------------------------------------------

# Alias table: maps every known variant to a single canonical form.
# Keys are already lower-cased / stripped so lookups are O(1).
_SKILL_ALIASES: dict[str, str] = {
    # JavaScript
    "js": "javascript",
    "javascript": "javascript",
    # React
    "react": "react",
    "reactjs": "react",
    "react.js": "react",
    "react js": "react",
    # TypeScript
    "ts": "typescript",
    "typescript": "typescript",
    # Node
    "node": "nodejs",
    "nodejs": "nodejs",
    "node.js": "nodejs",
    "node js": "nodejs",
    # Vue
    "vue": "vue",
    "vuejs": "vue",
    "vue.js": "vue",
    # Angular
    "angular": "angular",
    "angularjs": "angular",
    "angular.js": "angular",
    # Next
    "next": "nextjs",
    "nextjs": "nextjs",
    "next.js": "nextjs",
    # Express
    "express": "express",
    "expressjs": "express",
    "express.js": "express",
    # MongoDB
    "mongo": "mongodb",
    "mongodb": "mongodb",
    # PostgreSQL
    "postgres": "postgresql",
    "postgresql": "postgresql",
    # Machine Learning
    "ml": "machine learning",
    "machine learning": "machine learning",
    # Artificial Intelligence
    "ai": "artificial intelligence",
    "artificial intelligence": "artificial intelligence",
    # Python (no common alias, but include identity)
    "python": "python",
    # CSS preprocessors
    "sass": "sass",
    "scss": "sass",
}


def normalize_skill(s: str) -> str:
    """Lowercase, strip whitespace, collapse internal spaces, then resolve
    known aliases to a canonical form.

    Examples::

        normalize_skill("React.js")  -> "react"
        normalize_skill("  JS ")     -> "javascript"
        normalize_skill("Pytorch")   -> "pytorch"  (no alias, returned lowered)
    """
    cleaned = re.sub(r"\s+", " ", s.strip().lower())
    return _SKILL_ALIASES.get(cleaned, cleaned)


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def _parse_experience_range(experience_required: str) -> tuple[float, float] | None:
    """Return (min_years, max_years) or None if unparseable / irrelevant."""
    text = (experience_required or "").strip().lower()
    if not text or text in ("na", "n/a", "not specified", ""):
        return None
    if "fresher" in text or "0 year" in text:
        return (0.0, 0.0)
    # Match patterns like "0-2 years", "2 to 4 years", "3+ years"
    match = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)", text)
    if match:
        return (float(match.group(1)), float(match.group(2)))
    match = re.search(r"(\d+(?:\.\d+)?)\+", text)
    if match:
        lo = float(match.group(1))
        return (lo, lo + 10)  # treat "3+" as 3–13
    match = re.search(r"(\d+(?:\.\d+)?)", text)
    if match:
        val = float(match.group(1))
        return (val, val)
    return None


def _skill_score(job: dict[str, Any], profile: dict[str, Any]) -> int:
    """0–40 pts based on normalised skill overlap."""
    job_skills: list[str] = job.get("required_skills", []) or []
    user_skills: list[str] = profile.get("skills", []) or []

    norm_job = {normalize_skill(s) for s in job_skills}
    norm_user = {normalize_skill(s) for s in user_skills}

    overlap = len(norm_job & norm_user)
    denominator = max(len(norm_job), 1)
    return min(int(overlap / denominator * 40), 40)


def _experience_score(job: dict[str, Any], profile: dict[str, Any]) -> int:
    """0, 10, or 20 pts based on experience match."""
    exp_range = _parse_experience_range(job.get("experience_required", ""))
    if exp_range is None:
        return 10  # unknown → partial credit

    user_exp: float = float(profile.get("experience_years", 0) or 0)
    lo, hi = exp_range

    if lo <= user_exp <= hi:
        return 20
    if (lo - 1) <= user_exp <= (hi + 1):
        return 10
    return 0


def _location_score(job: dict[str, Any], profile: dict[str, Any]) -> int:
    """0, 10, or 20 pts based on location match."""
    job_loc = (job.get("location") or "").strip().lower()
    user_loc = (profile.get("preferred_location") or "").strip().lower()

    if not job_loc or not user_loc:
        return 0
    if "remote" in job_loc:
        return 20
    if job_loc == user_loc:
        return 20
    # Same state heuristic: last comma-separated token (e.g. "Pune, Maharashtra")
    job_state = job_loc.split(",")[-1].strip()
    user_state = user_loc.split(",")[-1].strip()
    if job_state and job_state == user_state:
        return 10
    return 0


def _role_score(job: dict[str, Any], profile: dict[str, Any]) -> int:
    """0 or 20 pts based on token overlap between job role and preferred roles."""
    job_role = (job.get("role") or "").lower()
    preferred_roles: list[str] = profile.get("preferred_roles", []) or []

    job_tokens = set(re.split(r"\W+", job_role)) - {""}
    for role in preferred_roles:
        role_tokens = set(re.split(r"\W+", role.lower())) - {""}
        if job_tokens & role_tokens:
            return 20
    return 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_score(job: dict[str, Any], profile: dict[str, Any]) -> int:
    """Return a relevance score in [0, 100] for *job* against *profile*.

    Component breakdown:
    - Skill overlap   : 0–40 pts  (normalised, alias-aware)
    - Experience match: 0–20 pts
    - Location match  : 0–20 pts
    - Role alignment  : 0–20 pts
    """
    return (
        _skill_score(job, profile)
        + _experience_score(job, profile)
        + _location_score(job, profile)
        + _role_score(job, profile)
    )


def generate_explanation(job: dict[str, Any], profile: dict[str, Any], score: int) -> str:
    """Call the local Ollama LLM to produce a 1–2 sentence explanation.

    Falls back to a generic string if the LLM is unavailable.
    """
    try:
        llm = get_llm()
        prompt = RANKING_PROMPT.format(
            job_role=job.get("role", "Unknown"),
            job_skills=", ".join(job.get("required_skills", [])),
            user_skills=", ".join(profile.get("skills", [])),
            score=score,
        )
        response = llm.invoke(prompt)
        # LangChain returns an AIMessage; extract string content
        return response.content if hasattr(response, "content") else str(response)
    except Exception:
        return (
            f"This role scored {score}/100 based on your skills, experience, "
            "location, and preferred roles."
        )


def rank_jobs(jobs: list[dict[str, Any]], profile: dict[str, Any]) -> list[dict[str, Any]]:
    """Annotate each job with *relevance_score* and *explanation*, then sort
    descending.  Explanation is only generated for the top 20 jobs.
    Scores are **not** written to MongoDB here.
    """
    if not jobs:
        return []

    # Score all jobs
    for job in jobs:
        job["relevance_score"] = compute_score(job, profile)

    # Sort descending
    ranked = sorted(jobs, key=lambda j: j["relevance_score"], reverse=True)

    # Generate explanations only for the top 20
    for job in ranked[:20]:
        job["explanation"] = generate_explanation(job, profile, job["relevance_score"])
    for job in ranked[20:]:
        job.setdefault("explanation", "")

    return ranked
