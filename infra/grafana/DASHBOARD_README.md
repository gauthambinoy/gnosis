# Grafana Dashboards

Reference for the Gnosis production Grafana setup.

## Dashboards

| File | Purpose |
|------|---------|
| `backend-overview.json` | Request rate, latency p50/p95/p99, 5xx rate, container CPU/RAM |
| `llm-gateway.json` | Per-provider call rate, error rate, token usage, retries |
| `database.json` | Connection count, slow queries, replication lag, disk |
| `business-metrics.json` | DAU, executions/day, revenue, churn |

Dashboards live in `infra/grafana/dashboards/` and are auto-imported by the Grafana provisioning config in `infra/grafana/provisioning/`.

## Validating the Setup

After provisioning a Grafana instance:

```bash
./infra/grafana/validate_monitoring.sh https://grafana.example.com $GRAFANA_API_TOKEN
```

The script checks:
- Each expected dashboard exists and has at least one panel
- Prometheus datasource is reachable
- Each critical alert rule is loaded and not paused

Exit code is non-zero if anything is missing — wire it into CI before any deploy.

## Critical Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| `BackendDown` | up{job="gnosis-backend"} == 0 for 2m | SEV-1 |
| `High5xxRate` | rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.01 | SEV-2 |
| `HighLatency` | histogram_quantile(0.95, ...) > 2 for 10m | SEV-3 |
| `DBConnectionsHigh` | pg_stat_activity_count > 80 | SEV-3 |
| `LLMProviderErrors` | rate(llm_requests_total{status="error"}[5m]) > 0.05 | SEV-2 |
| `RateLimiterSurge` | rate(http_requests_total{status="429"}[1m]) > 10 | SEV-3 |
| `AuditLogTamper` | gnosis_audit_log_integrity_valid == 0 | SEV-1 |
| `DiskSpaceLow` | node_filesystem_avail_bytes / node_filesystem_size_bytes < 0.15 | SEV-2 |

Each alert routes to PagerDuty `gnosis-oncall` and Slack `#gnosis-alerts`.

## Adding a New Dashboard

1. Build it in Grafana UI
2. Export JSON (Settings → JSON Model)
3. Save to `infra/grafana/dashboards/`
4. Add an entry to the table above
5. Run `validate_monitoring.sh` locally to confirm it loads
