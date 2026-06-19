# AI Career Assistant — Frontend

A Next.js 14 (App Router) single-page experience with a cinematic 3D hero
(React Three Fiber), glassmorphism UI, and Framer Motion animations. It talks to
the FastAPI backend over REST.

## Stack

- **Next.js 14** + React 18 + TypeScript
- **React Three Fiber** + drei for the 3D scene
- **Tailwind CSS** custom design system (aurora gradients, glass, neon accents)
- **Framer Motion** for entrance + micro-interactions
- **lucide-react** icons

## Local development

```bash
npm install
cp .env.example .env.local           # set NEXT_PUBLIC_API_URL
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Open <http://localhost:3000>. Make sure the backend is running (see repo root
`README.md` / `DEPLOY.md`).

## Deploy to Vercel

1. Push this repo to GitHub. If it's the monorepo, set Vercel's **Root Directory**
   to `frontend`.
2. Import on <https://vercel.com/new>; Next.js is auto-detected.
3. Add env var `NEXT_PUBLIC_API_URL` = your Hugging Face Space URL
   (e.g. `https://your-username-ai-career-assistant.hf.space`).
4. Deploy. Then set `ALLOWED_ORIGINS` on the backend to your `*.vercel.app` URL.

## Design system

| Token | Value |
|-------|-------|
| Background | `#05060a` (near-black) with aurora radial gradients |
| Accents | violet `#8b5cf6` → fuchsia `#d946ef` → cyan `#22d3ee` |
| Surfaces | glassmorphism: `bg-white/4` + `backdrop-blur-xl` + hairline border |
| Type | Space Grotesk (display) + Inter (body) |
| Motion | staggered fade-up on scroll, animated gradient text, floating blobs |

## Structure

```
app/
  layout.tsx        # fonts + metadata
  page.tsx          # composes the sections
  globals.css       # design tokens + glass/btn utilities
components/
  Background.tsx     # aurora + grid + noise layers
  Scene3D.tsx        # R3F canvas (career orb + agent satellites + sparkles)
  Navbar.tsx Hero.tsx HowItWorks.tsx AgentsShowcase.tsx Footer.tsx
  PipelineRunner.tsx # the interactive demo (form -> agent flow -> results)
  AgentFlow.tsx MatchRing.tsx JobResultCard.tsx
lib/
  api.ts types.ts cn.ts
```
