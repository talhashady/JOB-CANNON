# AI Career Assistant — Multi-Agent Orchestrator

A production-oriented **multi-agent system** that automates the job-search lifecycle:
discovery → verification → matching → resume/cover-letter customization → (dry-run)
application → tracking → skill-gap & interview prep.

Built around the **Manager + Handoff** pattern described in the blueprint, with a
**Career Orchestrator** sequencing eight specialist agents. Job discovery is powered by
[**JobSpy**](https://github.com/speedyapply/JobSpy) (Indeed, LinkedIn, Glassdoor, Google,
ZipRecruiter).

> This repository is a clean, runnable **reference implementation**. It is designed so the
> full pipeline runs end-to-end on your laptop with SQLite and **no API key** (deterministic
> fallbacks), and upgrades to OpenAI models + Postgres when configured.

---

## Why this design (engineering notes)

The original blueprint specifies Kubernetes, PostgreSQL, MongoDB, Elasticsearch, Redis,
a React frontend and a Selenium cluster. That is the right *target* architecture, but it is
not something you can clone-and-run. The improvements below keep the same architecture while
making it real today:

| Blueprint | This implementation | Why |
|---|---|---|
| Custom scraper | **JobSpy** backend | Battle-tested, no rate-limiting on Indeed, multi-board |
| Requires OpenAI | **Graceful fallback** to deterministic logic | Pipeline runs & tests without a key or network |
| Postgres + Mongo + ES + Redis | **SQLite by default**, pluggable | Zero-setup local dev; swap via `DATABASE_URL` |
| Live auto-apply via Selenium | **Dry-run by default** + explicit opt-in | ToS / legal safety; never silently submits |
| Implicit guardrails | **Composable guardrail layer** with tests | Verifiable, unit-tested safety |
| No tests | **Pytest suite** for pure logic | Confidence without external services |

See `ARCHITECTURE.md` for the full design and `docs/IMPROVEMENTS.md` for the rationale.

---

## Quick start

```bash
# 1. Create a virtualenv
python3 -m venv .venv && source .venv/bin/activate

# 2. Install
pip install -e .            # or: pip install -r requirements.txt

# 3. (Optional) configure
cp .env.example .env        # add OPENAI_API_KEY to enable LLM mode

# 4. Run the pipeline from the CLI (deterministic mode works with no key)
career-assistant run \
  --profile examples/sample_profile.json \
  --query "python developer" \
  --location "Remote" \
  --sites indeed \
  --results 25

# 5. Or start the API gateway
uvicorn career_assistant.api.app:app --reload
# -> http://127.0.0.1:8000/docs
```

> JobSpy is an optional dependency. Without it (or without network access) the scraping
> agent automatically serves realistic **sample jobs** so you can exercise the full pipeline.
> Install it with `pip install python-jobspy` to scrape live data.

---

## Pipeline stages

1. **Scraping Agent** — JobSpy multi-board search (≤1000/search cap honored).
2. **Verification Agent** — dedupe, expiry, company legitimacy, scam heuristics.
3. **Matching Agent** — weighted compatibility score (skills/experience/location/goals).
4. **Resume Agent** — reorders/highlights CV content; never invents experience.
5. **Cover Letter Agent** — tailored letter grounded in the CV.
6. **Application Agent** — dry-run submission with per-platform rate limiting.
7. **Tracking Agent** — persists status transitions.
8. **Skill-Gap & Interview Agent** — learning roadmap + mock interview questions.

---

## Safety & ethics

- **No real applications are submitted** unless you set `ALLOW_LIVE_APPLY=true` *and* provide
  a real submission backend. The default `dry_run` path records intent only.
- **PII scrubbing** runs on CV input before any model call.
- **Factual-accuracy guardrail** blocks resumes/letters that introduce skills not in the CV.
- Respect each job board's Terms of Service and local laws. You are responsible for usage.

## License

MIT — see `LICENSE`.
