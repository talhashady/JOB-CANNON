# Improvements over the original blueprint

These are the deliberate engineering decisions made while implementing the blueprint.
Each one preserves the intent of the design while making it runnable, testable, and safer.

## 1. JobSpy as the discovery backend
The blueprint left scraping unspecified. We standardize on **JobSpy**, which aggregates
Indeed, LinkedIn, Glassdoor, Google and ZipRecruiter behind one interface and has no Indeed
rate-limiting. The scraping agent honors the documented **1000 results/search** cap and
normalizes every board into a single `Job` model.

## 2. Offline-first / graceful degradation
The single biggest usability improvement: the system **runs with no API key and no network**.
- No `OPENAI_API_KEY` -> agents use deterministic fallbacks.
- No JobSpy / no network -> scraper serves realistic sample jobs.
- No CV parser libs -> plain-text CV parsing.
This makes onboarding, CI, and demos trivial, and isolates external-service risk.

## 3. Safety-first auto-application
Auto-submitting applications can violate platform ToS and harm users (account flags).
We make submission **dry-run by default**. Real submission requires `ALLOW_LIVE_APPLY=true`
*and* a user-provided backend. The rate limiter is always on.

## 4. Composable, unit-tested guardrails
Guardrails are pure functions with explicit inputs/outputs and dedicated tests, instead of
prose rules. The factual-accuracy guardrail does set-difference on skills so a resume can
never introduce experience absent from the CV.

## 5. Pragmatic storage
SQLite by default (zero setup), with a thin repository layer so Postgres is a URL change.
We avoid prematurely wiring Mongo/Elasticsearch/Redis; the seams exist where they'd plug in.

## 6. Strong typing
All domain objects are Pydantic v2 models with validation, so malformed scraper output or
profiles fail fast with clear errors.

## 7. Deterministic match scoring
The matching algorithm is explicit and weighted (skills 0.45, experience 0.25, location 0.15,
goal alignment 0.15) so results are explainable and testable - not a black box.

## 8. Observability
Structured logging with per-stage timing and an `agent_chain` audit trail on every run,
mirroring the blueprint's tracing requirement without locking you into a vendor.

## Deliberately out of scope (documented, not built)
- React/Vue frontend (API contract is provided).
- Kubernetes manifests / HPA (Dockerfile + compose provided as the local equivalent).
- Live Selenium cluster (dangerous to ship enabled; interface stubbed).
