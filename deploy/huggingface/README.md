---
title: AI Career Assistant API
emoji: 🚀
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
pinned: false
license: mit
---

# AI Career Assistant — Backend (Hugging Face Space)

This Space runs the FastAPI multi-agent backend in Docker.

## How this Space is built

Hugging Face Spaces detects the root `Dockerfile` and serves the container on port
`7860` (declared by `app_port` above). The repo's existing `Dockerfile` already
listens on `${PORT:-7860}`, so it works as-is.

## Required / optional secrets

Add these under **Settings → Variables and secrets**:

| Name | Type | Notes |
|------|------|-------|
| `OPENAI_API_KEY` | secret | Optional. Without it, agents use deterministic fallbacks. |
| `ALLOWED_ORIGINS` | variable | Your Vercel URL, e.g. `https://your-app.vercel.app`. |
| `ALLOW_LIVE_APPLY` | variable | Keep `false` unless you have a compliant apply backend. |
| `DEFAULT_JOB_SITES` | variable | e.g. `indeed,linkedin`. |

## Endpoints

- `GET /` — service info
- `GET /health` — health + config flags
- `GET /docs` — interactive OpenAPI docs
- `POST /profiles` — create a profile from CV text
- `POST /run` — run the full pipeline
- `GET /applications/{user_id}` — application history

> See the repo root `DEPLOY.md` for the step-by-step push instructions.
