"""
Ranking prompt used by generate_explanation() in ranking_agent.py.
"""

RANKING_PROMPT = """You are a job-relevance assistant. Given the job details and a candidate's skills, write a concise 1–2 sentence explanation of why this job is or isn't a good match.

Job Role: {job_role}
Job Required Skills: {job_skills}
Candidate Skills: {user_skills}
Relevance Score: {score}/100

Respond with only the explanation sentences. Do not include any preamble or labels."""
