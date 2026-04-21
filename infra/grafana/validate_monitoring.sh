#!/usr/bin/env bash
# Validate the Grafana monitoring setup is healthy before a deploy.
#
# Usage: validate_monitoring.sh <grafana_base_url> <api_token>
set -euo pipefail

if [[ $# -lt 2 ]]; then
  echo "Usage: $0 <grafana_base_url> <api_token>" >&2
  exit 2
fi

BASE_URL="${1%/}"
TOKEN="$2"
AUTH=(-H "Authorization: Bearer $TOKEN" -H "Accept: application/json")

EXPECTED_DASHBOARDS=(
  "backend-overview"
  "llm-gateway"
  "database"
  "business-metrics"
)

EXPECTED_ALERTS=(
  "BackendDown"
  "High5xxRate"
  "HighLatency"
  "DBConnectionsHigh"
  "LLMProviderErrors"
  "RateLimiterSurge"
  "AuditLogTamper"
  "DiskSpaceLow"
)

fail=0

echo "→ Checking Grafana reachable…"
if ! curl -fsS "${AUTH[@]}" "$BASE_URL/api/health" >/dev/null; then
  echo "  ❌ Grafana not reachable at $BASE_URL"
  exit 1
fi

echo "→ Checking Prometheus datasource…"
if ! curl -fsS "${AUTH[@]}" "$BASE_URL/api/datasources/name/Prometheus" >/dev/null; then
  echo "  ❌ Prometheus datasource missing"
  fail=1
fi

echo "→ Checking dashboards…"
for d in "${EXPECTED_DASHBOARDS[@]}"; do
  if curl -fsS "${AUTH[@]}" "$BASE_URL/api/search?query=$d&type=dash-db" \
      | grep -q "\"title\""; then
    echo "  ✅ $d"
  else
    echo "  ❌ $d missing"
    fail=1
  fi
done

echo "→ Checking alert rules…"
rules_json=$(curl -fsS "${AUTH[@]}" "$BASE_URL/api/v1/provisioning/alert-rules" || echo "[]")
for a in "${EXPECTED_ALERTS[@]}"; do
  if echo "$rules_json" | grep -q "\"title\":\"$a\""; then
    echo "  ✅ $a"
  else
    echo "  ❌ $a alert rule missing"
    fail=1
  fi
done

if [[ $fail -ne 0 ]]; then
  echo "❌ Monitoring validation failed"
  exit 1
fi
echo "✅ Monitoring validation passed"
