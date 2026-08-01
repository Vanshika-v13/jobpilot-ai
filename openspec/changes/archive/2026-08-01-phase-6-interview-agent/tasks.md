## 1. Models and Prompts

- [x] 1.0 Update `docs/database.md` — add `interview_questions` field (array of objects: question, topic, difficulty) to the jobs collection schema, documenting it as the field populated/cached by the Interview Agent.
- [x] 1.1 Update `backend/schemas/jobs.py` to add Pydantic models for `InterviewQuestion` and `InterviewQuestionsResponse`.
- [x] 1.2 Create `backend/prompts/interview_prompt.py` — use `{question_count}`, `{technical_count}`, and `{hr_count}` placeholders (no hardcoded numbers). The agent computes `technical_count = round(question_count * 0.7)` and `hr_count = question_count - technical_count` before formatting.

## 2. Agent Implementation

- [x] 2.1 Create `backend/agents/interview_agent.py` with signature `generate_interview_questions(job_id: str, question_count: int = 10)`. Pass `question_count` through to the prompt formatting.
- [x] 2.2 Implement `PydanticOutputParser` and `JsonOutputParser` with an explicit 1-time retry loop inside the agent to handle empty or invalid LLM responses, falling back gracefully if the retry also fails.
- [x] 2.3 Integrate `sanitize_description()` before feeding the raw job description to the LLM.

## 3. Endpoint and Caching

- [x] 3.1 Update `backend/api/v1/jobs.py` to add the `POST /api/v1/jobs/{id}/interview-questions` endpoint.
- [x] 3.2 Implement caching logic in the endpoint: check the MongoDB job document for an existing `interview_questions` array; return it if found, otherwise invoke the agent and update the document.

## 4. Testing

- [x] 4.1 Create `backend/tests/test_interview_agent.py` to unit test the agent's prompt generation, retry logic, and fallback handling.
- [x] 4.2 Create `backend/tests/test_interview_endpoint.py` to test the new API endpoint, including cache hits and misses.
- [x] 4.3 Run the full pytest suite to verify no regressions.

