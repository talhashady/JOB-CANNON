# Architecture

## Topology (Manager + Handoff hybrid)

```
User Profile / CV Upload
       |
       v
[Career Orchestrator]  <-- Profile Integrity Monitor (passive guardrail)
       |
       v
[Scraping Agent] --> [Verification Agent]
       |
       v
[Matching Agent] --> Ranked Recommendations
       |
  (user selects job)
       |
  +----+----+
  |         |
  v         v
[Resume   [Cover Letter
 Agent]    Agent]
  |         |
  +----+----+
       |
       v
[Application Agent] --> dry-run submission (rate limited)
       |
       v
[Tracking Agent] --> status monitoring
       |
       v
[Skill-Gap & Interview Agent] --> roadmap + mock interview
```

The **Career Orchestrator** is the single entry point. It owns session context
(`ProfileContext`) and hands off ownership to specialist agents stage by stage, while
retaining state across the journey.

## Package layout

```
src/career_assistant/
  config.py            # env-driven settings (dataclass, dotenv)
  logging_config.py    # structured logging setup
  models/              # pydantic domain models (Job, Profile, Application, ...)
  storage/             # SQLite repositories (pluggable to Postgres)
  tools/               # function tools: jobspy scraper, match score, cv parse, ...
  guardrails/          # PII scrub, completeness, factual accuracy, ATS, rate limit
  agents/              # base LLM abstraction + 8 specialist agents + orchestrator
  pipeline.py          # end-to-end pipeline runner (ties agents together)
  api/app.py           # FastAPI gateway
  cli.py               # command-line entry point
```

## Agent abstraction

Every agent extends `agents.base.BaseAgent`. Each agent declares:
- `name`, `instructions`, `model`
- a deterministic `_fallback(...)` implementation used when no LLM is configured
- an optional `_llm(...)` path that calls the model with the same contract

`BaseAgent.act(...)` picks the LLM path when `settings.llm_enabled` is true, otherwise the
fallback. This means the **entire pipeline is testable and runnable offline**, and upgrading
to live models is a config flag, not a rewrite. The structure mirrors the OpenAI Agents SDK
(`Agent`, `Runner`, `function_tool`, `handoff`); see `docs/OPENAI_SDK_MAPPING.md` for the
one-to-one mapping and a drop-in SDK adapter.

## State management

`ProfileContext` (in `models/profile.py`) is the session object persisted through the run:
`user_id`, `profile_data`, `job_queue`, `match_scores`, `application_status`, `agent_chain`,
`timestamps`. In local mode it lives in SQLite; the repository interface is intentionally
thin so Redis/Postgres can back it in production.

## Guardrails

| Guardrail | Type | Enforced at |
|---|---|---|
| PII scrubber | input | before any model/tool sees CV text |
| Profile completeness | input | before matching |
| Factual accuracy | output | resume & cover-letter generation |
| ATS formatting validator | output | resume generation |
| Application rate limiter | tool | application submission |
| Job verification gate | tool | matching only ranks `verified=True` |

## Production upgrade path

- Swap `DATABASE_URL` to Postgres; repositories already speak SQL-ish DAO methods.
- Add Redis-backed `ProfileContext` store for multi-worker sessions.
- Front the API with the React portal (out of scope here; contract documented in `api/app.py`).
- Replace deterministic agents with the OpenAI Agents SDK adapter.
