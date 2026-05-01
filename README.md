![CI](https://github.com/gauthambinoy/gnosis/actions/workflows/ci.yml/badge.svg)
![Python](https://img.shields.io/badge/python-3.12-blue)
![Node](https://img.shields.io/badge/node-20-green)
![License](https://img.shields.io/badge/license-MIT-blue)

# 🧠 Gnosis — AI Agent Automation Platform

> A production-minded AI agent platform: neuroscience-inspired agent design, 4-tier memory, self-learning loops, RPA automation, multi-agent swarms, and a Universal LLM Gateway.

Gnosis is built as a portfolio-grade SaaS foundation: FastAPI + async SQLAlchemy backend, Next.js 16 frontend, CI, Docker Compose, observability, security middleware, Terraform AWS infrastructure, and mocked LLM tests so contributors can validate changes without provider keys.

## Recruiter / Startup Demo Path

1. **Run locally in 5 minutes** with Docker Compose.
2. **Open the dashboard** at `http://localhost:3000` and API docs at `http://localhost:8000/docs`.
3. **Create a user and an agent** using the curl demo below.
4. **Show the architecture**: 100+ API modules, 40+ core engines, memory/learning/oracle/swarm/RPA systems, CI, security docs, deployment docs.
5. **Deploy publicly** using [docs/PORTFOLIO_DEPLOY.md](docs/PORTFOLIO_DEPLOY.md) when real hosting secrets are available.

## What Makes It Interesting

- **Agent Factory** — turns natural-language automation descriptions into deployment plans.
- **4-tier memory** — correction, episodic, procedural, and semantic memory with FAISS retrieval.
- **3-loop learning** — instant corrections, pattern extraction, and periodic evolution.
- **Dream + Oracle engines** — idle-time scenario simulation and cross-agent insight detection.
- **Universal LLM Gateway** — OpenRouter, OpenAI, Anthropic, Ollama/local, and other providers behind one interface.
- **Automation layer** — RPA record/replay, inbound webhooks, schedules, pipelines, and integrations.
- **SaaS readiness** — auth, billing/quota guards, feature flags, audit logging, PII controls, rate limiting, metrics, and Terraform AWS infrastructure.

## Architecture at a Glance

```text
Next.js 16 dashboard
  ├─ App Router UI, auth screens, command palette, live agent views
  └─ REST + WebSocket
        ↓
FastAPI API layer (/api/v1)
  ├─ Auth, agents, factory, memory, RAG, RPA, swarm, billing, governance
  ├─ Middleware: request ID, body limit, security headers, CORS, rate limits, metrics
  └─ Core engines
        ├─ LLM gateway → OpenRouter/OpenAI/Anthropic/Ollama
        ├─ Memory + RAG → FAISS + SQLAlchemy models
        ├─ Learning/Dream/Oracle/Predictive engines
        └─ RPA/Swarm/Pipeline/Scheduler engines
              ↓
PostgreSQL · Redis · Prometheus/Grafana · AWS ECS/RDS/ElastiCache via Terraform
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for deeper module-level detail.

## Quickstart

### Prerequisites

| Tool | Minimum version |
| --- | --- |
| Python | 3.12 |
| Node.js | 20 |
| Docker + Compose | Recommended |
| PostgreSQL / Redis | Optional for local no-Docker mode |

### Docker Compose (recommended)

```bash
git clone https://github.com/gauthambinoy/gnosis.git
cd gnosis
cp backend/.env.example backend/.env
# Fill SECRET_KEY before production; local dev may use DEBUG=true with a generated key.
docker compose up -d --build
```

| Service | URL |
| --- | --- |
| Frontend | http://localhost:3000 |
| Backend | http://localhost:8000 |
| API docs | http://localhost:8000/docs |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (`admin` / `gnosis`) |

### No-Docker local development

```bash
# Backend
cd backend
pip install -r requirements-dev.txt
export ENVIRONMENT=development
export DEBUG=true
export SECRET_KEY="$(openssl rand -hex 32)"
export DATABASE_URL="sqlite+aiosqlite:///./dev.db"
uvicorn app.main:app --reload --port 8000

# Frontend, from repo root in another terminal
cd frontend
npm ci
npm run dev
```

## API Demo: Create and Queue an Agent

```bash
# 1) Register and capture token
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"secure-password-123","full_name":"Demo User"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')

# 2) Create an agent
AGENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name":"Customer Memory Concierge",
    "description":"Remembers customer preferences and turns corrections into durable operating rules.",
    "personality":"friendly",
    "avatar_emoji":"🧠",
    "trigger_type":"manual",
    "integrations":["slack","notion"],
    "guardrails":["scrub_pii","require_human_handoff_on_refund"]
  }' | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')

# 3) Queue an execution
curl -s -X POST http://localhost:8000/api/v1/execute/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":\"$AGENT_ID\",\"trigger_type\":\"manual\",\"trigger_data\":{\"input\":\"Summarize this customer note and remember their preference for concise updates.\"}}" | python3 -m json.tool
```

More example agent recipes live in [examples/agent-recipes.json](examples/agent-recipes.json).

## Project Layout

```text
gnosis/
├── backend/               # FastAPI app, core engines, SQLAlchemy models, tests
├── frontend/              # Next.js 16 dashboard and component tests
├── docs/                  # Ops, auth, WebSocket, and portfolio deploy docs
├── examples/              # Demo agent recipes for recruiters/users
├── infra/                 # Terraform AWS, Prometheus, Grafana provisioning
├── sdk/                   # Python SDK skeleton/docs
├── docker-compose.yml     # Local full stack
└── .github/workflows/     # CI, security, deploy workflows
```

## Validation

### Backend

```bash
cd backend
export ENVIRONMENT=ci
export DEBUG=true
export SECRET_KEY="ci-test-secret-key-not-for-production-use-only"
export DATABASE_URL="sqlite+aiosqlite:///./test.db"
python3 -m pytest tests/ -q --tb=short
ruff check .
```

LLM calls are mocked by default. Tests marked `live_llm` are skipped unless explicitly selected and provider keys are exported.

### Frontend

```bash
cd frontend
npm run typecheck
npm run lint
npx vitest run
npm run build
```

## Deployment

- **Portfolio demo:** [docs/PORTFOLIO_DEPLOY.md](docs/PORTFOLIO_DEPLOY.md) — Vercel frontend + hosted Docker backend when secrets are available.
- **AWS production:** [DEPLOYMENT.md](DEPLOYMENT.md) and `infra/terraform/` — ECS Fargate, RDS, ElastiCache, ALB, CloudFront, WAF, KMS, SQS/SNS/SES.
- **Operations:** [RUNBOOK.md](RUNBOOK.md) — rollback, backups, health checks, and secret rotation.

## Security

- Strong `SECRET_KEY` is mandatory outside development/test.
- Default LLM tests never call real providers.
- Security posture: JWT/bcrypt auth, hardened middleware, request IDs, audit logging, PII scrubbing, body-size limits, CORS allowlists, SSRF-aware Auto-API host allowlist.
- See [SECURITY.md](SECURITY.md), [COMPLIANCE.md](COMPLIANCE.md), and [docs/AUTH_MATRIX.md](docs/AUTH_MATRIX.md).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for the branching model, Conventional Commits, and pre-PR checks.

## License

MIT
