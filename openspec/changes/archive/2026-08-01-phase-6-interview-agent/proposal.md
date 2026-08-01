## Why

This change implements Phase 6 of the development cycle, introducing an Interview Agent that generates role-specific interview questions for a selected job. This allows users to practice for interviews using real requirements extracted from job descriptions, providing actionable value from the scraped data.

## What Changes

- Add a new `Interview Agent` (`backend/agents/interview_agent.py`) to generate technical and HR/behavioral interview questions based on job details.
- Implement the `POST /api/v1/jobs/{id}/interview-questions` endpoint.
- Parse LLM responses using `PydanticOutputParser` with `format_instructions` and retry logic (avoiding `with_structured_output` to prevent silent failures).
- Generate a configurable number of questions (default 10), split roughly 70% technical and 30% HR/behavioral.
- Tag each question with a topic and difficulty level (easy, medium, hard).
- Apply the existing `sanitize_description()` safety check before feeding job data to the LLM.
- **Caching Decision**: Interview questions will be **cached** on the job document. 
  - *Tradeoff*: Caching saves LLM costs and reduces latency for repeated views of the same job. The downside is that users cannot get a fresh set of questions if they want to practice again for the exact same job. A "regenerate" parameter could be added in the future, but caching is the safer default to prevent excessive LLM API usage.

## Capabilities

### New Capabilities
- `interview-generation`: Capable of taking a job ID, fetching the job, extracting skills/description, and using an LLM to reliably generate structured, categorized interview questions.

### Modified Capabilities


## Impact

- `backend/agents/`: Adds `interview_agent.py`.
- `backend/api/v1/jobs.py`: Adds the new endpoint.
- `backend/schemas/jobs.py`: Adds response models for interview questions.
- `backend/tests/`: Adds new test coverage for the Interview Agent and endpoint.
