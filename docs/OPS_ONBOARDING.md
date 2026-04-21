# Operations Onboarding Checklist

For new on-call engineers joining the Gnosis ops rotation. Allow ~half a day.

## 1. Access (Day 1)

- [ ] GitHub repo: read + push to `main` (require 2FA)
- [ ] AWS console: SSO into `gnosis-prod` and `gnosis-staging` accounts
- [ ] AWS CLI configured locally (`aws configure sso`)
- [ ] PagerDuty: added to `gnosis-oncall` schedule
- [ ] Slack: `#gnosis-ops`, `#gnosis-alerts`, `#gnosis-incidents`
- [ ] 1Password / Vault: access to `gnosis-prod` shared vault
- [ ] Grafana: SSO login at `https://grafana.gnosis.example.com`
- [ ] Sentry: added to the `gnosis` org with `member` role
- [ ] CloudWatch dashboards URL bookmarked

## 2. Local Setup

- [ ] `git clone` and run `docker-compose up`
- [ ] `curl localhost:8000/api/v1/health/detailed` returns `healthy`
- [ ] Run `cd backend && pytest -q` — all green
- [ ] Install Terraform 1.6+ and run `terraform init` in `infra/terraform`
- [ ] Install `psql`, `redis-cli`, `aws`, `jq`

## 3. Read These Documents (in order)

1. [README.md](../README.md) — what Gnosis is
2. [ARCHITECTURE.md](../ARCHITECTURE.md) — components and data flow
3. [DEPLOYMENT.md](../DEPLOYMENT.md) — how to deploy
4. [RUNBOOK.md](../RUNBOOK.md) — incident response procedures
5. [SECURITY.md](../SECURITY.md) — threat model
6. [COMPLIANCE.md](../COMPLIANCE.md) — GDPR / SOC 2 controls

## 4. Shadow a Deployment

- [ ] Watch one staging deploy end-to-end with the current on-call
- [ ] Watch one prod deploy
- [ ] Practice a rollback in staging (`infra/terraform` revert + ECS task definition rollback)

## 5. Run a Fire Drill

- [ ] Trigger a synthetic 5xx burst against staging and verify alerts fire
- [ ] Practice the database restore procedure on staging from the latest snapshot
- [ ] Run an audit log integrity check after manual edit (use `verify_integrity()`)

## 6. Know Your Dashboards

| Dashboard | URL | Watch for |
|-----------|-----|-----------|
| Backend overview | Grafana → "Gnosis Backend" | RPS, p95 latency, 5xx rate |
| LLM gateway | Grafana → "LLM Gateway" | Provider error rate, token usage, retries |
| Database | RDS console → Performance Insights | Connection count, top queries |
| Alerts | Grafana → "Alerting" | All red/yellow alerts |
| Cost | AWS Cost Explorer (saved view "gnosis-prod") | Daily spend trend |

## 7. Critical Runbooks (memorize the entry point)

- API down → `RUNBOOK.md` → "Service Unavailable"
- Database failover → `RUNBOOK.md` → "RDS Failover"
- LLM provider outage → `RUNBOOK.md` → "Provider Failover"
- Secret rotation → `RUNBOOK.md` → "Rotate Credentials"
- DDoS / abuse → `RUNBOOK.md` → "DDoS Mitigation"

## 8. Escalation Path

1. **Tier 1**: You (on-call)
2. **Tier 2**: Backend lead (PagerDuty: `gnosis-backend-secondary`)
3. **Tier 3**: CTO (phone, only for `SEV-1`)

`SEV-1` = customer data at risk OR full outage > 15 min.

## 9. First Week On-Call Goals

- [ ] Respond to at least one real alert (with shadow support)
- [ ] Close one ops follow-up issue in GitHub
- [ ] Add one improvement to this checklist (it should always grow)

## 10. Sign-Off

When all the boxes above are checked, post in `#gnosis-ops`:

> ✅ @your-handle has completed ops onboarding and is on the rotation as of `YYYY-MM-DD`.

The previous on-call lead approves with a 👍 and you're in.

## Reading the request-audit buffer

The per-request audit middleware (`backend/app/middleware/audit_log.py`)
persists every captured request to durable storage so records survive process
restarts.

**Primary store — Redis list**

- Key: `gnosis:audit:requests`
- Encoding: one JSON document per entry (`LPUSH` head = newest)
- Cap: 10 000 entries (enforced via `LTRIM 0 9999` on each write)

Quick peek from a shell on any pod:

```bash
redis-cli -u "$REDIS_URL" LRANGE gnosis:audit:requests 0 49 | jq .
redis-cli -u "$REDIS_URL" LLEN   gnosis:audit:requests
```

**Fallback store — Postgres table** `request_audit_log`

Written to whenever Redis is unavailable. Schema is defined by
`app/models/audit.py` and created by Alembic migration
`004_request_audit_log`.

```sql
SELECT timestamp, method, path, status_code, latency_ms, user_id
FROM   request_audit_log
ORDER  BY timestamp DESC
LIMIT  100;
```

**Operator API**

The same view is exposed over HTTP at `GET /api/v1/audit/recent` which reads
from Redis first and transparently falls back to the database, so ops never
needs to know which backend currently has the data.

**Alerting on Redis outage**

Persistence failures during a Redis outage are logged at WARNING level with
the prefix `audit.redis_write_failed` / `audit.redis_read_failed`. Alert on a
sustained rate of these lines — during an outage the DB fallback keeps
durability intact but write latency and DB load will rise.
