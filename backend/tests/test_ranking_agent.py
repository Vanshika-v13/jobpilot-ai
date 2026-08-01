"""
Tests for backend/agents/ranking_agent.py
Covers task 7.2 and the skill-normalisation requirement from task 3.3.
"""

import pytest
from unittest.mock import MagicMock, patch

from agents.ranking_agent import (
    normalize_skill,
    compute_score,
    rank_jobs,
)


# ---------------------------------------------------------------------------
# normalize_skill
# ---------------------------------------------------------------------------

class TestNormalizeSkill:
    """Unit tests for the normalize_skill helper."""

    def test_lowercase_and_strip(self):
        assert normalize_skill("  Python  ") == "python"

    def test_react_js_equals_react(self):
        """'React.js' (job listing) must match 'React' (user profile)."""
        assert normalize_skill("React.js") == normalize_skill("React")

    def test_reactjs_equals_react(self):
        assert normalize_skill("ReactJS") == normalize_skill("React")

    def test_js_equals_javascript(self):
        assert normalize_skill("JS") == "javascript"
        assert normalize_skill("JavaScript") == "javascript"

    def test_nodejs_variants(self):
        assert normalize_skill("Node.js") == normalize_skill("NodeJS")
        assert normalize_skill("node") == normalize_skill("Node.js")

    def test_typescript_alias(self):
        assert normalize_skill("TS") == "typescript"

    def test_unknown_skill_lowercased(self):
        """Skills with no alias should be returned lowercased."""
        assert normalize_skill("PyTorch") == "pytorch"

    def test_internal_whitespace_collapsed(self):
        assert normalize_skill("machine  learning") == "machine learning"


# ---------------------------------------------------------------------------
# compute_score — skill component
# ---------------------------------------------------------------------------

class TestComputeScoreSkills:
    """Tests for the skill-overlap component (0–40 pts)."""

    def _job(self, skills):
        return {
            "required_skills": skills,
            "experience_required": "0-2 years",
            "location": "Remote",
            "role": "Software Engineer",
        }

    def _profile(self, skills):
        return {
            "skills": skills,
            "experience_years": 1,
            "preferred_location": "Remote",
            "preferred_roles": ["Software Engineer"],
        }

    def test_perfect_skill_match_gives_40_pts(self):
        job = self._job(["Python", "FastAPI", "PostgreSQL"])
        profile = self._profile(["Python", "FastAPI", "PostgreSQL"])
        # skill component only: remove experience/location/role contributions
        # We check the full score ≥ 40; isolate by zeroing other components.
        job_no_loc = {**job, "location": "Somewhere Unknown"}
        profile_no_loc = {**profile, "preferred_location": "", "preferred_roles": [], "experience_years": 5}
        score = compute_score(job_no_loc, profile_no_loc)
        assert score == 40  # only skill component fires

    def test_zero_skill_overlap_gives_0_skill_pts(self):
        job = self._job(["Rust", "Go"])
        profile = self._profile(["Python", "Django"])
        job_no_loc = {**job, "location": "Somewhere Unknown"}
        profile_no_loc = {**profile, "preferred_location": "", "preferred_roles": [], "experience_years": 5}
        score = compute_score(job_no_loc, profile_no_loc)
        assert score == 0

    def test_normalization_react_js_matches_react(self):
        """'React.js' in the job listing should match 'React' in the profile."""
        job = self._job(["React.js", "TypeScript"])
        profile = self._profile(["React", "TypeScript"])
        # Isolate skill score by keeping other dimensions neutral
        job_isolated = {**job, "location": "Somewhere Unknown", "role": "Unrelated"}
        profile_isolated = {**profile, "preferred_location": "", "preferred_roles": [], "experience_years": 5}
        score = compute_score(job_isolated, profile_isolated)
        # Both skills match → full 40 pts
        assert score == 40

    def test_partial_skill_match(self):
        """2 of 4 job skills matched → 20 pts skill component."""
        job = self._job(["Python", "FastAPI", "Redis", "Kafka"])
        profile = self._profile(["Python", "FastAPI"])
        job_isolated = {**job, "location": "Somewhere Unknown", "role": "Unrelated"}
        profile_isolated = {**profile, "preferred_location": "", "preferred_roles": [], "experience_years": 5}
        score = compute_score(job_isolated, profile_isolated)
        assert score == 20  # 2/4 * 40


