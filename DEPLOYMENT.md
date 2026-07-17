# DEPLOYMENT.md — Avian Observatory

> How to deploy the platform to production. **The repository is prepared but not
> deployed** — no cloud resources exist yet. This is the runbook to create them.

## Target architecture

```
Vercel (Next.js frontend)  ──HTTPS──▶  Heroku Container Stack (FastAPI + TensorFlow + BirdNET)
                                             │
                                       Heroku Postgres (metadata)
```

- **Frontend → Vercel.** Static/SSR Next.js; reads `NEXT_PUBLIC_API_BASE` at build/runtime.
- **Backend → Heroku Container Stack (Docker).** Full TensorFlow + BirdNET inference.
- **Database → Heroku Postgres.**

## Why the Container Stack (not the buildpack)

The classic Heroku Python buildpack has a **500 MB compressed slug limit**. The
API's dependency stack is **~2.3 GB** (TensorFlow alone is 1.1 GB). A Docker image
has no slug limit, so the backend deploys via the **Container Stack**
(`heroku.yml`). No functionality is reduced.

## Files in this repository that make deployment possible

| File | Role |
|---|---|
| `Dockerfile` | API image: Python 3.12, ffmpeg/libsndfile/libgomp, full ML stack, single-`uvicorn` start on `$PORT` |
| `.dockerignore` | Keeps the build context small + secret-free (excludes `birdenv/`, `frontend/`, training audio, `.env*`) |
| `heroku.yml` | Container-stack manifest: build `web` from `Dockerfile`; **release** = `alembic upgrade head` + `python -m api.seed`; run `web` |
| `Procfile` | Same process contract (buildpack path / documentation) |
| `app.json` | Declarative manifest: `stack: container`, Postgres add-on, `standard-2x` dyno, config vars |
| `api/settings.py` | Reads `DATABASE_URL` (Heroku) and normalises `postgres://`→`postgresql+psycopg://`; CORS accepts a comma-separated config var |

## ⚠️ The one thing to plan for: models + seed data are gitignored

`models/*.tflite/.keras`, `sample_audio/`, `birdnet_results2/`, and
`detections/*.json` are **gitignored** (deliberately, for the GitHub release), so a
**git-based** Heroku build (`git push heroku`) would **not** contain them. The
image needs them baked in. Two supported options:

1. **Recommended — `heroku container:push` from a local checkout** (the local
   Docker build context *does* include the gitignored files, so they get baked in).
   Requires **Docker installed locally** (not currently installed on this machine).
2. **Object storage** — host the artefacts on S3/R2 and add a `RUN` step to the
   `Dockerfile` (or a release step) that downloads them. Avoids committing large
   binaries; adds a bucket to manage.

`.dockerignore` is already written so that option 1 works out of the box.

---

## Prerequisites (install once, locally)

- **Heroku CLI** (`heroku --version`) — installed on this machine ✅
- **Docker Desktop** — required for `heroku container:push` (option 1) — **not yet installed**
- **Vercel account** (+ optional `vercel` CLI) — for the frontend
- Your MapTiler client key (already in `frontend/.env.local`)

## Backend deploy — step by step (future)

```bash
# 1. Authenticate + create a container app
heroku login
heroku create avian-observatory-api --stack container

# 2. Provision PostgreSQL (injects DATABASE_URL)
heroku addons:create heroku-postgresql:essential-0 -a avian-observatory-api

# 3. Configure production env
heroku config:set BIRDDASH_ENVIRONMENT=production BIRDDASH_AUTH_MODE=dev -a avian-observatory-api
#   CORS is set after the frontend URL is known (step 8)

# 4. Build + push the image (option 1 — needs local Docker; bakes in models/data)
heroku container:push web -a avian-observatory-api
heroku container:release web -a avian-observatory-api
#   The release phase auto-runs: alembic upgrade head && python -m api.seed

# 5. Scale the dyno. standard-2x (1 GB) is RECOMMENDED for TensorFlow headroom;
#    a 512 MB dyno is likely to hit memory limits under model loading/inference.
heroku ps:scale web=1:standard-2x -a avian-observatory-api

# 6. Verify
heroku logs --tail -a avian-observatory-api
curl https://avian-observatory-api.herokuapp.com/api/v1/healthz     # {"status":"ok"}
curl https://avian-observatory-api.herokuapp.com/api/v1/readyz      # checks the DB
curl https://avian-observatory-api.herokuapp.com/api/v1/models/comparison  # NT 23/23
```

## Frontend deploy — step by step (future)

```
7. Vercel → New Project → import github.com/harshrastogii/BirdDashboard
   • Root Directory: frontend
   • Environment Variables:
       NEXT_PUBLIC_API_BASE   = https://avian-observatory-api.herokuapp.com
       NEXT_PUBLIC_MAPTILER_KEY = <your MapTiler key>
   • Deploy.

8. Allow the frontend origin through CORS (backend):
   heroku config:set BIRDDASH_CORS_ALLOW_ORIGINS=https://<your-app>.vercel.app -a avian-observatory-api
```

## Post-deploy verification checklist

- [ ] `/api/v1/healthz` → ok; `/api/v1/readyz` → DB reachable
- [ ] Release phase ran migrations + seed (`heroku releases`, logs)
- [ ] `/api/v1/models/comparison` → NT 23/23 (parser fix present)
- [ ] `/api/v1/models/registry`, `/api/v1/map/sites`, `/api/v1/species` respond
- [ ] TensorFlow + BirdNET load (hit `/recordings/{id}/nt-predictions` and `/multi-species`)
- [ ] Frontend loads; Models, Map, Workspace pages render; no console/CORS errors

## Known limitations in this topology

- **Ephemeral filesystem.** Heroku dynos reset on deploy/restart. Seeded read data
  (baked into the image) is fine, but **new uploads and freshly-computed detections
  do not persist** across restarts. For durable uploads, add S3/R2 object storage
  and point the uploads/detections paths at it (a follow-up, not required for the
  seeded demo).
- **Cold starts.** Loading TensorFlow adds seconds to the first request after a
  dyno starts.
- **PostGIS** is not enabled (not required until GIS Stage 2).

## Estimated monthly cost (Heroku, USD)

| Resource | Plan | ~Cost/mo |
|---|---|---|
| Web dyno | Standard-2x (1 GB, **recommended** for TF) | ~$50 |
| PostgreSQL | Essential-0 | ~$5 |
| Vercel (frontend) | Hobby | $0 |
| **Total** | | **~$55/mo** |

*(Eco/Basic 512 MB dynos are cheaper but likely to hit memory limits under
TensorFlow; standard-2x is recommended for headroom. Actual footprint should be
confirmed on first deploy — a smaller dyno may suffice for light/read-only use.)*

## Rollback

`heroku releases:rollback -a avian-observatory-api` reverts to the previous
release (image + migrations are versioned per release).
