# Gnosis Deployment Guide

Step-by-step procedures for deploying Gnosis to production AWS ECS infrastructure.

## Prerequisites

- AWS Account with permissions to: ECS, RDS, ElastiCache, EC2, IAM, Secrets Manager
- Terraform ≥ 1.5
- Docker installed locally
- `aws` CLI configured with credentials
- Repository cloned and latest code pulled

## Pre-Deployment Checklist

Before any deployment, verify:

- [ ] All PHASE 1 tests passing: `cd backend && pytest tests/ -v`
- [ ] Type checking clean: `cd backend && mypy app/core/ --config-file=pyproject.toml`
- [ ] Frontend builds: `cd frontend && npm run build`
- [ ] Database migrations tested: `cd backend && alembic upgrade head` (with test DB)
- [ ] Environment variables documented: all required secrets in `.env.example`
- [ ] Secrets exist in AWS Secrets Manager (never commit secrets)
- [ ] Feature flags configured for gradual rollout
- [ ] Monitoring dashboards ready in Grafana
- [ ] `GNOSIS_AUTO_API_ALLOWED_HOSTS` set (see [Auto-API outbound allowlist](#auto-api-outbound-allowlist))

## Auto-API outbound allowlist

The `/api/v1/apis/connections/{id}/call` endpoint can issue outbound HTTP
requests to third-party APIs. To prevent SSRF and abuse, the endpoint enforces:

- A per-user rate limit (30 calls/minute).
- A host allowlist read from the env var **`GNOSIS_AUTO_API_ALLOWED_HOSTS`**
  (comma-separated hostnames, e.g.
  `GNOSIS_AUTO_API_ALLOWED_HOSTS=api.stripe.com,api.github.com`). Subdomains
  of allowed hosts are accepted.
- A hard block on private, loopback, link-local, multicast, reserved, and
  unresolvable hostnames (DNS-resolved before the call).

In production (`DEBUG=false`) an empty allowlist disables the endpoint
entirely (every call returns 403). In development (`DEBUG=true`) an empty
allowlist logs a warning but allows the call so local testing is not blocked.

## Deployment Procedure

> **Immutable image tags (policy)**
> Production does not publish or consume the `:latest` tag. CI (`.github/workflows/deploy.yml`) and `deploy.sh` push only immutable git-SHA tags, and `docker-compose.prod.yml` requires `IMAGE_TAG` to be explicitly set (`${IMAGE_TAG:?…}`). Roll forward and roll back by exporting the exact SHA you want (`export IMAGE_TAG=<git-sha>`) before `docker compose … up -d` or before the ECS task-definition update. CI uses a test-only fallback secret when `CI_SECRET_KEY` is absent; production deployments must always set real secrets through the hosting provider or AWS Secrets Manager.

### 1. Build Backend Docker Image

```bash
cd backend

# Set build variables — IMAGE_TAG MUST be the git SHA (immutable). No :latest.
export IMAGE_TAG="$(git rev-parse --short HEAD)"
export AWS_REGION="us-east-1"
export AWS_ACCOUNT_ID="$(aws sts get-caller-identity --query Account --output text)"
export ECR_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/gnosis-backend"

# Login to ECR
aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $ECR_REPO

# Build and push (SHA tag only — :latest is intentionally NOT published)
docker build -t $ECR_REPO:$IMAGE_TAG .
docker push $ECR_REPO:$IMAGE_TAG

echo "✅ Backend image pushed: $ECR_REPO:$IMAGE_TAG"
```

### 2. Build Frontend Docker Image

```bash
cd ../frontend

export FRONTEND_REPO="$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/gnosis-frontend"

# Build and push (SHA tag only — :latest is intentionally NOT published)
docker build -t $FRONTEND_REPO:$IMAGE_TAG .
docker push $FRONTEND_REPO:$IMAGE_TAG

echo "✅ Frontend image pushed: $FRONTEND_REPO:$IMAGE_TAG"
```

### 3. Run Database Migrations

```bash
cd ../backend

# Set production database connection
export DATABASE_URL="postgresql+asyncpg://$(aws secretsmanager get-secret-value \
  --secret-id gnosis-db-creds --query SecretString --output text | jq -r .username):$(aws secretsmanager get-secret-value \
  --secret-id gnosis-db-creds --query SecretString --output text | jq -r .password)@gnosis-prod-postgres.c9akciq32.us-east-1.rds.amazonaws.com:5432/gnosis"

# Create backup snapshot first (safety)
aws rds create-db-snapshot \
  --db-instance-identifier gnosis-prod-postgres \
  --db-snapshot-identifier "gnosis-prod-backup-$(date +%Y%m%d-%H%M%S)"

# Run migrations
alembic upgrade head

# Verify schema
alembic current

echo "✅ Database migrations completed"
```

### 4. Plan Infrastructure Changes

```bash
cd ../infra/terraform

# Initialize Terraform (if not already done)
terraform init

# Plan changes
terraform plan \
  -var="environment=prod" \
  -var="backend_image=$ECR_REPO:$IMAGE_TAG" \
  -var="frontend_image=$FRONTEND_REPO:$IMAGE_TAG" \
  -out=tfplan

# Review output carefully
# Should show: 0 to add, 0 to change, 0 to destroy (for image-only updates)
```

### 5. Apply Terraform Changes

```bash
# Apply with confirmation
terraform apply tfplan

# Monitor ECS task startup
aws ecs describe-services \
  --cluster gnosis-prod \
  --services backend \
  --query 'services[0].deployments' \
  --output table

echo "✅ Terraform applied successfully"
```

### 6. Verify Deployment Health

```bash
# Get load balancer DNS
export ALB_DNS=$(aws elbv2 describe-load-balancers \
  --names gnosis-prod-alb \
  --query 'LoadBalancers[0].DNSName' \
  --output text)

# Health check endpoint
curl -I "http://$ALB_DNS/api/v1/health"
# Expected: HTTP/1.1 200 OK

# Check backend logs for errors
aws logs tail /ecs/gnosis-prod/backend --follow --since 1m

# Check Grafana metrics (if available)
echo "Visit: http://grafana-prod.gnosis.local:3001"
echo "Check dashboards: Backend Health, ECS Tasks, Database"

echo "✅ Deployment health verified"
```

### 7. Monitor First Hour

```bash
# Watch error rate
watch -n 10 'aws cloudwatch get-metric-statistics \
  --namespace gnosis \
  --metric-name http_requests_total \
  --statistics Sum \
  --start-time $(date -u -d "10 minutes ago" +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60'

# Monitor ECS task status
watch -n 5 'aws ecs describe-services \
  --cluster gnosis-prod \
  --services backend frontend \
  --query "services[*].[serviceName,deployments[0].runningCount,deployments[0].desiredCount]" \
  --output table'

# Check for database connection issues
aws logs filter-log-events \
  --log-group-name /ecs/gnosis-prod/backend \
  --filter-pattern "database\|connection" \
  --start-time $(date -d '10 minutes ago' +%s000)

echo "⚠️  If errors spike > 5% of traffic, proceed to Rollback"
```

## Rollback Procedure

If deployment issues detected, rollback immediately:

### Code Rollback (ECS)

```bash
# Force new deployment using previous image
aws ecs update-service \
  --cluster gnosis-prod \
  --service backend \
  --force-new-deployment

# Or revert to specific image tag
aws ecs update-service \
  --cluster gnosis-prod \
  --service backend \
  --task-definition gnosis-backend:PREVIOUS_VERSION

# Monitor rollout
aws ecs describe-services \
  --cluster gnosis-prod \
  --services backend \
  --query 'services[0].deployments'

echo "✅ Code rollback completed"
```

### Database Rollback (if migration failed)

```bash
# Restore from snapshot created before migration
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier gnosis-prod-postgres-restored \
  --db-snapshot-identifier "gnosis-prod-backup-TIMESTAMP" \
  --no-multi-az

# Update DNS to point to restored instance (requires manual DNS update)

# Revert code to previous version first
```

### Terraform Rollback

```bash
cd infra/terraform

# Show previous state
terraform show

# Revert to previous state version (if using remote state)
terraform state pull > terraform.state.backup

# Or manually revert to previous variable values
terraform apply -var="backend_image=$ECR_REPO:PREVIOUS_TAG"
```

## Post-Deployment Verification

After successful deployment, verify:

```bash
# 1. API endpoints responding
curl -H "Authorization: Bearer $TEST_TOKEN" \
  "http://$ALB_DNS/api/v1/agents"

# 2. Database connectivity
curl "http://$ALB_DNS/api/v1/health" | jq .database

# 3. Redis cache working
# Check agent creation latency (should be < 500ms)

# 4. Frontend assets loaded
curl -s "http://$ALB_DNS/" | grep -i "webpack"

# 5. Webhook infrastructure ready
# Test webhook delivery: POST /api/v1/webhooks/test

# 6. Metrics collected
# Verify Prometheus scrape: http://prometheus:9090/targets

# 7. Logs flowing
# Check CloudWatch log streams have recent entries

echo "✅ All post-deployment checks passed"
```

## Common Issues & Solutions

### ECS Task Failed to Start

**Symptoms**: Task shows `STOPPED` with reason like "Essential container exited"

**Solutions**:
```bash
# Check container logs
aws ecs describe-tasks \
  --cluster gnosis-prod \
  --tasks <task-arn> \
  --query 'tasks[0].containers[*].[name, lastStatus, stopCode, stoppedReason]'

# Common causes:
# - Missing env var: Check AWS Secrets Manager has all required keys
# - Image not found: Verify ECR image exists and tag is correct
# - Database unavailable: Check RDS security group allows ECS task SG
```

### Database Migration Timeout

**Symptoms**: `alembic upgrade head` hangs or times out

**Solutions**:
```bash
# Increase timeout
alembic upgrade head --sql  # Generate SQL without running
# Review SQL for long operations

# Or run in smaller batches
alembic upgrade +1  # Run one migration at a time

# Check for locks
psql -h $DB_HOST -U $DB_USER -d gnosis -c "SELECT * FROM pg_locks;"
```

### High Error Rate After Deploy

**Symptoms**: 5xx errors spike, ALB health checks start failing

**Solutions**:
1. Check logs for specific error: `aws logs tail /ecs/gnosis-prod/backend --follow`
2. Verify environment variables: `aws ecs describe-task-definition --task-definition gnosis-backend:CURRENT`
3. Check feature flags: `curl http://$ALB_DNS/api/v1/feature-flags`
4. If > 5 minutes of errors, execute rollback procedure above

## Monitoring During Deployment

Key metrics to watch:

| Metric | Good | Concerning | Critical |
|--------|------|------------|----------|
| HTTP 5xx rate | < 0.1% | 0.1-1% | > 1% |
| API latency p99 | < 500ms | 500-2000ms | > 2s |
| Database connections | < 50% of pool | 50-80% | > 80% |
| Memory usage | < 60% | 60-80% | > 80% |
| Running tasks | = desired | > desired | < desired |

## Emergency Contacts

If deployment goes wrong:

- **Ops Lead**: Page ops-oncall via PagerDuty
- **Database Admin**: Notify in #database-incidents Slack channel
- **Infrastructure**: Contact infrastructure-team@gnosis.local

## Documentation

After successful deployment, update:

- [ ] RUNBOOK.md with any new procedures discovered
- [ ] Deployment timestamps in project wiki
- [ ] Rollback test results (optional but recommended)
- [ ] Any infrastructure changes in code comments

## See Also

- [RUNBOOK.md](../RUNBOOK.md) — On-call operational procedures
- [SECURITY.md](../SECURITY.md) — Security considerations
- [ARCHITECTURE.md](../ARCHITECTURE.md) — System design details
- [infra/terraform/README.md](../infra/terraform/README.md) — IaC documentation
