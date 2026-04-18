# Gnosis Runbook

Operational reference for on-call engineers. Keep this document up-to-date whenever you change infrastructure or alert thresholds.

---

## On-Call Basics

### Where logs live

| Environment | Location | How to access |
|-------------|----------|---------------|
| Local / Docker | `docker-compose logs -f backend` | stdout |
| Production (ECS) | CloudWatch Logs: `/ecs/gnosis-<env>/backend` | AWS Console → CloudWatch → Log Groups, or `aws logs tail /ecs/gnosis-prod/backend --follow` |
| Frontend (ECS) | CloudWatch Logs: `/ecs/gnosis-<env>/frontend` | same as above |

All backend log lines are structured JSON. Key fields: `timestamp`, `level`, `logger`, `message`. Filter by level with:

```bash
aws logs filter-log-events \
  --log-group-name /ecs/gnosis-prod/backend \
  --filter-pattern '{ $.level = "ERROR" }' \
  --start-time $(date -d '1 hour ago' +%s000)
```

### Where metrics live

- **Prometheus** — `http://<host>:9090` (local) or the internal ALB DNS in production.
- **Grafana** — `http://<host>:3001` (local, admin/gnosis) or the provisioned Grafana ECS service in production.
- **Application metrics endpoint** — `GET http://localhost:8000/metrics` (Prometheus text format). Useful for quick spot-checks:
  ```bash
  curl -s http://localhost:8000/metrics | grep gnosis_
  ```

Key metrics to watch:

| Metric | Alert threshold | Meaning |
|--------|----------------|---------|
| `gnosis_http_requests_total{status=~"5.."}` | > 1 % of total over 5 min | Backend errors |
| `gnosis_agent_executions_total{status="failed"}` | > 10 % of total over 5 min | Agent failure spike |
| `gnosis_llm_requests_total` rate drop | > 50 % drop vs 24h avg | LLM provider outage |
| `gnosis_auth_events_total{event="failed"}` | > 100/min | Brute-force attempt |
| Container memory usage | > 80 % of limit | Memory pressure |

### Where the health endpoint lives

```
GET http://localhost:8000/api/v1/health
```

Returns `{"status": "ok"}` when the backend is healthy. The ALB health check uses this path.

---

## Common Alerts and First-Response Steps

### 5xx Spike

1. Check recent deployments: `git log --oneline -5 origin/main` — was there a release in the last hour?
2. Hit the health endpoint: `curl http://localhost:8000/api/v1/health`. If it returns non-200, the app is down.
3. Check database connectivity: look for `PostgreSQL unavailable` in logs. If present, see **DB Down** below.
4. Check for tracebacks in CloudWatch: filter on `"ERROR"` or `"Traceback"`.
5. If a bad deploy is confirmed, follow the **Rollback Procedure** below.
6. If the error is isolated to a specific route, check whether a recent migration broke the schema: `alembic current` vs `alembic heads`.

### Memory Pressure

1. Identify which container is over the limit: ECS console → cluster → task → Container tab.
2. Check agent execution loops: large numbers of concurrent agent executions will spike memory. Look at `gnosis_agent_executions_total` rate.
3. Check memory GC status: `GET /api/v1/memory-gc/status` (admin auth required). If GC is backlogged, trigger manually: `POST /api/v1/memory-gc/run`.
4. If Redis is holding too much data: `redis-cli info memory` — check `used_memory_human`. The Docker Compose configuration caps Redis at 128 MB with `allkeys-lru` eviction.
5. If pressure persists, scale up the ECS task memory limit in `infra/terraform/ecs.tf` → `terraform apply`.

### Auth Failure Spike

1. Check `gnosis_auth_events_total{event="failed"}` rate in Grafana.
2. Look for a single source IP: CloudWatch Logs → filter on `"auth"` + `"failed"` and check the `client_ip` field.
3. If brute-force is confirmed, block the IP at the WAF: AWS Console → WAF → Web ACLs → IP sets → add IP.
4. Verify rate-limiting is active: `app/core/rate_limiter.py` enforces `RATE_LIMIT_PER_MINUTE` (default 100). Check whether the env var is set in production.
5. Check for valid tokens being rejected: could indicate `SECRET_KEY` mismatch after a secret rotation (see **Secrets Rotation** below).

### LLM Provider Outage

1. Check OpenRouter status: https://status.openrouter.ai (primary provider).
2. Check individual provider status pages (OpenAI, Anthropic) if relevant models are affected.
3. The `LLMGateway` has tier-based fallback: if `balanced` tier fails it falls back to `fast`. Confirm fallback is happening by checking `gnosis_llm_requests_total{tier}` breakdown.
4. If the primary provider (`OPENROUTER_API_KEY`) is exhausted or unreachable, set `DEFAULT_LLM_PROVIDER=anthropic` or `DEFAULT_LLM_PROVIDER=openai` in the ECS task environment and trigger a new deployment.
5. If Ollama is available locally, set `DEFAULT_LLM_PROVIDER=ollama` and `OLLAMA_BASE_URL` for a degraded but functional service.

---

## Rollback Procedure

### Code rollback

```bash
# 1. Find the last good commit
git log --oneline origin/main | head -10

# 2. Create a revert commit
git revert <bad-commit-sha> --no-edit
git push origin main

# 3. CI will run automatically; once green, the new deployment will start
```

If the revert cannot be cleanly applied (merge conflicts), check out the last good tag/SHA into a hotfix branch:

```bash
git checkout -b fix/emergency-rollback <last-good-sha>
# make the fix, commit, open PR
```

### Infrastructure rollback (Terraform)

