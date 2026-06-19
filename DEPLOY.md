# Deployment Guide

Two deployable units:

- **Backend** (FastAPI) → **Hugging Face Spaces** (Docker)
- **Frontend** (Next.js) → **Vercel**

```
  Browser ─► Vercel (Next.js UI) ──HTTPS─► Hugging Face Space (FastAPI API)
```

---

## 1) Backend → Hugging Face Spaces

### Option A — New Space from this repo (recommended)

1. Create a Space: <https://huggingface.co/new-space> → **SDK: Docker** → blank template.
2. Copy the Space card header into the repo root README, or just push the file at
   `deploy/huggingface/README.md` **as the Space's root `README.md`** (it contains the
   required YAML front matter with `sdk: docker` and `app_port: 7860`).
3. Push the backend to the Space remote:
   ```bash
   # from the project root (the folder with Dockerfile + pyproject.toml)
   git init
   git remote add space https://huggingface.co/spaces/<your-username>/ai-career-assistant
   cp deploy/huggingface/README.md README.space.md   # keep your project README separate
   #   -> then commit README.space.md as README.md in the Space, OR paste the YAML
   #      header at the top of your existing README.md.
   git add .
   git commit -m "Deploy AI Career Assistant backend"
   git push space main
   ```
4. In the Space, open **Settings → Variables and secrets** and add `OPENAI_API_KEY`
   (secret) and `ALLOWED_ORIGINS=https://<your-app>.vercel.app`.
5. Wait for the build. Your API is live at:
   `https://<your-username>-ai-career-assistant.hf.space`
   (check `/health` and `/docs`).

> The Dockerfile listens on `${PORT:-7860}`; Spaces sets `PORT=7860` automatically.

### Option B — Any other Docker host (Render/Fly/Railway)

```bash
docker build -t ai-career-assistant .
docker run -p 8000:7860 -e OPENAI_API_KEY=sk-... ai-career-assistant
```

---

## 2) Frontend → Vercel

1. Push the `frontend/` folder to a GitHub repo (or import the monorepo and set the
   **Root Directory** to `frontend`).
2. On <https://vercel.com/new>, import the repo. Vercel auto-detects Next.js.
3. Add an Environment Variable:
   - `NEXT_PUBLIC_API_URL = https://<your-username>-ai-career-assistant.hf.space`
4. Deploy. Vercel gives you `https://<your-app>.vercel.app`.
5. Go back to the HF Space and set `ALLOWED_ORIGINS` to that Vercel URL, then restart
   the Space so CORS allows your frontend.

### Local dev

```bash
# terminal 1 — backend
pip install -e ".[all]"
uvicorn career_assistant.api.app:app --reload --port 8000

# terminal 2 — frontend
cd frontend
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

---

## 3) OpenAI Agents SDK (optional runtime)

The app ships with a built-in orchestrator that runs offline. To run on the official
SDK instead:

```bash
pip install openai-agents
export OPENAI_API_KEY=sk-...
python -c "from career_assistant.agents_sdk import is_available; print(is_available())"
```

See `src/career_assistant/agents_sdk/adapter.py`.
