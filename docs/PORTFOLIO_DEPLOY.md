# Portfolio Demo Deployment

Use this path when you want a public recruiter/startup demo without pretending secrets are already configured.

## Recommended free/low-cost split

| Layer | Host | Why |
| --- | --- | --- |
| Frontend | Vercel hobby project from `frontend/` | Native Next.js deploys, preview URLs, free custom domain support |
| Backend API | Render/Fly/Railway Docker service from `backend/` | Runs the FastAPI Dockerfile without changing app code |
| Database | Managed PostgreSQL from the backend host | Avoids exposing local DB credentials |
| Redis | Optional managed Redis | App degrades gracefully for a demo, but Redis is recommended for rate limits/pub-sub |

## 1. Backend service

Create a new web service from this repository using `backend/Dockerfile`.

Required environment variables:

```bash
ENVIRONMENT=production
DEBUG=false
SECRET_KEY=<openssl rand -hex 32>
DATABASE_URL=<managed-postgres-url, async SQLAlchemy format>
REDIS_URL=<managed-redis-url, optional but recommended>
ALLOWED_ORIGINS=https://<your-vercel-app>.vercel.app
CORS_ORIGINS=https://<your-vercel-app>.vercel.app
DEFAULT_LLM_PROVIDER=openrouter
OPENROUTER_API_KEY=<optional for live LLM calls>
GNOSIS_AUTO_API_ALLOWED_HOSTS=api.github.com,api.openrouter.ai
```

Start command if the host does not infer Docker CMD:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Health check path:

```text
/api/v1/health
```

## 2. Frontend service

Import the repo into Vercel and set **Root Directory** to `frontend`.

Environment variables:

```bash
NEXT_PUBLIC_API_URL=https://<your-backend-host>
NEXT_PUBLIC_WS_URL=wss://<your-backend-host>
```

Vercel build command stays `npm run build`; output uses the default Next.js adapter.

## 3. Smoke test after deploy

```bash
curl https://<your-backend-host>/api/v1/health
curl https://<your-backend-host>/api/v1/health/live
```

Then open the Vercel URL, create a user, and create the "Customer Memory Concierge" recipe from `examples/agent-recipes.json`.

## Production notes

- Do not reuse local or CI `SECRET_KEY` values.
- Use provider dashboards/secrets stores; never commit deployed values.
- Run Alembic migrations before pointing real users at the backend.
- Keep AWS Terraform in `infra/terraform/` for the full production path when the project needs VPC, WAF, ECS, RDS, and ElastiCache.
