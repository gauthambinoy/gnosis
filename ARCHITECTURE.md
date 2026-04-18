# Gnosis — Architecture

This document describes the internal architecture of the Gnosis AI Agent Orchestration Platform.
It is intended for contributors, operators, and anyone who wants to understand how the pieces fit together.
All module paths are relative to the repository root.

---

## High-Level Component Diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                        Client Layer                                  │
│  Browser / Mobile    ──────────────────────────────────────────────  │
│  Next.js 16 SPA (frontend/src/)                                      │
│    App Router pages  ·  Zustand state  ·  Tailwind UI                │
└──────────────────────────────┬───────────────────────────────────────┘
                               │ HTTP REST (JSON)  +  WebSocket
                               ▼
┌──────────────────────────────────────────────────────────────────────┐
│                       Backend API Layer                              │
│  FastAPI  (backend/app/main.py)                                      │
│                                                                      │
│  Middleware stack (outermost → innermost):                           │
│    GZipMiddleware  →  CORSMiddleware  →  UltraSecurityMiddleware     │
│    →  SecurityMiddleware  →  RequestBodyLimitMiddleware              │
│    →  APIVersionMiddleware  →  RequestIDMiddleware                   │
│    →  MetricsMiddleware  →  route handlers                           │
│                                                                      │
│  100+ router modules  (backend/app/api/*.py)                         │
│  WebSocket endpoints  (backend/app/ws/)                              │
└──────────┬───────────────────────────────────────────────────────────┘
           │
           ├──────────────────────────────────────────────────────────┐
           │  Core Engines  (backend/app/core/)                       │
           │  llm_gateway  ·  learning_engine  ·  dream_engine        │
           │  oracle_engine  ·  predictive_engine  ·  agent_factory   │
           │  memory_engine  ·  rag_engine  ·  swarm_engine           │
           │  rpa_engine  ·  billing  ·  feature_flags                │
           │  guardrails  ·  system_control  ·  collaboration         │
           │  metrics  ·  auth  ·  scheduler  ·  task_worker  …       │
           └──────────────────────────────────────────────────────────┘
           │
           ├──────────────────────────────────────────────────────────┐
           │  Data / Infra Tier                                       │
           │  PostgreSQL 16  (SQLAlchemy async + Alembic)             │
           │  Redis 7        (cache, pub/sub, rate-limit counters)    │
           │  FAISS          (in-process vector store)                │
           │  S3 / DynamoDB / SQS  (AWS — optional, prod only)        │
           └──────────────────────────────────────────────────────────┘
```

---

## Backend Layering

### `backend/app/api/` — Route Handlers

Each file in `api/` is a self-contained FastAPI `APIRouter`. Routers are registered in `main.py` under the `/api/v1` prefix. High-traffic routers receive the `require_rate_limit` dependency that enforces the configurable `RATE_LIMIT_PER_MINUTE` setting. Notable router groups:

| Category | Modules |
|----------|---------|
| Auth & Identity | `auth`, `sso` |
| Agent lifecycle | `agents`, `awakening`, `execute`, `factory`, `agent_clone`, `agent_health`, `agent_export`, `agent_permissions` |
| Memory & Knowledge | `memory`, `rag`, `knowledge_graph`, `memory_prefetch`, `memory_gc` |
| LLM & Streaming | `llm`, `streaming`, `ollama` |
| Orchestration | `pipelines`, `schedules`, `swarm`, `replay`, `execution_cancel`, `exec_queue` |
| Automation | `rpa`, `auto_api`, `inbound_webhooks`, `webhook_triggers`, `webhooks_config` |
| Intelligence | `oracle`, `predictions`, `dreams`, `drift`, `self_heal`, `quality`, `ab_compare` |
| Observability | `audit`, `costs`, `dashboard_stats`, `debugger`, `flamegraph`, `redis_metrics`, `query_analyzer`, `pool_monitor`, `waterfall`, `bundle_analysis` |
| Governance | `billing`, `quotas`, `feature_flags`, `config_snapshots`, `retries`, `dlq`, `retention`, `compliance_reports`, `gdpr`, `dpa`, `consent`, `residency`, `data_flow`, `pii`, `env_promotion` |
| Collaboration | `collaboration`, `collab_edit`, `comments`, `annotations`, `approvals`, `bookmarks` |
| Persona / Behaviour | `emotions`, `mood`, `voice_profiles`, `voice_input`, `persona_inheritance`, `response_templates`, `prompt_compression` |
| Developer UX | `onboarding`, `tutorials`, `sandbox`, `recipes`, `changelog`, `help`, `nudges`, `commands`, `badges`, `cli` |
| Platform | `workspaces`, `integrations`, `integration_tokens`, `marketplace`, `internal_marketplace`, `templates`, `tools`, `search`, `files`, `export_import`, `versions`, `snapshots`, `docker_export`, `edge_deploy`, `bandwidth`, `pwa` |
| System | `system`, `system_control`, `security_dashboard`, `health`, `aws_status`, `standup`, `events`, `activity`, `prompts`, `explanations`, `realworld` |

### `backend/app/core/` — Business Logic Engines

Pure-Python (and async) modules that contain all business logic. Routers depend on core modules; core modules never import from `api/`. This separation keeps the domain layer independently testable.

### `backend/app/models/` — SQLAlchemy ORM

Async SQLAlchemy 2 models using `DeclarativeBase`. Files: `agent.py`, `user.py`, `execution.py`, `memory.py`, `insight.py`, `trust.py`, `engine_state.py`, `base.py`. All models inherit from `app/models/base.py` which sets up the `metadata` object used by Alembic.

### `backend/app/schemas/` — Pydantic v2 Models

Request/response contracts: `agents.py`, `auth.py`, `execute.py`, `factory.py`, `memory.py`, `pipelines.py`, `schedules.py`, `common.py`. Validation happens at the FastAPI boundary; schemas never reach the database layer directly.

### `backend/app/middleware/` — Request Middleware

- `request_id.py` — attaches a unique `X-Request-ID` header to every request for distributed tracing.
- `body_limit.py` — enforces the 10 MB request body ceiling.
- `audit_log.py` — writes a structured audit entry for every mutating request.
- `rate_limiter.py` — sliding-window rate limiting backed by Redis counters.

### `backend/app/tasks/` — Background Workers

`memory_decay.py` is scheduled every 5 minutes via `task_worker` to decay memory `strength` scores across all agents. Additional periodic tasks (`memory_consolidation`, `pattern_learning`, `oracle_analysis`, `trust_evaluation`) are registered in `main.py` lifespan.

### `backend/app/ws/` — WebSocket Endpoints

- `nerve_center.py` — primary real-time channel for agent events, execution status, and system notifications.
- `minds_eye.py` — secondary channel for visual/streaming AI output.
- `routes.py` — execution streaming over WebSocket.
- `manager.py` — connection manager (room-based broadcast).
- `redis_adapter.py` — bridges WebSocket rooms to Redis pub/sub for multi-instance deployments.

---

## Auth Flow

```
Client                        FastAPI                      PostgreSQL
  │                              │                              │
  │  POST /api/v1/auth/login     │                              │
  │  { username, password }      │                              │
  │──────────────────────────────▶                              │
  │                              │  SELECT user WHERE email=?   │
  │                              │─────────────────────────────▶│
  │                              │◀─────────────────────────────│
  │                              │  bcrypt.verify(pw, hash)     │
  │                              │  jwt.encode(sub=user_id,     │
  │                              │    exp=now+30min, HS256)     │
  │◀──────────────────────────────│                              │
  │  { access_token,             │                              │
  │    refresh_token }           │                              │
  │                              │                              │
  │  GET /api/v1/agents          │                              │
  │  Authorization: Bearer <jwt> │                              │
  │──────────────────────────────▶                              │
  │                              │  HTTPBearer.auto_error=False │
  │                              │  jwt.decode(token, SECRET_KEY│
  │                              │    algorithms=["HS256"])     │
  │                              │  → current_user dependency   │
```

Key modules: `app/core/auth.py` (hashing, token encode/decode, `get_current_user` dependency), `app/core/security.py` (injection-pattern detection middleware), `app/core/security_hardened.py` (`UltraSecurityMiddleware` with additional header hardening and CORS enforcement). SSO (Google + GitHub OAuth2) is handled by `app/api/sso.py`.

Token lifetimes are controlled by `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30) and `REFRESH_TOKEN_EXPIRE_DAYS` (default 30), both defined in `app/config.py`.

---

## Core Engine Modules

### `app/core/llm_gateway.py` — Universal LLM Gateway

Routes LLM requests to any provider through a common `LLMGateway` class. Supported providers: OpenRouter (primary, 100+ models), OpenAI, Anthropic, Google, Mistral, Groq, Cohere, Together AI, and Ollama (local). Each provider has a `PROVIDER_CONFIGS` entry with model-tier mappings (`default`, `fast`, `balanced`, `powerful`, `cheap`). The gateway adds in-memory response caching (keyed on prompt hash), retry logic via `app/core/retry.py`, and per-call cost estimation. A companion `app/core/llm_streamer.py` handles streaming responses.

### `app/core/agent_factory.py` — Natural Language Agent Builder

The "describe it → Gnosis builds it" factory. Parses a natural-language description against `INTENT_TEMPLATES` (monitor, scrape, automate_email, data_pipeline, and others) to select an archetype, then generates a complete agent configuration including system prompt, tool list, schedule, and metadata — without requiring the user to write any configuration manually.

### `app/core/learning_engine.py` — 3-Loop Self-Learning

Implements three learning loops:
1. **Instant (Loop 1)** — Stores user corrections immediately into the correction-tier memory with maximum priority; the agent uses them on the very next execution.
2. **Pattern (Loop 2)** — Periodically analyses recent episodic memories to extract procedural rules that the agent can generalise.
3. **Evolution (Loop 3)** — Deep periodic analysis; tunes trust scores, prunes stale memories, and snapshots the agent's evolution trajectory.

Depends on `app/core/memory_engine.py` for storage and `app/core/embeddings.py` for similarity.

### `app/core/dream_engine.py` — Sleep-Time Agent Evolution

When an agent is idle, the Dream Engine generates `DreamScenario` objects (replay, variation, novel, adversarial) by simulating alternative executions of past experiences. Scenarios are scored for improvement; high-scoring variations are promoted to `EvolutionRecord` entries that update the agent's system prompt. This is inspired by how the human brain consolidates memories during sleep.

### `app/core/oracle_engine.py` — Cross-Agent Pattern Detection

Analyses patterns across all agents in the workspace to generate `OracleInsight` objects. Detects: high-failure agents (> 20 % failure rate), low-accuracy agents (< 70 %), agents doing duplicate work, cost outliers (> 3× workspace average), and underused-memory agents (< 5 stored memories). Insights are classified as `critical / warning / info / success` and surfaced in the dashboard.

### `app/core/predictive_engine.py` — Proactive Agent Spawning

Analyses per-user `UserPattern` records (time-of-day, day-of-week, action sequence) to produce `Prediction` objects recommending agents the user will likely need before they ask. Predictions have a confidence score; accepted / dismissed predictions feed back into the pattern model.

### `app/core/swarm_engine.py` — Multi-Agent Collaboration

Agents advertise `AgentCapability` records (skills, trust score, availability). The Swarm Engine matches `SwarmTask` requirements to available agents, assembles teams, enables in-swarm consensus voting, and distributes credit. Agents can hire other agents mid-execution to handle sub-tasks they cannot complete alone.

### `app/core/memory_engine.py` — 4-Tier Memory

Stores and retrieves `MemoryEntry` objects across four tiers:
- **Correction** — highest-priority, immutable user corrections; never decays.
- **Episodic** — individual execution records with semantic embeddings.
- **Procedural** — generalised rules extracted by the Learning Engine.
- **Semantic** — long-term factual knowledge.

Vector similarity search is provided by `app/core/vector_store.py` (FAISS). Memory `strength` values decay over time via `app/tasks/memory_decay.py`.

### `app/core/rag_engine.py` — Retrieval-Augmented Generation

Handles document ingestion: reads files, chunks content, generates embeddings via `app/core/embeddings.py`, and stores them in the FAISS vector store alongside a `Document` metadata record in PostgreSQL. At query time, the RAG Engine retrieves the top-k similar chunks and prepends them to the LLM context window.

### `app/core/rpa_engine.py` — Browser RPA

Records and replays browser automation sequences. Supported `ActionType` values include `click`, `double_click`, `type`, `navigate`, `wait`, `screenshot`, `select`, `hover`, `drag_drop`, `assert_text`, `extract_text`, `conditional`, and `loop`. The engine can generate executable Playwright scripts from recorded sessions.

### `app/core/billing.py` — Usage Metering and Quotas

Tracks LLM token consumption, agent execution counts, file storage, and team seat usage. Enforces plan limits for `FREE / STARTER / PRO / ENTERPRISE` tiers. Quota guards are checked before execution in cooperation with `app/core/quota_engine.py`.

### `app/core/feature_flags.py` — Controlled Rollouts

`FeatureFlagEngine` stores `FeatureFlag` objects in the `engine_state` table via `app/core/engine_state_store.py`. Flags support three scopes: `global`, `workspace`, and `user`. Each flag has a `rollout_pct` (0–100) for percentage-based rollouts. Evaluation is O(1) with in-memory caching; the cache is invalidated on flag updates.

### `app/core/guardrails.py` — Pre-Execution Safety

`GuardrailEngine` evaluates a set of built-in and user-defined rules before any agent action executes. Built-in rules block mass-email (> 10 recipients), warn on cost > $1.00, require approval for `delete` operations, block PII in output, and enforce rate limits. Custom rules can be added at runtime.

### `app/core/system_control.py` — Authorised Admin Operations

Provides privileged system-management operations (process listing, resource usage, authorised command execution) for admin users. All operations are fully audited via `app/core/audit_log.py`. Uses `psutil` when available for system metrics.

### `app/core/collaboration.py` — Multi-Agent Discussion Rooms

`CollaborationRoom` objects hold `RoomMessage` threads where agents (and users) can exchange `discussion`, `proposal`, `decision`, `question`, and `answer` typed messages. Rooms are used by the Swarm Engine for in-team deliberation.

### `app/core/metrics.py` — Prometheus Instrumentation

Exposes `prometheus_client` counters and histograms:
- `gnosis_http_requests_total` — labelled by method, endpoint, status.
- `gnosis_agent_executions_total` — labelled by status.
- `gnosis_llm_requests_total` — labelled by provider, tier.
- `gnosis_memory_ops_total` — labelled by operation, tier.
- `gnosis_auth_events_total` — labelled by event type.

Metrics are scraped from the `/metrics` endpoint (Prometheus text format).

### `app/core/scheduler.py` & `app/core/task_worker.py`

`scheduler_engine` manages cron-style agent schedules stored in the `schedules` table. `task_worker` is a lightweight in-process periodic task runner used for platform-level housekeeping (memory consolidation, pattern learning, oracle analysis, trust evaluation, memory decay).

---

## Data Stores

### PostgreSQL 16

Primary persistent store, accessed via `SQLAlchemy 2` async engine. The connection URL is set in `DATABASE_URL`. In development and CI, `sqlite+aiosqlite:///./test.db` is used instead. The engine is initialised in `app/core/database.py`; startup degrades gracefully if the database is unavailable ("demo mode" warning logged, `db_available = False`).

**Alembic migrations** live in `backend/alembic/versions/`:
- `001_initial.py` — creates all base tables.
- `002_fix_execution_fields.py` — column adjustments.
- `003_engine_states.py` — adds the `engine_states` table used by `engine_state_store.py`.

Run migrations with:
```bash
cd backend
alembic upgrade head
```

### Redis 7

Used for:
- Response caching in `llm_gateway.py`.
- Rate-limit counters in `app/core/rate_limiter.py`.
- Pub/sub bus for WebSocket multi-instance fan-out (`app/ws/redis_adapter.py`).
- Session store (`app/core/session_store.py`).

Managed by `app/core/redis_client.py` (`redis_manager`). The application starts without Redis if `REDIS_URL` is unreachable — features that require Redis degrade silently.

### FAISS (In-Process Vector Store)

`app/core/vector_store.py` wraps `faiss-cpu` with a per-agent index namespace (`agent_vectors`). Embeddings are generated by `app/core/embeddings.py`. The FAISS index is held in process memory; there is no persistence layer for vectors yet — they are re-indexed from PostgreSQL on restart.

---

## LLM Provider Abstraction

All LLM calls go through `app/core/llm_gateway.py`. The `LLMGateway.complete()` method selects a provider and model tier from `PROVIDER_CONFIGS`, applies caching (keyed on SHA-256 of the prompt), and falls back to the next available tier on error. Supported providers: `openrouter`, `openai`, `anthropic`, `google`, `mistral`, `groq`, `cohere`, `together`, `ollama`. Provider API keys are configured via env vars in `app/config.py` (`OPENROUTER_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`). The Ollama bridge (`app/core/ollama_bridge.py`) enables local model serving without an API key.

---

## Feature Flag System

`app/core/feature_flags.py` defines `FeatureFlagEngine` (singleton: `feature_flag_engine`). Flags are persisted in the `engine_states` Postgres table (keyed on `"feature_flags"` entity namespace) via `app/core/engine_state_store.py`, so they survive restarts without a dedicated table. The HTTP API at `/api/v1/feature-flags` provides CRUD operations. Evaluation via `feature_flag_engine.is_enabled(flag_name, entity_id)` is O(1) with an in-memory dict; flag creation/updates invalidate the in-memory cache.

---

## Observability

### Metrics

`app/core/metrics.py` registers Prometheus counters, histograms, and gauges. `MetricsMiddleware` (added in `main.py`) records each request automatically. The `/metrics` endpoint returns `text/plain; version=0.0.4` Prometheus exposition format. The `docker-compose.yml` Prometheus service scrapes `http://backend:8000/metrics` every 15 seconds. Grafana is provisioned with a pre-built dashboard in `infra/grafana/dashboards/`.

### Structured Logging

`app/core/logger.py` (`setup_logging` / `get_logger`) configures Python's `logging` module with structured JSON output at the level set by `LOG_LEVEL` (default `INFO`). Every log record includes timestamp, level, logger name, and message. In production (ECS), logs flow to CloudWatch Logs (`/ecs/gnosis-<env>/backend`).

### Sentry

Sentry integration is available via `app/core/sentry_integration.py`. Set `SENTRY_DSN` to activate it.

### Tracing

`app/core/tracing.py` and `app/core/trace_sampler.py` provide hooks for distributed tracing. AWS X-Ray is provisioned in `infra/terraform/xray.tf`.

---

## Deployment: AWS Architecture

All infrastructure is defined in `infra/terraform/`. Key resources:

| Resource | Terraform file | Notes |
|----------|---------------|-------|
| ECS Cluster (Fargate) | `ecs.tf` | Container Insights enabled; uses FARGATE + FARGATE_SPOT |
| Application Load Balancer | `alb.tf` | HTTPS with WAF attached |
| CloudFront CDN | `cloudfront.tf` | Fronts both ALB and S3 static assets |
| RDS PostgreSQL 16 | `rds.tf` | Multi-AZ, gp3 storage, encrypted at rest |
| ElastiCache Redis 7 | `elasticache.tf` | Replication group for HA |
| VPC + subnets | `vpc.tf` | Public + private subnets across AZs |
| WAF | `waf.tf` | Attached to ALB and CloudFront |
| IAM roles | `iam.tf`, `aws-services-iam.tf` | Task execution role, secrets access |
| Secrets Manager | `secrets.tf` | DB password, API keys — referenced as ECS secrets |
| SQS | `sqs.tf` | Execution queue (`SQS_EXECUTION_QUEUE_URL`), webhook queue |
| DynamoDB | `dynamodb.tf` | Execution records, session store |
| S3 | `s3.tf` | File uploads (`S3_UPLOAD_BUCKET`), exports |
| Cognito | `cognito.tf` | Optional user pool (enterprise deployments) |
| CloudTrail | `cloudtrail.tf` | API audit logs |
| KMS | `kms.tf` | Encryption keys for RDS and S3 |
| Lambda | `lambda.tf` | Auxiliary functions (e.g. SQS consumers) |
| Route 53 | `route53.tf` | DNS records |
| SNS | `sns.tf` | Alert notifications |
| SSM | `ssm.tf` | Parameter store for config |

Deployment is triggered via `deploy.sh` which builds and pushes Docker images to ECR, then runs `terraform apply`.

Remote Terraform state is **not yet configured** (the `backend "s3"` block in `main.tf` is commented out). State is currently stored locally — this should be migrated to an S3 backend before production use.
