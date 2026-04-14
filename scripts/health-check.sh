#!/usr/bin/env bash
set -euo pipefail

###############################################################################
# Gnosis Health Check
# Checks backend, frontend, database, and Redis connectivity.
# Usage: ./scripts/health-check.sh [BASE_URL]
###############################################################################

BASE_URL="${1:-http://localhost:8000}"
FRONTEND_URL="${2:-http://localhost:3000}"
TIMEOUT=5
PASS=0
FAIL=0
RESULTS=()

check() {
  local name="$1"
  local status="$2"
  if [ "$status" = "ok" ]; then
    RESULTS+=("  ✅  $name")
    ((PASS++))
  else
    RESULTS+=("  ❌  $name — $status")
    ((FAIL++))
  fi
}

echo ""
echo "╔══════════════════════════════════════╗"
echo "║       Gnosis Health Check            ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "  Backend:  $BASE_URL"
echo "  Frontend: $FRONTEND_URL"
echo ""

# --- Backend health endpoint ---
BACKEND_RESP=$(curl -sf --max-time "$TIMEOUT" "$BASE_URL/health" 2>&1) && \
  check "Backend API" "ok" || \
  check "Backend API" "unreachable ($BASE_URL/health)"

# --- Database connectivity (via backend health) ---
if [ -n "$BACKEND_RESP" ]; then
  DB_STATUS=$(echo "$BACKEND_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('database','unknown'))" 2>/dev/null || echo "unknown")
  if [ "$DB_STATUS" = "connected" ] || [ "$DB_STATUS" = "ok" ] || [ "$DB_STATUS" = "healthy" ]; then
    check "Database (PostgreSQL)" "ok"
  else
    check "Database (PostgreSQL)" "status: $DB_STATUS"
  fi
else
  check "Database (PostgreSQL)" "could not determine (backend unreachable)"
fi

# --- Redis connectivity (via backend health) ---
if [ -n "$BACKEND_RESP" ]; then
  REDIS_STATUS=$(echo "$BACKEND_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('redis','unknown'))" 2>/dev/null || echo "unknown")
  if [ "$REDIS_STATUS" = "connected" ] || [ "$REDIS_STATUS" = "ok" ] || [ "$REDIS_STATUS" = "healthy" ]; then
    check "Redis" "ok"
  else
    check "Redis" "status: $REDIS_STATUS"
  fi
else
  check "Redis" "could not determine (backend unreachable)"
fi

# --- Frontend accessibility ---
HTTP_CODE=$(curl -so /dev/null --max-time "$TIMEOUT" -w "%{http_code}" "$FRONTEND_URL" 2>/dev/null) || HTTP_CODE="000"
if [ "$HTTP_CODE" -ge 200 ] && [ "$HTTP_CODE" -lt 400 ]; then
  check "Frontend" "ok"
else
  check "Frontend" "HTTP $HTTP_CODE ($FRONTEND_URL)"
fi

# --- Summary ---
echo "┌──────────────────────────────────────┐"
echo "│  Results                             │"
echo "├──────────────────────────────────────┤"
for line in "${RESULTS[@]}"; do
  echo "│ $line"
done
echo "├──────────────────────────────────────┤"
echo "│  Passed: $PASS   Failed: $FAIL"
echo "└──────────────────────────────────────┘"
echo ""

if [ "$FAIL" -gt 0 ]; then
  exit 1
fi
