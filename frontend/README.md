# Avian Observatory — Web App

The Next.js frontend for **Avian Observatory**, a scientific platform for acoustic
bird monitoring, biodiversity assessment, and environmental intelligence in the
Northern Territory. It consumes the FastAPI backend (`../api`) as its stable
contract.

## Stack

Next.js 16 (App Router) · React 19 · TypeScript · Tailwind CSS v4 · TanStack Query ·
MapLibre GL + MapTiler · wavesurfer.js · Zustand · next-themes.

## Run (dev)

```bash
# 1. Backend (from repo root, in the birdenv venv)
uvicorn api.main:app --port 8000     # requires: alembic upgrade head && python -m api.seed

# 2. Frontend
cd frontend
npm install          # first time only
npm run dev          # http://localhost:3000
```

Config lives in `.env.local` (gitignored):

```
NEXT_PUBLIC_API_BASE=http://localhost:8000
NEXT_PUBLIC_MAPTILER_KEY=<your MapTiler key>
```

## Structure

```
app/
  page.tsx                 public homepage
  (platform)/              app shell (sidebar + topbar) wrapping all modules
    dashboard/ map/ species/ recordings/ …
components/
  ui/  layout/  map/  audio/  spectrogram/  data/  domain/
lib/
  api/ (client, types, hooks)  config  providers  utils
```

## Design system

"Observatory" identity: deep teal + slate, restrained NT earth-tone accents,
field-notebook metadata cues. Light default; night-observatory dark. Tokens are
CSS variables in `app/globals.css`, consumed via Tailwind.

## Build

```bash
npm run build        # production build (Turbopack)
```
