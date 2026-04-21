# WebSocket Reliability Guarantees

Real-time execution updates over `wss://`.

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `ws://host/ws/executions?token=JWT` | Stream of all execution events for the authenticated user |
| `ws://host/ws/executions/{id}?token=JWT` | Stream of events for one execution |
| `ws://host/ws/agents/{id}?token=JWT` | All execution events for one agent |

## Message Format

Every server-to-client message is a JSON object:

```json
{
  "type": "execution.token",
  "execution_id": "uuid",
  "sequence": 42,
  "timestamp": "2026-04-21T10:00:00Z",
  "payload": { ... }
}
```

### Event Types

- `connection.ack` — sent on successful connect, contains `session_id`
- `execution.started` — execution accepted by worker
- `execution.token` — single token streamed from LLM
- `execution.tool_call` — agent invoked a tool
- `execution.tool_result` — tool returned
- `execution.completed` — final output emitted, channel closes
- `execution.failed` — execution errored, channel closes
- `heartbeat` — empty keep-alive, every 25 seconds

## Ordering

- **Within one `execution_id`** messages are strictly ordered by `sequence` (monotonic, gap-free)
- **Across executions** ordering is best-effort. Use `timestamp` if cross-execution order matters.

## Heartbeats

The server sends a `heartbeat` frame every **25 seconds**. Clients SHOULD treat 60s of silence as a dead connection and reconnect.

```javascript
const HEARTBEAT_TIMEOUT_MS = 60_000;
let lastSeen = Date.now();
ws.onmessage = (e) => { lastSeen = Date.now(); };
setInterval(() => {
  if (Date.now() - lastSeen > HEARTBEAT_TIMEOUT_MS) ws.close();
}, 10_000);
```

## Reconnection Backoff

Exponential with jitter:

```
attempt 1: 1s  + jitter(0-500ms)
attempt 2: 2s  + jitter(0-1s)
attempt 3: 4s  + jitter(0-2s)
attempt 4: 8s  + jitter(0-4s)
attempt 5+: 16s + jitter(0-8s)
```

The reference SDK (`sdk/`) implements this automatically.

## Resuming After Disconnect

To avoid missing events when reconnecting, pass `?since_sequence=N`:

```
wss://host/ws/executions/{id}?token=JWT&since_sequence=42
```

The server replays buffered events with `sequence > 42`. The replay buffer holds **the last 1,000 events per execution**, retained for 5 minutes after the last activity.

If the buffer has rolled over you receive `connection.replay_unavailable` and must fetch the missing range via `GET /api/v1/executions/{id}/events?since=N`.

## Backpressure

Per-connection bounded queue (1,000 messages). If a slow client cannot drain fast enough:

1. Connection is paused; the executor keeps producing events to the persistent log
2. After 30s of sustained backpressure the connection is closed with code `1013`
3. Client should reconnect with `since_sequence` to resume

## Authentication

- Token passed as `?token=JWT` query parameter (browser WebSocket APIs cannot set headers)
- Validated on `CONNECT`; expired tokens get `4401` close
- Re-auth required on reconnect

## Close Codes

| Code | Meaning | Client Action |
|------|---------|---------------|
| 1000 | Normal close | Don't reconnect |
| 1001 | Server going away (deploy) | Reconnect with backoff |
| 1011 | Server error | Reconnect with backoff |
| 1013 | Backpressure timeout | Reconnect with `since_sequence` |
| 4401 | Auth expired/invalid | Refresh token, reconnect |
| 4403 | Forbidden (no access) | Don't reconnect |
| 4429 | Rate limited | Wait `Retry-After`, then reconnect |

## Delivery Semantics

- **At-least-once** within the replay window (5 min / 1,000 events)
- **Exactly-once** is not guaranteed at the WebSocket layer — clients should de-dup on `sequence`
- For audit-grade delivery, use **webhooks** (`POST /api/v1/webhooks`); webhook delivery is retried with persistence

## SLA Notes

- Median first-message latency after `connection.ack`: < 100ms
- Heartbeat jitter: ±2s
- Buffer retention: 1,000 events OR 5 minutes (whichever comes first)
- WebSocket connection cap: 50 concurrent per user (Pro), 500 (Business), unlimited (Enterprise)
