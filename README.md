![CI](https://github.com/gauthambinoy/gnosis/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Node](https://img.shields.io/badge/node-20-green)
![License](https://img.shields.io/badge/license-MIT-blue)

# 🧠 Gnosis — AI Agent Orchestration Platform

> Build, deploy, and manage intelligent AI agents with a powerful orchestration engine.

## What is Gnosis?

Gnosis is a multi-tenant AI agent orchestration platform built on a FastAPI backend and a Next.js 16 frontend. The backend exposes over 100 router modules (registered in `backend/app/main.py`) covering everything from core agent lifecycle management to governance, compliance, observability, and RPA automation. All API routes live under the `/api/v1` prefix and are rate-limited by default via `app/core/rate_limiter.py`.

The platform includes a suite of autonomous "engine" modules in `backend/app/core/`: an **Agent Factory** that generates complete agents from a natural-language description, a **3-loop Learning Engine** (instant correction → pattern extraction → deep evolution), a **Dream Engine** that simulates scenarios while agents are idle to improve their prompts, an **Oracle Engine** for cross-agent pattern detection and proactive insight generation, and a **Predictive Engine** that analyses user behavioural patterns to spawn agents before they are requested.

Additional capabilities include a **Swarm Engine** enabling agents to form dynamic teams, vote on decisions, and share credit; a **RAG Engine** with FAISS-based vector search for document ingestion and retrieval; **RPA automation** via a record-and-replay browser engine built on Playwright action types; multi-tier **billing** (Free / Starter / Pro / Enterprise) enforced by quota guards; and **feature flags** with per-workspace / per-user scoped rollout percentages. The platform is fully observable through `prometheus_client` metrics at `/metrics` and structured JSON logging via `app/core/logger.py`.

Security is layered: JWT (HS256) with bcrypt password hashing lives in `app/core/auth.py` and `app/core/security.py`; a hardened `UltraSecurityMiddleware` sits on top of a general `SecurityMiddleware`; PII scrubbing (`app/core/pii_scrubber.py`), injection pattern detection, request-body size limiting, GDPR/DPA consent management, and audit logging round out the enterprise security posture. OAuth2 SSO via Google and GitHub is wired through `app/api/sso.py`.

## Architecture at a Glance

See **[ARCHITECTURE.md](ARCHITECTURE.md)** for full detail. The short version:

- **Frontend** (Next.js 16, TypeScript, Tailwind, Zustand, Framer Motion) → REST + WebSocket → **Backend**
- **Backend** (FastAPI, SQLAlchemy async, Alembic, pydantic-settings) → **Core Engines** (40+ modules in `app/core/`)
- **Data stores**: PostgreSQL 16 (primary), Redis 7 (cache + pub/sub), in-process FAISS vectors
- **LLM Providers**: OpenRouter (primary, 100+ models), OpenAI, Anthropic, Ollama (local) via `app/core/llm_gateway.py`
- **Infra**: AWS ECS Fargate + RDS PostgreSQL + ElastiCache Redis + CloudFront + ALB, managed by Terraform in `infra/terraform/`

## Quickstart

### Prerequisites

| Tool | Minimum version |
|------|----------------|
| Python | 3.12 |
| Node.js | 20 |
| PostgreSQL | 16 (optional — SQLite used in dev/CI) |
| Redis | 7 (optional — degrades gracefully) |

### Local development (no Docker)

```bash
# 1. Clone
git clone https://github.com/gauthambinoy/gnosis.git
cd gnosis

# 2. Backend
cd backend
pip install -r requirements.txt

# Minimum required env vars (add to backend/.env or export):
export SECRET_KEY="$(openssl rand -hex 32)"
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
export DEBUG=true

uvicorn app.main:app --reload --port 8000

# 3. Frontend (new terminal, from repo root)
cd frontend
npm ci
npm run dev
```

The backend will be available at `http://localhost:8000`; interactive API docs at `http://localhost:8000/docs`.
The frontend will be available at `http://localhost:3000`.

### Docker Compose (recommended)

```bash
docker-compose up -d
```

| Service | URL |
|---------|-----|
| Backend (FastAPI) | http://localhost:8000 |
| Frontend (Next.js) | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (admin / gnosis) |

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 16, React 19, TypeScript, Tailwind CSS, Zustand, Framer Motion |
| Backend | Python 3.12, FastAPI, SQLAlchemy 2 (async), Pydantic v2 |
| Auth | JWT (HS256) + bcrypt, OAuth2 SSO (Google, GitHub) |
| Database | PostgreSQL 16 (prod), SQLite / aiosqlite (dev/CI) |
| Cache / PubSub | Redis 7 |
| Vector Search | FAISS (in-process) |
| LLM Routing | OpenRouter, OpenAI, Anthropic, Ollama |
| Migrations | Alembic |
| Metrics | prometheus_client |
| Infra / IaC | Terraform ≥ 1.5, AWS ECS Fargate, RDS, ElastiCache, CloudFront |
| CI | GitHub Actions |

## Project Layout

```
gnosis/
├── backend/
│   ├── app/
│   │   ├── api/          # 100+ FastAPI router modules
│   │   ├── core/         # Business logic engines (llm_gateway, learning_engine,
│   │   │                 #   dream_engine, oracle_engine, predictive_engine,
│   │   │                 #   agent_factory, rpa_engine, swarm_engine, billing,
│   │   │                 #   feature_flags, rag_engine, memory_engine, guardrails,
│   │   │                 #   system_control, collaboration, metrics, auth, …)
│   │   ├── middleware/   # audit_log, body_limit, rate_limiter, request_id
│   │   ├── models/       # SQLAlchemy ORM models (agent, user, execution, memory, …)
│   │   ├── schemas/      # Pydantic request / response schemas
│   │   ├── tasks/        # Background task workers (memory_decay, …)
│   │   ├── ws/           # WebSocket endpoints (nerve_center, minds_eye, routes)
│   │   ├── config.py     # Pydantic-Settings (all env vars documented here)
│   │   └── main.py       # FastAPI app, middleware stack, router registration
│   ├── alembic/          # Database migrations (3 migration files)
│   └── tests/            # pytest test suite
├── frontend/
│   └── src/
│       ├── app/          # Next.js App Router pages ((app)/ and (auth)/)
│       ├── components/   # Reusable React components
│       └── lib/          # API client, utilities
├── infra/
│   ├── terraform/        # AWS IaC (ECS, RDS, ElastiCache, CloudFront, ALB, WAF, …)
│   ├── prometheus/       # Prometheus scrape config
│   └── grafana/          # Dashboard provisioning
├── scripts/              # Utility scripts
├── sdk/                  # Client SDK (stub)
├── docker-compose.yml    # Full local stack
└── deploy.sh             # Deployment helper
```

## Running Tests

### Backend

```bash
cd backend
# env vars required for test runner:
export DEBUG=true
export SECRET_KEY="ci-test-secret-key-not-for-production-use-only"
export DATABASE_URL="sqlite+aiosqlite:///./test.db"

pytest tests/ -v --tb=short
```

`pytest-cov` is available in the requirements; add `--cov=app --cov-report=term-missing` for coverage output.

**LLM calls are mocked by default.** An autouse fixture in `backend/tests/conftest.py` replaces `llm_gateway.complete`, every provider in `app/llm/client.py`, and any `aiohttp`/`httpx` call aimed at OpenRouter, OpenAI, Anthropic, Google, or Ollama with a deterministic canned response, so the suite can never reach a real provider. Customize the canned response per-test with the `mock_llm` fixture (`mock_llm.set_response(content=..., tokens_prompt=..., tokens_completion=..., cost_estimate=..., provider=...)`). To run against a real provider, mark the test with `@pytest.mark.live_llm` and invoke `pytest -m live_llm` with the appropriate API keys exported.

### Frontend

```bash
cd frontend
npx vitest run
```

The full CI pipeline (`npm run build && npm run lint && npx vitest run`) mirrors `.github/workflows/ci.yml`.

### CI repo-secrets

`.github/workflows/ci.yml` reads `SECRET_KEY` from a GitHub Actions repo secret named **`CI_SECRET_KEY`** (no longer hard-coded). Before CI can pass, a maintainer must set this secret once in **GitHub → Settings → Secrets and variables → Actions → New repository secret**:

| Name            | Value                                                              |
| --------------- | ------------------------------------------------------------------ |
| `CI_SECRET_KEY` | Any random 32+ char string (e.g. `openssl rand -hex 32`). Test-only — do **not** reuse in any other environment. |

If the secret is missing, the backend test job will fail on app import because `SECRET_KEY` will be empty.

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for branching model, Conventional Commits, pre-PR checks, and coding standards.

## Security

See **[SECURITY.md](SECURITY.md)** for the vulnerability disclosure policy.

## Operations

See **[RUNBOOK.md](RUNBOOK.md)** for on-call procedures, rollback steps, database operations, and secrets rotation.

## License

MIT
