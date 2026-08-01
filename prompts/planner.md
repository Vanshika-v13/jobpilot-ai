# Planner Agent Prompt

<!-- System prompt for the Planner Agent — orchestrates multi-step job application workflows -->

## Input Contract
The Planner Agent takes the following parameters:
- `role` (str): The targeted job role (e.g. "Software Engineer")
- `location` (str): Target location or "Remote"
- `experience` (str): Required experience range (e.g. "0-2 years")
- `skills` (list[str]): List of skills to search for
- `source` (str): The portal source, one of: `"internshala"`, `"unstop"`, or `"all"`

## Output Contract
Returns a list of `SearchPlan` objects, where each plan is structured as:
```json
{
  "portal": "internshala" | "unstop",
  "role": "...",
  "location": "...",
  "experience": "...",
  "skills": ["..."]
}
```

## Behavior
- If `source` is `"internshala"`, exactly one plan for the `"internshala"` portal is generated.
- If `source` is `"unstop"`, exactly one plan for the `"unstop"` portal is generated.
- If `source` is `"all"`, two plans are generated, one for each portal.
- This is a deterministic, rule-based node in Phase 4.
