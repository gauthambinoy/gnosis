#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Gnosis — Local Development Setup
# Checks prerequisites, starts infrastructure, and installs dependencies.
###############################################################################

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

ERRORS=0

header() {
  echo ""
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "  $1"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
}

require() {
  local cmd="$1"
  local label="${2:-$1}"
  if command -v "$cmd" &>/dev/null; then
    echo "  ✅  $label ($(command -v "$cmd"))"
  else
    echo "  ❌  $label — not found"
    ((ERRORS++))
  fi
}

# ─── Prerequisites ───────────────────────────────────────────────────────────

header "Checking prerequisites"

require docker  "Docker"
require node    "Node.js"
require python3 "Python 3"
require pip     "pip"
require npm     "npm"

if [ "$ERRORS" -gt 0 ]; then
  echo ""
  echo "❌  Missing $ERRORS prerequisite(s). Please install them and re-run."
  exit 1
fi

# Check Docker daemon is running
if ! docker info &>/dev/null; then
  echo "  ❌  Docker daemon is not running. Please start Docker and re-run."
  exit 1
fi
echo "  ✅  Docker daemon is running"

# ─── Environment file ────────────────────────────────────────────────────────

header "Setting up environment"

if [ ! -f backend/.env ]; then
  if [ -f backend/.env.example ]; then
    cp backend/.env.example backend/.env
    echo "  📄  Created backend/.env from .env.example"
  else
    echo "  ⚠️   No backend/.env.example found — skipping .env creation"
  fi
else
  echo "  📄  backend/.env already exists"
fi

if [ ! -f frontend/.env ]; then
  if [ -f frontend/.env.example ]; then
    cp frontend/.env.example frontend/.env
    echo "  📄  Created frontend/.env from .env.example"
  else
    echo "  ⚠️   No frontend/.env.example found — skipping .env creation"
  fi
else
  echo "  📄  frontend/.env already exists"
fi

# ─── Infrastructure (Postgres + Redis) ───────────────────────────────────────

header "Starting infrastructure (PostgreSQL + Redis)"

docker compose up -d postgres redis
echo "  🐘  PostgreSQL running on localhost:5432"
echo "  🔴  Redis running on localhost:6379"

# ─── Backend dependencies ────────────────────────────────────────────────────

header "Installing backend dependencies"

cd "$ROOT_DIR/backend"
if [ -f requirements.txt ]; then
  pip install -q -r requirements.txt
  echo "  📦  Backend dependencies installed"
else
  echo "  ⚠️   No requirements.txt found"
fi

# ─── Frontend dependencies ───────────────────────────────────────────────────

header "Installing frontend dependencies"

cd "$ROOT_DIR/frontend"
if [ -f package.json ]; then
  npm ci --silent
  echo "  📦  Frontend dependencies installed"
else
  echo "  ⚠️   No package.json found"
fi

# ─── Done ────────────────────────────────────────────────────────────────────

cd "$ROOT_DIR"

echo ""
echo "╔══════════════════════════════════════════════════════════╗"
echo "║  🚀  Gnosis local environment is ready!                 ║"
echo "╠══════════════════════════════════════════════════════════╣"
echo "║                                                         ║"
echo "║  Start the backend:                                     ║"
echo "║    cd backend && uvicorn app.main:app --reload          ║"
echo "║                                                         ║"
echo "║  Start the frontend:                                    ║"
echo "║    cd frontend && npm run dev                           ║"
echo "║                                                         ║"
echo "║  Backend:   http://localhost:8000                       ║"
echo "║  Frontend:  http://localhost:3000                       ║"
echo "║  API docs:  http://localhost:8000/docs                  ║"
echo "║                                                         ║"
echo "║  Stop infra: docker compose down                        ║"
echo "╚══════════════════════════════════════════════════════════╝"
echo ""