```bash
cd infra/terraform

# Review what changed
terraform plan

# Roll back to a previous state (use with caution — state must be clean)
# If state is in S3 (once configured):
#   aws s3 cp s3://gnosis-terraform-state/terraform.tfstate.backup ./terraform.tfstate

terraform apply -target=aws_ecs_service.backend   # re-apply specific resource
```

> **Note:** Terraform remote state is not yet configured (the S3 backend block in `infra/terraform/main.tf` is commented out). Until it is enabled, state is local only. Coordinate rollbacks manually if multiple engineers are involved.

---

## Database Operations

### Run migrations

```bash
cd backend
export DATABASE_URL="postgresql+asyncpg://gnosis:<password>@<host>:5432/gnosis"
alembic upgrade head
```

### Roll back one migration

```bash
alembic downgrade -1
```

### Roll back to a specific revision

```bash
alembic downgrade 002_fix_execution_fields
```

### Show current migration state

```bash
alembic current
alembic history --verbose
```

### Backup expectations

> **TBD** — Automated RDS snapshots are not yet configured in Terraform. The `rds.tf` file provisions the database but does not set `backup_retention_period` > 0 or schedule automated snapshots. Until this is resolved:
>
> - Take a manual snapshot before every production migration: AWS Console → RDS → DB instance → Actions → Take snapshot.
> - Alternatively, use `pg_dump`: `pg_dump -h <host> -U gnosis -d gnosis -Fc > gnosis_$(date +%Y%m%d).dump`

### Restore from dump

```bash
pg_restore -h <host> -U gnosis -d gnosis -Fc gnosis_<date>.dump
```

---

## Secrets Rotation

### SECRET_KEY (JWT signing key)

Rotating `SECRET_KEY` invalidates **all existing JWT tokens**. All logged-in users will be signed out.

1. Generate a new key: `openssl rand -hex 32`
2. Update the secret in AWS Secrets Manager (referenced by ECS task definition as `SECRET_KEY`).
3. Trigger a new ECS deployment: `aws ecs update-service --cluster gnosis-prod --service backend --force-new-deployment`
4. Monitor auth events: after the rollout, watch `gnosis_auth_events_total{event="failed"}` — a spike is expected as cached tokens expire. It should normalise within `ACCESS_TOKEN_EXPIRE_MINUTES` (default 30 min).

### LLM API keys (OPENROUTER_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY)

1. Generate a new key in the respective provider dashboard.
2. Update the secret in AWS Secrets Manager.
3. Force a new ECS deployment (same command as above).
4. Revoke the old key in the provider dashboard **after** confirming the new deployment is healthy.

### Database password (POSTGRES_PASSWORD)

1. Update the RDS master password: `aws rds modify-db-instance --db-instance-identifier gnosis-prod-postgres --master-user-password <new-pass> --apply-immediately`
2. Update Secrets Manager with the new password.
3. Force a new ECS backend deployment so the app picks up the new `DATABASE_URL`.
4. Verify connectivity: `curl http://localhost:8000/api/v1/health` should return 200.

### Google / GitHub OAuth secrets

1. Rotate in Google Cloud Console / GitHub OAuth App settings.
2. Update `GOOGLE_CLIENT_SECRET` / `GITHUB_CLIENT_SECRET` in Secrets Manager.
3. Force a new ECS deployment.

---

## Recovery from Common Failure Modes

### Database (PostgreSQL) Down

1. Check RDS instance status: AWS Console → RDS → DB instances → check `Available` status.
2. If a Multi-AZ failover is in progress, wait — it typically completes in 60–120 seconds and the app will reconnect automatically (SQLAlchemy will retry on the next request; `db_available` is re-evaluated at startup).
3. If the RDS instance is stopped: `aws rds start-db-instance --db-instance-identifier gnosis-prod-postgres`
4. If connectivity is blocked: check the security group in `infra/terraform/security_groups.tf` — the ECS task SG must be allowed on port 5432.
5. The backend runs in "demo mode" when the database is unavailable (logged as `PostgreSQL unavailable — running in demo mode`). API responses that require the database will return 503.

### Redis Down

1. Check ElastiCache replication group status: AWS Console → ElastiCache → Redis clusters.
2. The application degrades gracefully: rate limiting falls back to in-memory counters, caching is bypassed, WebSocket fan-out is limited to the current instance.
3. To force a Redis reconnection without restarting the backend: the `redis_manager` reconnects automatically on the next operation after a failed ping.
4. If the Redis endpoint has changed (e.g. after a cluster recreation), update `REDIS_URL` in Secrets Manager and force a new ECS deployment.

### LLM Provider Outage

See **LLM Provider Outage** under Common Alerts above.

### ECS Task Crash Loop

1. Check the stopped task reason: ECS Console → cluster → Tasks tab → stopped task → Stopped reason.
2. Check logs: CloudWatch `/ecs/gnosis-<env>/backend` — look for the `FATAL` or unhandled exception that caused the crash.
3. Common causes: missing required env var (`SECRET_KEY` not set and `DEBUG=false`), migration not run (SQLAlchemy can't find a table), out-of-memory (increase task memory in `ecs.tf`).
4. Fix and redeploy; do not lower the desired task count to 0 unless you are intentionally taking the service down.

---

## Escalation Path

1. **On-call engineer** — first response, follow steps in this runbook.
2. **Backend lead** — escalate if the issue cannot be resolved in 30 minutes or requires a code change.
3. **Infrastructure** — escalate for AWS-level issues (RDS failover, ECS capacity, WAF false positives).
4. **Provider support** — escalate to OpenRouter / AWS Support for outages outside our control.

For P0 incidents (complete service unavailability): page the on-call lead directly; do not wait for Slack.
