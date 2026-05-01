# Getting Started with Gnosis

Run the full local stack and create your first AI automation agent.

## One-Minute Local Setup

```bash
git clone https://github.com/gauthambinoy/gnosis.git
cd gnosis
cp backend/.env.example backend/.env
# For local-only use, set DEBUG=true and generate SECRET_KEY in backend/.env:
# SECRET_KEY=$(openssl rand -hex 32)
docker compose up -d --build
```

What starts:

| Service | URL |
| --- | --- |
| Backend API | http://localhost:8000 |
| Interactive API docs | http://localhost:8000/docs |
| Frontend dashboard | http://localhost:3000 |
| Prometheus | http://localhost:9090 |
| Grafana | http://localhost:3001 (`admin` / `gnosis`) |

## Your First Agent

### 1. Register and save a token

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "demo@example.com",
    "password": "secure-password-123",
    "full_name": "Demo User"
  }' | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
```

If the user already exists, login instead:

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"secure-password-123"}' \
  | python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
```

### 2. Create an agent

```bash
AGENT_ID=$(curl -s -X POST http://localhost:8000/api/v1/agents \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Investor Inbox Triage",
    "description": "Classifies inbound founder/investor emails, extracts next actions, and drafts concise replies.",
    "personality": "professional",
    "avatar_emoji": "✉️",
    "trigger_type": "email_received",
    "integrations": ["gmail", "slack"],
    "guardrails": ["require_approval_before_send", "scrub_pii"]
  }' | python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])')
```

### 3. Queue an execution

```bash
curl -s -X POST http://localhost:8000/api/v1/execute/trigger \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d "{\"agent_id\":\"$AGENT_ID\",\"trigger_type\":\"manual\",\"trigger_data\":{\"input\":\"Classify: URGENT - production database CPU is at 95%.\"}}" \
  | python3 -m json.tool
```

### 4. Explore generated plans with the Agent Factory

```bash
curl -s -X POST http://localhost:8000/api/v1/factory/analyze \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"description":"Monitor competitor pricing pages every morning and summarize changes in Slack."}' \
  | python3 -m json.tool
```

## Frontend Usage

1. Open http://localhost:3000.
2. Register/login with the same credentials.
3. Visit Factory, Nerve Center, Memory, Oracle, Swarm, RPA, and Security pages.
4. Use `examples/agent-recipes.json` for demo-ready agent ideas.

## Key Endpoints

- `POST /api/v1/auth/register` — create account and receive tokens.
- `POST /api/v1/auth/login` — login and receive tokens.
- `POST /api/v1/agents` — create an agent.
- `GET /api/v1/agents` — list agents.
- `POST /api/v1/execute/trigger` — queue an agent execution.
- `POST /api/v1/factory/analyze` — generate an automation deployment plan.
- `GET /api/v1/health` — liveness check.
- `GET /api/v1/health/ready` — dependency readiness check.

## Monitoring & Logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
curl http://localhost:8000/api/v1/health/ready | python3 -m json.tool
```

## Troubleshooting

- **`backend/.env` missing:** run `cp backend/.env.example backend/.env`.
- **Invalid/empty `SECRET_KEY`:** generate one with `openssl rand -hex 32`.
- **Port already in use:** stop local services on ports 3000, 3001, 5432, 6379, 8000, or 9090.
- **No LLM output:** provider keys are optional for local smoke tests; add `OPENROUTER_API_KEY`, `OPENAI_API_KEY`, or `ANTHROPIC_API_KEY` for live model calls.

## Deploy Next

For a public portfolio demo, follow [docs/PORTFOLIO_DEPLOY.md](docs/PORTFOLIO_DEPLOY.md). For full AWS infrastructure, follow [DEPLOYMENT.md](DEPLOYMENT.md).
