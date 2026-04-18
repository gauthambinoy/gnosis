"""Custom OpenAPI documentation configuration."""

OPENAPI_TAGS = [
    {"name": "agents", "description": "Create, manage, and monitor AI agents"},
    {"name": "executions", "description": "Run agent tasks and track execution status"},
    {"name": "memory", "description": "Agent memory management across 4 tiers"},
    {"name": "pipelines", "description": "Multi-agent workflow pipelines"},
    {"name": "files", "description": "File upload, download, and management"},
    {"name": "auth", "description": "Authentication and user management"},
    {"name": "quotas", "description": "Workspace resource quota management"},
    {"name": "compliance", "description": "GDPR, PII detection, data retention"},
    {"name": "observability", "description": "Debugging, cost tracking, flamegraphs"},
    {"name": "performance", "description": "Query analysis, streaming, Redis metrics"},
    {"name": "webhooks", "description": "Outbound webhook configuration"},
    {"name": "real-time", "description": "Server-Sent Events for live updates"},
    {"name": "search", "description": "Global search across all entities"},
    {"name": "onboarding", "description": "User onboarding flow"},
    {"name": "bulk", "description": "Bulk operations for scale management"},
    {
        "name": "config-snapshots",
        "description": "Immutable agent configuration versioning",
    },
    {"name": "tools", "description": "Shared tool registry"},
    {"name": "activity", "description": "Workspace activity feed"},
    {"name": "audit", "description": "Request/response audit trail"},
    {"name": "reliability", "description": "Retry management and circuit breaking"},
    {"name": "health", "description": "System health checks"},
    {"name": "dashboard", "description": "Aggregated dashboard statistics"},
    {"name": "streaming", "description": "Real-time LLM token streaming"},
]

API_DESCRIPTION = """
# Gnosis AI Agent Platform API

Build, deploy, and manage intelligent AI agents with learning capabilities.

## Key Features
- 🤖 **Agent Creation** — Describe what you need, Gnosis builds it
- 🧠 **4-Tier Memory** — Corrections > Episodic > Semantic > Procedural
- 🔗 **Pipelines** — Chain agents for multi-step workflows
- 📊 **Observability** — Time-travel debugging, cost tracking, flamegraphs
- 🛡️ **Compliance** — PII detection, GDPR erasure, data retention
- ⚡ **Real-time** — SSE streaming, WebSocket updates
- 🔌 **Webhooks** — External notifications on key events

## Authentication
All endpoints (except `/health`) require a Bearer token in the Authorization header:
```
Authorization: Bearer <your-jwt-token>
```

## Rate Limits
- Default: 60 requests/minute per user
- Burst: 10 additional requests allowed
- Headers: `X-RateLimit-Limit`, `X-RateLimit-Remaining`
"""


def get_openapi_config() -> dict:
    return {
        "title": "Gnosis AI Agent Platform",
        "description": API_DESCRIPTION,
        "version": "1.0.0",
        "openapi_tags": OPENAPI_TAGS,
        "docs_url": "/docs",
        "redoc_url": "/redoc",
    }
