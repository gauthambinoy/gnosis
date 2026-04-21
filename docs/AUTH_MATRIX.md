# Gnosis API Authentication Matrix

This document enumerates every endpoint in `backend/app/api/` and its required auth
status. It is the audit trail for the H4 hardening pass.

Status legend:

- **required** — endpoint calls `Depends(get_current_user_id)` and rejects anonymous callers
  (or returns `user_id = "00000000-…-0001"` in DEBUG mode, per `app/core/auth.py`).
- **public** — intentionally unauthenticated; marked with a `# PUBLIC: …` comment on the
  `@router` decorator line in source.
- **optional** — anonymous calls accepted but a bearer token is extracted opportunistically
  (e.g. anonymous feedback).

The enforcement test lives at `backend/tests/test_router_auth_matrix.py`; any endpoint
added without auth and not on the `PUBLIC_ALLOWLIST` there will fail CI.

## Routers hardened in this pass (H4)

### `app/api/awakening.py`
| Method | Path | Status | Justification |
|---|---|---|---|
| POST | `/chat` | required | Streams LLM output — costs tokens per caller |

### `app/api/aws_status.py`
| Method | Path | Status | Justification |
|---|---|---|---|
| GET | `/status` | required | Exposes internal cloud service inventory |

### `app/api/collaboration.py`
| Method | Path | Status | Justification |
|---|---|---|---|
| POST | `/rooms` | required | Creates multi-agent discussion room |
| GET | `/rooms` | required | Lists rooms (may contain private topics) |
| GET | `/rooms/{room_id}` | required | Reads room state |
| POST | `/rooms/{room_id}/messages` | required | Posts as agent into a room |
| POST | `/rooms/{room_id}/discuss` | required | Triggers LLM discussion cycle |
| POST | `/rooms/{room_id}/resolve` | required | Mutates room status |
| POST | `/rooms/{room_id}/archive` | required | Mutates room status |
| GET | `/stats` | required | Internal metrics |

### `app/api/dreams.py`
All 9 endpoints require auth — agent-scoped learning state.

### `app/api/events.py`
| GET | `/recent` / `/connections` | required | Reveals internal event/WS state |

### `app/api/export_import.py`
All 5 endpoints require auth — exports and ingests arbitrary agent configs.

### `app/api/factory.py`
All 8 endpoints require auth — creates and deploys new agents/pipelines.

### `app/api/feedback.py`
| Method | Path | Status | Justification |
|---|---|---|---|
| POST | `` | public (optional bearer) | Anonymous feedback path preserved; user_id captured when token present |
| GET | `` | required | Feedback moderation queue |

### `app/api/health.py` & `app/api/health_check.py`
Every endpoint is **public** — required by load balancers and uptime monitors for
liveness/readiness probes.

### `app/api/integrations.py`
| Method | Path | Status | Justification |
|---|---|---|---|
| GET | `/providers` | required | Shows caller's own connection status |
| GET | `/{provider}/auth` | required | Starts OAuth flow on behalf of caller |
| GET | `/{provider}/callback` | public | OAuth provider redirect; state param is validated by `oauth_manager` |
| DELETE | `/{provider}` | required | Revokes caller's tokens |
| GET | `/{provider}/status` | required | Caller-scoped connection status |

The hard-coded `_DEFAULT_USER = "default"` user has been replaced with the authenticated
`user_id` in all five handlers so OAuth tokens are now scoped correctly per user (response
shape unchanged).

### `app/api/knowledge_graph.py`
All 7 endpoints require auth — extraction and graph mutation.

### `app/api/marketplace.py`
| Method | Path | Status | Justification |
|---|---|---|---|
| GET | `/categories` | public | Public marketplace taxonomy |
| GET | `/browse` | public | Anonymous marketplace discovery |
| GET | `/stats` | public | Aggregate non-sensitive counts |
| GET | `/{agent_id}` | public | Public listing page |
| GET | `/{agent_id}/reviews` | public | Reviews shown on public listing |
| POST | `/publish` | required | Creates new listing |
| POST | `/{agent_id}/clone` | required | Returns clone config |
| POST | `/{agent_id}/reviews` | required | Review now attributed to caller instead of hard-coded `"anonymous"` |

### `app/api/memory.py`
All 5 endpoints require auth — agent memories include user data.

### `app/api/oracle.py`
All 3 endpoints require auth — platform health/insights for authenticated operators only.

### `app/api/pipelines.py`
All 11 endpoints require auth — CRUD + execution over user pipelines.

### `app/api/predictions.py`
All 6 endpoints require auth. The hard-coded `user_id="default"` default parameter was
replaced with the authenticated user id; `track_action` now derives `user_id` from the
token instead of trusting the request body.

### `app/api/prompts.py`
All 3 endpoints require auth — prompt-optimizer history is per-user.

### `app/api/pwa.py`
| GET | `/manifest` | public | PWA install manifest must load pre-login |
| GET | `/config` | public | Service-worker bootstrap config |