# ---------------------------------------------------------------------------
# compute_score — experience component
# ---------------------------------------------------------------------------

class TestComputeScoreExperience:
    """Tests for experience parsing and scoring."""

    def _base_job(self, experience_required):
        return {
            "required_skills": [],
            "experience_required": experience_required,
            "location": "Somewhere Unknown",
            "role": "Unrelated",
        }

    def _base_profile(self, experience_years):
        return {
            "skills": [],
            "experience_years": experience_years,
            "preferred_location": "",
            "preferred_roles": [],
        }

    def test_range_0_2_fresher_matches(self):
        score = compute_score(self._base_job("0-2 years"), self._base_profile(1))
        assert score == 20

    def test_fresher_label(self):
        score = compute_score(self._base_job("Fresher"), self._base_profile(0))
        assert score == 20

    def test_na_experience(self):
        score = compute_score(self._base_job("NA"), self._base_profile(5))
        assert score == 10  # unknown → partial credit

    def test_within_1_yr_of_range(self):
        score = compute_score(self._base_job("2-4 years"), self._base_profile(1))
        assert score == 10  # 1 is one year below range min

    def test_far_out_of_range(self):
        score = compute_score(self._base_job("5-8 years"), self._base_profile(1))
        assert score == 0


# ---------------------------------------------------------------------------
# compute_score — location component
# ---------------------------------------------------------------------------

class TestComputeScoreLocation:
    """Tests for location matching."""

    def _job(self, location):
        return {
            "required_skills": [],
            "experience_required": "NA",
            "location": location,
            "role": "Unrelated",
        }

    def _profile(self, preferred_location):
        return {
            "skills": [],
            "experience_years": 0,
            "preferred_location": preferred_location,
            "preferred_roles": [],
        }

    def test_remote_always_matches(self):
        score = compute_score(self._job("Remote"), self._profile("Bangalore"))
        assert score >= 20

    def test_exact_city_match(self):
        score = compute_score(self._job("Bangalore"), self._profile("Bangalore"))
        assert score >= 20

    def test_no_location_match(self):
        score = compute_score(self._job("Delhi"), self._profile("Mumbai"))
        # No location pts; experience is 10 (NA); skill and role are 0
        assert score == 10


# ---------------------------------------------------------------------------
# rank_jobs
# ---------------------------------------------------------------------------

class TestRankJobs:
    """Integration-level tests for rank_jobs."""

    def _make_job(self, role, skills, location="Remote", exp="0-2 years"):
        return {
            "role": role,
            "required_skills": skills,
            "location": location,
            "experience_required": exp,
        }

    def _profile(self):
        return {
            "skills": ["Python", "FastAPI"],
            "experience_years": 1,
            "preferred_location": "Remote",
            "preferred_roles": ["Backend Developer"],
        }

    @patch("agents.ranking_agent.generate_explanation", return_value="mocked explanation")
    def test_sorted_descending_by_score(self, _mock_explain):
        jobs = [
            self._make_job("Data Analyst", ["Excel", "SQL"]),
            self._make_job("Backend Developer", ["Python", "FastAPI"]),
            self._make_job("Designer", ["Figma"]),
        ]
        ranked = rank_jobs(jobs, self._profile())
        scores = [j["relevance_score"] for j in ranked]
        assert scores == sorted(scores, reverse=True)

    @patch("agents.ranking_agent.generate_explanation", return_value="mocked explanation")
    def test_explanation_populated(self, _mock_explain):
        jobs = [self._make_job("Backend Developer", ["Python", "FastAPI"])]
        ranked = rank_jobs(jobs, self._profile())
        assert ranked[0]["explanation"] == "mocked explanation"

    def test_empty_job_list(self):
        assert rank_jobs([], self._profile()) == []
