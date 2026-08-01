## Context

Phase 6 introduces the Interview Agent, which generates role-specific interview questions based on job details (required skills, preferred skills, and raw description). A previous issue in Phase 5 demonstrated that `with_structured_output` can lead to silent parsing failures with local LLMs (Ollama). Therefore, the design must use explicit parsing and retry logic. 

## Goals / Non-Goals

**Goals:**
- Provide a reliable `Interview Agent` that generates structured interview questions.
- Expose the agent via `POST /api/v1/jobs/{id}/interview-questions`.
- Ensure output robustness using `PydanticOutputParser` and retry loops.
- Pre-process job descriptions with the existing `sanitize_description()` utility.
- Cache generated questions on the `jobs` document to save API costs and latency.

**Non-Goals:**
- Generating a UI for this feature (frontend changes are deferred).
- Using `with_structured_output` for LLM calls.

## Decisions

- **Parsing Pattern**: Use `PydanticOutputParser` along with `format_instructions` injected into the prompt. Rationale: Phase 5 proved this is more reliable for our chosen LLMs compared to native structured output wrappers.
- **Retry Mechanism**: If parsing fails or yields empty lists, the agent will retry exactly 1 time (matching the established pattern in prior phases). If the retry also fails or returns empty, the agent will fall back gracefully (e.g., returning partial generated questions or an empty response) to avoid excessive latency from multiple sequential LLM calls. Rationale: LLMs can occasionally return poorly formatted JSON or empty strings.
- **Caching Strategy**: Store the generated questions array on the MongoDB `jobs` collection under an `interview_questions` field. Rationale: Generating 10+ questions is slow and expensive. Caching ensures that if a user re-visits the job to practice, the questions load instantly. The tradeoff is lack of variety per job, but this is acceptable for V1.
- **Question Count Parameter**: The agent function signature is `generate_interview_questions(job_id: str, question_count: int = 10)`. The caller can override the default to request more or fewer questions. The `INTERVIEW_PROMPT` template dynamically inserts `{question_count}` and derives the split: `round(question_count * 0.7)` technical, `question_count - round(question_count * 0.7)` HR/behavioral. No numbers are hardcoded in the prompt text.
- **Question Composition**: The prompt will strictly enforce the dynamically-computed 70% technical / 30% HR split and require difficulty (`easy`, `medium`, `hard`) and `topic` tags for every question.

## Risks / Trade-offs

- **Risk**: The LLM may hallucinate topics not relevant to the job. → **Mitigation**: The prompt will strictly instruct the LLM to derive technical questions only from the `required_skills`, `preferred_skills`, and `raw_description`.
- **Risk**: Repeated practice on the same job yields identical questions due to caching. → **Mitigation**: Documented tradeoff; acceptable for now to prioritize cost/latency. A "force refresh" flag can be added later if requested.
