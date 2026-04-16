#!/usr/bin/env bash
set -euo pipefail

# ─── Configuration ───────────────────────────────────────────────────────────
AWS_REGION="${AWS_REGION:-us-east-1}"
AWS_ACCOUNT_ID="${AWS_ACCOUNT_ID:?Set AWS_ACCOUNT_ID}"
ECR_REGISTRY="${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
BACKEND_REPO="${ECR_REGISTRY}/gnosis-backend"
FRONTEND_REPO="${ECR_REGISTRY}/gnosis-frontend"
PROJECT_NAME="${PROJECT_NAME:-gnosis}"
ENVIRONMENT="${ENVIRONMENT:-dev}"
ECS_CLUSTER="${ECS_CLUSTER:-${PROJECT_NAME}-${ENVIRONMENT}}"
BACKEND_SERVICE="${BACKEND_SERVICE:-${PROJECT_NAME}-${ENVIRONMENT}-backend}"
FRONTEND_SERVICE="${FRONTEND_SERVICE:-${PROJECT_NAME}-${ENVIRONMENT}-frontend}"
IMAGE_TAG="${IMAGE_TAG:-$(git rev-parse --short HEAD)}"

echo "🚀 Deploying Gnosis (tag: ${IMAGE_TAG})"

# ─── 1. Authenticate with ECR ────────────────────────────────────────────────
echo "🔑 Logging into ECR..."
aws ecr get-login-password --region "${AWS_REGION}" \
  | docker login --username AWS --password-stdin "${ECR_REGISTRY}"

# ─── 2. Build Docker images ──────────────────────────────────────────────────
echo "🔨 Building backend..."
docker build -t "${BACKEND_REPO}:${IMAGE_TAG}" -t "${BACKEND_REPO}:latest" ./backend

echo "🔨 Building frontend..."
docker build -t "${FRONTEND_REPO}:${IMAGE_TAG}" -t "${FRONTEND_REPO}:latest" ./frontend

# ─── 3. Push to ECR ──────────────────────────────────────────────────────────
echo "📤 Pushing backend..."
docker push "${BACKEND_REPO}:${IMAGE_TAG}"
docker push "${BACKEND_REPO}:latest"

echo "📤 Pushing frontend..."
docker push "${FRONTEND_REPO}:${IMAGE_TAG}"
docker push "${FRONTEND_REPO}:latest"

# ─── 4. Update ECS services ──────────────────────────────────────────────────
echo "♻️  Updating ECS backend service..."
aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${BACKEND_SERVICE}" \
  --force-new-deployment \
  --region "${AWS_REGION}" \
  --no-cli-pager

echo "♻️  Updating ECS frontend service..."
aws ecs update-service \
  --cluster "${ECS_CLUSTER}" \
  --service "${FRONTEND_SERVICE}" \
  --force-new-deployment \
  --region "${AWS_REGION}" \
  --no-cli-pager

echo "✅ Deployment triggered! Monitor at:"
echo "   https://${AWS_REGION}.console.aws.amazon.com/ecs/v2/clusters/${ECS_CLUSTER}/services"
