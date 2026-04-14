# Gnosis — AWS Infrastructure with Terraform

This directory contains the complete AWS infrastructure-as-code for the Gnosis
application (FastAPI backend + Next.js frontend).

---

## Architecture Overview

```
Internet
   │
   ▼
CloudFront (CDN, static cache)          ← optional, requires domain_name
   │
   ▼
Application Load Balancer (ALB)
   ├── /api/*  →  ECS Backend  (FastAPI, port 8000)
   └── /*      →  ECS Frontend (Next.js, port 3000)

Private Subnets:
   ├── RDS PostgreSQL 16
   └── ElastiCache Redis 7

Secrets Manager: DATABASE_URL, REDIS_URL, SECRET_KEY, OPENROUTER_API_KEY
ECR: gnosis-backend, gnosis-frontend
```

---

## Prerequisites

| Tool      | Version  | Install guide |
|-----------|----------|---------------|
| AWS CLI   | v2       | https://docs.aws.amazon.com/cli/latest/userguide/install-cliv2.html |
| Terraform | ≥ 1.5    | https://developer.hashicorp.com/terraform/install |
| Docker    | ≥ 24     | https://docs.docker.com/get-docker/ |
| An AWS account with admin permissions | — | — |

Make sure the AWS CLI is configured:

```bash
aws configure          # enter Access Key, Secret, region (us-east-1)
aws sts get-caller-identity   # verify it works
```

---

## Step 1 — Configure Variables

```bash
cd infra/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` and set your values. At minimum:

| Variable            | Required? | Notes |
|---------------------|-----------|-------|
| `region`            | Yes       | Default: `us-east-1` |
| `environment`       | Yes       | `dev`, `staging`, or `prod` |
| `openrouter_api_key`| Yes       | Your OpenRouter API key |
| `domain_name`       | No        | Leave empty for HTTP-only dev |

> **Security**: Never commit `terraform.tfvars` to git — it may contain secrets.

---

## Step 2 — Deploy Infrastructure

```bash
# Initialize Terraform (downloads providers)
terraform init

# Preview what will be created
terraform plan

# Apply — type 'yes' when prompted
terraform apply
```

This takes **10–15 minutes** (RDS and ElastiCache are slow to provision).

After completion, Terraform prints outputs:

```
alb_dns_name     = "gnosis-dev-alb-123456.us-east-1.elb.amazonaws.com"
ecr_backend_url  = "123456789.dkr.ecr.us-east-1.amazonaws.com/gnosis-backend"
ecr_frontend_url = "123456789.dkr.ecr.us-east-1.amazonaws.com/gnosis-frontend"
```

---

## Step 3 — Push Docker Images to ECR

```bash
# Authenticate Docker with ECR
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
AWS_REGION=$(terraform output -raw region 2>/dev/null || echo "us-east-1")

aws ecr get-login-password --region $AWS_REGION | \
  docker login --username AWS --password-stdin $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com

# Build and push backend
cd ../../backend
docker build -t gnosis-backend .
docker tag gnosis-backend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/gnosis-backend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/gnosis-backend:latest

# Build and push frontend
cd ../frontend
docker build -t gnosis-frontend .
docker tag gnosis-frontend:latest $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/gnosis-frontend:latest
docker push $AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/gnosis-frontend:latest
```

---

## Step 4 — Force ECS to Pick Up New Images

```bash
cd ../infra/terraform

CLUSTER=$(terraform output -raw ecs_cluster_name)

aws ecs update-service --cluster $CLUSTER --service gnosis-dev-backend  --force-new-deployment
aws ecs update-service --cluster $CLUSTER --service gnosis-dev-frontend --force-new-deployment
```

---

## Step 5 — Verify Deployment

```bash
ALB_DNS=$(terraform output -raw alb_dns_name)

# Backend health check
curl -s http://$ALB_DNS/api/v1/health

# Frontend
curl -sI http://$ALB_DNS/
```

Check the ECS console or CloudWatch Logs for container logs:

```bash
aws logs tail /ecs/gnosis-dev/backend --follow
aws logs tail /ecs/gnosis-dev/frontend --follow
```

---

## Cost Estimate (Minimal Dev Setup)

| Service        | Monthly Estimate |
|----------------|-----------------|
| ECS Fargate    | ~$25            |
| RDS (db.t3.micro) | ~$15        |
| ElastiCache    | ~$12            |
| NAT Gateway    | ~$32            |
| ALB            | ~$16            |
| ECR            | ~$1             |
| Secrets Manager| ~$2             |
| CloudWatch     | ~$1             |
| **Total**      | **~$50–$100/mo**|

> **Tip**: The NAT Gateway is the largest fixed cost. For personal dev you
> could remove it and use public subnets for ECS, though that's less secure.

---

## Tear Down Everything

```bash
# Remove all infrastructure (type 'yes' when prompted)
terraform destroy
```

> **Warning**: This deletes the database and all data. For production, enable
> `deletion_protection` on RDS and set `prevent_destroy = true` in lifecycle
> blocks before deploying.

---

## Production Checklist

Before going to production, update these settings:

- [ ] `deletion_protection = true` on RDS
- [ ] `lifecycle { prevent_destroy = true }` on RDS and ElastiCache
- [ ] `multi_az = true` on RDS
- [ ] `num_cache_clusters = 2` + `automatic_failover_enabled = true` on Redis
- [ ] Configure a real `domain_name` and validate the ACM certificate
- [ ] Enable Terraform remote state (S3 + DynamoDB) — see `main.tf`
- [ ] Set `environment = "prod"` and `LOG_LEVEL` to `WARNING`
- [ ] Review and tighten IAM policies
- [ ] Enable RDS Performance Insights
- [ ] Set up CloudWatch alarms and SNS notifications
- [ ] Enable WAF on ALB/CloudFront
