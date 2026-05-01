# Gnosis Troubleshooting FAQ

Quick fixes for the most common issues. If your problem isn't here, open a GitHub issue.

---

## Setup & Installation

### Q: `docker-compose up` fails with "port already in use"
Another service is using port 8000, 3000, 5432 or 6379. Either stop it, or override the port:
```bash
BACKEND_PORT=8080 FRONTEND_PORT=3001 docker-compose up
```

### Q: Backend container exits immediately
Run `docker-compose logs backend` and look for the first ERROR line. Common causes:
- Missing environment variables → run `python3 backend/scripts/validate_secrets.py --environment dev`
- Database not ready → wait 10s and re-run; the backend retries 5 times by default
- Migration mismatch → `docker-compose exec backend alembic upgrade head`

### Q: `alembic upgrade head` fails with "target database is not up to date"
The DB has migrations the codebase doesn't know about (someone else applied newer ones). Either:
- Pull latest: `git pull && docker-compose build backend`
- Or rollback: `alembic downgrade -1` then upgrade again

---

## Authentication

### Q: I get `401 Unauthorized` on every request
Your JWT expired (default lifetime: 30 minutes). Re-login:
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"...","password":"..."}'
```
For long-running scripts use an **API key** instead — they don't expire.

### Q: Google/GitHub OAuth returns "redirect_uri_mismatch"
The callback URL registered with the OAuth provider must exactly match `OAUTH_REDIRECT_URI`. Common mistake: trailing slash, http vs https, or forgetting to add the staging URL.

### Q: Password reset email never arrives
Check `SMTP_*` environment variables. In dev mode the email is printed to the backend logs instead of sent. Search for `"reset_token"` in `docker-compose logs backend`.

---

## Agents & Execution

### Q: My agent is stuck in `running` state
Likely causes:
1. **LLM provider timeout** — check `docker-compose logs backend | grep llm_gateway`
2. **Tool call hung** — RPA browser tools have a 30s default timeout; increase via `RPA_DEFAULT_TIMEOUT_MS`
3. **Worker crashed** — restart with `docker-compose restart backend`

Force-fail a stuck execution:
```bash
curl -X POST "http://localhost:8000/api/v1/executions/$EXEC_ID/cancel" \
  -H "Authorization: Bearer $TOKEN"
```

### Q: `429 Too Many Requests`
You hit the rate limit (100 req/min default). Wait 60 seconds or upgrade your tier. Check current usage:
```bash
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/api/v1/billing/usage
```

### Q: `LLMError: Invalid API key`
Set the provider key in `.env`:
```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```
Then `docker-compose restart backend`.

### Q: Agent returns gibberish or wrong language
Tighten the system prompt and lower `temperature` (try `0.2`). Check `model` is correct — `claude-3-haiku` is much weaker than `claude-3.5-sonnet`.

---

## RPA / Browser Automation

### Q: RPA action fails with "selector not found"
The page changed or hasn't finished loading. Add an explicit wait:
```json
{"action": "wait_for_selector", "selector": "button.submit", "timeout_ms": 5000}
```

### Q: "Browser context closed unexpectedly"
The headless browser hit OOM. Either reduce concurrent RPA jobs or bump the container memory limit in `docker-compose.yml` (`mem_limit: 2g`).

### Q: Can RPA scripts read/write local files?
**No.** RPA actions are sandboxed to browser interactions only. There is no file-system or shell action type — see `backend/tests/test_rpa_sandbox.py` for the security tests.

---

## Database & Migrations

### Q: "could not connect to server" on first startup
Postgres takes ~5–10s to initialize. The backend retries 5 times. If it still fails, check `docker-compose logs postgres` for "database system is ready to accept connections".

### Q: How do I take a manual backup?
```bash
docker-compose exec postgres pg_dump -U gnosis gnosis > backup-$(date +%F).sql
```
Restore:
```bash
docker-compose exec -T postgres psql -U gnosis gnosis < backup.sql
```

### Q: "FATAL: role does not exist"
DB volume from a previous install. Reset it:
```bash
docker-compose down -v   # WARNING: deletes all data
docker-compose up -d
```

---

## Webhooks

### Q: Webhook never fires
1. Verify the webhook is enabled: `GET /api/v1/webhooks`
2. Check signature verification on your receiver — requests are signed with the secret you provided (header `X-Gnosis-Signature`)
3. Receiver must respond `2xx` within 10s; otherwise we retry 3 times with exponential backoff

### Q: How do I verify the webhook signature?
```python
import hmac, hashlib
expected = hmac.new(SECRET.encode(), body, hashlib.sha256).hexdigest()
assert expected == request.headers["X-Gnosis-Signature"]
```

---

## Production Deployment

### Q: Health check returns `degraded`
At least one component is down. Hit `/api/v1/health/detailed` to see which:
```bash
curl https://your-domain.com/api/v1/health/detailed | jq .components
```
Common: Redis pool exhausted, LLM provider rate-limited, DB connection saturation.

### Q: ECS task keeps cycling
Open CloudWatch logs for the task. Most common cause: the task can't reach the database due to a security-group misconfig. Verify:
```bash
aws ec2 describe-security-groups --group-ids $RDS_SG \
  --query 'SecurityGroups[0].IpPermissions'
```

### Q: How do I roll back a bad deployment?
See [DEPLOYMENT.md](DEPLOYMENT.md) — "Rollback Procedures" section. Short version:
```bash
aws ecs update-service --cluster gnosis-prod --service backend \
  --task-definition gnosis-backend:PREVIOUS_REVISION
```

---

## Performance

### Q: Responses are slow (>5s)
1. Check LLM provider latency in Grafana → `llm_request_duration_seconds`
2. Database slow queries: `docker-compose exec postgres psql -U gnosis -c "SELECT query, mean_exec_time FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"`
3. Increase backend workers: `BACKEND_WORKERS=4` in `.env`

### Q: High memory usage in backend
Most likely the in-memory event bus or audit log. Check `/api/v1/health/detailed` for `audit_entries`. In production set:
```
AUDIT_LOG_RETENTION_DAYS=90
```
And run the prune cron (see `backend/scripts/prune_audit_log.py`).

---

## Still stuck?

- Search existing issues: https://github.com/gauthambinoy/gnosis/issues
- Open a new issue with: `docker-compose logs --tail=200`, your `.env` (with secrets redacted), and exact reproduction steps
- Security concerns: see [SECURITY.md](SECURITY.md) — do not file public issues for vulnerabilities
