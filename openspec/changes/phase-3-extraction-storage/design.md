## Context

In Phase 2, scrapers were implemented for Internshala and Unstop. The Internshala scraper returns raw HTML blobs, whereas the Unstop scraper returns pre-structured JSON along with a `"structured": true` flag. 

Phase 3 introduces the Extraction Agent (`backend/agents/extraction_agent.py`) to process and normalize these raw outputs into the standard `jobs` collection schema. It also establishes the database access functions using Motor to write these jobs and manage `job_searches` records.

## Goals / Non-Goals

**Goals:**
- Implement `ExtractionAgent` to normalize raw scraping inputs from both Internshala and Unstop.
- Process Unstop data using direct Python-based field mapping (no LLM call) when `structured: True` is present.
- Process Internshala data using LLM-based structured extraction via LangChain (supporting Ollama/Gemini based on project configuration).
- Standardize all job outputs to the `jobs` schema specified in `docs/database.md`.
- Save normalized jobs to the MongoDB `jobs` collection asynchronously via Motor.
- Create and update records in the `job_searches` collection linking jobs to their search metadata.
- Handle only `internshala` and `unstop` as valid source values (Wellfound is completely excluded).
- Write automated tests under `backend/tests/` to verify normalization and persistence.

**Non-Goals:**
- Implement any API endpoints for search (Phase 4 responsibility).
- Implement job ranking or scoring against profiles (Phase 4 responsibility).
- Implement any frontend UI changes.

## Decisions

### 1. Extraction Path Branching
- **Decision**: Inspect the input payload for the `structured` flag (set to `True` for Unstop). 
- **Rationale**: If `structured` is true, the fields are already parsed and extracted by the scraper layer. Direct dictionary mapping avoids expensive and slow LLM calls, saving time and compute. For Internshala, the LLM will parse the raw HTML.

### 2. LLM-Based Extraction via LangChain Structured Output
- **Decision**: Use LangChain's `with_structured_output` with a Pydantic schema for the LLM extraction path.
- **Rationale**: Ensures the local Ollama (or fallback Gemini) model returns a valid JSON matching the required schema. We will define a Pydantic model for the job details to ensure typing constraints are met before inserting into the database.

### 3. Pydantic Model for Job Extraction
The Extraction Agent will use a Pydantic model representing the subset of fields extracted from raw HTML:
```python
from pydantic import BaseModel, Field
from typing import List, Optional

class ExtractedJob(BaseModel):
    company: str
    role: str
    location: str
    salary: str = "Not disclosed"
    posted_date: Optional[str] = None
    required_skills: List[str] = Field(default_factory=list)
    preferred_skills: List[str] = Field(default_factory=list)
    raw_description: str
    experience_required: str = "Not disclosed"
    job_type: str = "full-time"  # 'full-time', 'part-time', 'contract', 'internship'
```

### 4. Database Access Layer
- **Decision**: Create `backend/database/collections.py` containing operations for `jobs` and `job_searches`.
- **Rationale**: Keeps database queries modular and typed, isolated from the agent logic, making unit testing with a mock or test database straightforward.

## Risks / Trade-offs

- **[Risk]** Local Ollama model latency and extraction quality.
  - *Mitigation*: Fallback to Gemini if `LLM_PROVIDER` is set to `gemini` or if Ollama is unavailable. Use a system prompt optimized for smaller models (e.g., Llama 3 or Mistral).
- **[Risk]** HTML formats changing on Internshala.
  - *Mitigation*: The extraction relies on passing the relevant text blocks or the full body to the LLM, making it more resilient to minor HTML tag/class changes compared to fragile CSS selectors.