### `app/api/rag.py`
All 8 endpoints require auth — ingested documents may contain private data.

### `app/api/realworld.py`
All 7 endpoints require auth. The `create_trigger` handler no longer accepts `user_id` from
the request body; it derives it from the token, and `list_triggers` no longer defaults
to the shared `"default"` bucket.

### `app/api/replay.py`
All 4 endpoints require auth — execution recordings contain sensitive traces.

### `app/api/rpa.py`
All 16 endpoints require auth. `start_recording` now stamps the session with the
authenticated user id, not the user-supplied one.

### `app/api/schedules.py`
All 8 endpoints require auth — scheduler runs cost quota.

### `app/api/security_dashboard.py`
| Method | Path | Status | Justification |
|---|---|---|---|
| GET | `/stats`, `/threats`, `/blocked-ips` | required | Operator-only telemetry |
| POST | `/block-ip`, `/unblock-ip` | required | Mutates firewall state |
| GET | `/csrf-token` | public | CSRF token must be obtainable before login to protect the auth endpoints themselves |
| POST | `/scan` | required | Internal security self-scan |

### `app/api/sso.py`
| Method | Path | Status | Justification |
|---|---|---|---|
| GET | `/providers` | public | Drives login-page provider picker |
| POST | `/authorize` | public | Initiates SSO flow for anonymous users |
| POST | `/callback` | public | OAuth provider redirect; state param validated |
| POST | `/link` | required | Attaches SSO identity to existing account |
| GET | `/accounts/{user_id}` | required | Admin-visible linked-accounts |
| GET | `/stats` | required | Internal telemetry |

### `app/api/standup.py`
All 3 endpoints require auth — operational reports.

### `app/api/swarm.py`
All 10 endpoints require auth — swarm registry and task orchestration.

### `app/api/system_control.py`
All 11 endpoints require auth — OS-level introspection and command execution. `execute_command`
now records the authenticated `user_id` in the audit trail instead of the fixed `"admin"`
string (captured in the audit log; response body unchanged).

### `app/api/system.py`
All 14 endpoints require auth — DLQ/queue/pool/tracing surfaces are operator-only.

### `app/api/templates.py`
| GET | `` | public | Workflow template catalog |
| GET | `/{template_id}` | public | Template detail (catalog) |
| POST | `/{template_id}/deploy` | required | Creates a real agent |

### `app/api/versions.py`
All 6 endpoints require auth — version history of user agents.

### `app/api/webhook_triggers.py`
| Method | Path | Status | Justification |
|---|---|---|---|
| POST | `/triggers` | required | Creates trigger config |
| GET | `/triggers` | required | Lists caller's triggers |
| GET | `/triggers/{trigger_id}` | required | Reads trigger config |
| DELETE | `/triggers/{trigger_id}` | required | Removes trigger |
| POST | `/triggers/{trigger_id}/toggle` | required | Toggles active flag |
| POST | `/trigger/{trigger_id}` | public | External webhook invocation — authenticity enforced via `x-webhook-signature` HMAC header |
| GET | `/triggers/{trigger_id}/invocations` | required | Invocation history |
| GET | `/stats` | required | Aggregate metrics |

## Partially-protected routers (remaining endpoints hardened)

### `app/api/agent_permissions.py`
All endpoints now require auth (grant already had it; revoke/list/check added).

### `app/api/auto_api.py`
Catalog (`/catalog`, `/catalog/{name}`, `/search`, `/categories`) remains **public** —
read-only public catalog metadata. Every connection-management endpoint (`/connect`,
`/connections`, `/connections/{id}`, `/connections/{id}/test`, `/connections/{id}/call`,
`/connections/{id}` DELETE, `/generate/{name}`, `/stats`) now requires auth.

### `app/api/billing.py`
- `/plans` → **public** (pricing page).
- `/stats` → now **required** (was silently open).
- All other endpoints already required auth.

### `app/api/env_promotion.py`
All 5 endpoints now require auth (deploy/rollback/list were unprotected).

### `app/api/integration_tokens.py`
All 4 endpoints now require auth (revoke/validate were unprotected).

### `app/api/internal_marketplace.py`
- Search and get-listing are **public** (internal catalog browse has no sensitive data).
- Publish, rate, and download now all require auth.

### `app/api/llm.py`
Every endpoint is now `required`. Previously `list_models`, `get_llm_stats`, `get_tiers`,
`get_providers`, `get_costs`, `get_agent_costs`, and `get_recent_cost_records` were open —
they expose billing signals and configured providers.

### `app/api/workspaces.py`
All 11 endpoints now require auth; 7 were missing the guard (stats, get, patch, delete,
remove member, update role, list members).

## Routers that already had full auth coverage

The remaining 80 routers in `app/api/` already declared `Depends(get_current_user_id)` on
every endpoint before this pass. See the parameterized test for the definitive view.
