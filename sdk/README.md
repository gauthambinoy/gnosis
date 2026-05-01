# Gnosis SDK

Official Python client library for Gnosis AI Agent Orchestration Platform.

## Status

**Current: Stub / Minimal Implementation**

This SDK is a foundational stub provided for compatibility. Full feature coverage is planned for v1.1.

## Installation

```bash
pip install gnosis-sdk
```

## Quick Start

### Authentication

```python
from gnosis import GnosisClient

client = GnosisClient(
    api_key="your-api-key-here",
    base_url="https://api.gnosis.example.com"
)

# Or use environment variable
# export GNOSIS_API_KEY="your-api-key-here"
client = GnosisClient()  # Auto-loads from env
```

### Create an Agent

```python
agent = client.agents.create(
    name="Email Classifier",
    description="Classifies incoming emails by priority",
    system_prompt="You are an email classification expert...",
    model="claude-3.5-sonnet"
)

print(f"Created agent: {agent.id}")
```

### Execute Agent

```python
execution = client.agents.execute(
    agent_id=agent.id,
    input="Classify this email: 'Urgent: System outage in production'",
)

print(f"Result: {execution.output}")
print(f"Status: {execution.status}")
print(f"Cost: ${execution.cost_usd:.4f}")
```

### List Agents

```python
agents = client.agents.list(limit=10, offset=0)

for agent in agents:
    print(f"- {agent.name} ({agent.id})")
```

### Webhook Integration

```python
# Register webhook to receive execution results
client.webhooks.register(
    url="https://example.com/webhooks/gnosis",
    event_types=["execution.completed", "execution.failed"],
    secret="webhook-secret-key"
)

# Verify webhook signature
from gnosis.webhooks import verify_signature

is_valid = verify_signature(
    payload=request.body,
    signature=request.headers["X-Gnosis-Signature"],
    secret="webhook-secret-key"
)
```

## Key Resources

### Agents

```python
# List agents
agents = client.agents.list()

# Get agent details
agent = client.agents.get(agent_id="agent-123")

# Create agent
agent = client.agents.create(
    name="...",
    description="...",
    system_prompt="...",
    model="claude-3.5-sonnet",
    tools=[
        {
            "name": "search",
            "description": "Search the web",
            "parameters": {...}
        }
    ]
)

# Update agent
agent = client.agents.update(
    agent_id="agent-123",
    description="Updated description"
)

# Delete agent
client.agents.delete(agent_id="agent-123")

# Clone agent
cloned = client.agents.clone(agent_id="agent-123", name="New Copy")
```

### Executions

```python
# Execute agent synchronously (waits for result)
execution = client.agents.execute(
    agent_id="agent-123",
    input="What is the capital of France?",
    timeout_seconds=30
)

# Execute asynchronously (returns immediately)
execution = client.agents.execute_async(
    agent_id="agent-123",
    input="Analyze this large dataset...",
)

execution_id = execution.id

# Check execution status
execution = client.executions.get(execution_id)

# List agent executions
executions = client.agents.list_executions(agent_id="agent-123")
```

### Billing & Quotas

```python
# Get current usage
usage = client.billing.get_usage()
print(f"API calls this month: {usage.api_calls}")
print(f"LLM tokens: {usage.llm_tokens}")
print(f"Estimated cost: ${usage.estimated_cost_usd:.2f}")

# Get plan details
plan = client.billing.get_plan()
print(f"Plan: {plan.tier}")  # 'free', 'starter', 'pro', 'enterprise'
print(f"Monthly limit: {plan.monthly_api_calls}")
```

## API Reference

### Client Initialization

```python
GnosisClient(
    api_key: str = None,              # Defaults to GNOSIS_API_KEY env var
    base_url: str = "https://api.gnosis.example.com",
    timeout_seconds: int = 30,
    retries: int = 3,
    verify_ssl: bool = True,
)
```

### Common Response Types

```python
class Agent:
    id: str
    name: str
    description: str
    created_at: datetime
    updated_at: datetime
    model: str
    system_prompt: str
    tools: list[Tool]
    owner_id: str
    workspace_id: str

class Execution:
    id: str
    agent_id: str
    input: str
    output: str
    status: str  # "pending", "running", "completed", "failed"
    result: dict
    error: str | None
    llm_model: str
    tokens_used: int
    cost_usd: float
    created_at: datetime
    completed_at: datetime | None
```

## Error Handling

```python
from gnosis.exceptions import (
    GnosisError,
    AuthenticationError,
    NotFoundError,
    ValidationError,
    RateLimitError,
)

try:
    execution = client.agents.execute(agent_id="invalid-id", input="test")
except NotFoundError:
    print("Agent not found")
except RateLimitError:
    print("Rate limited - wait before retrying")
except AuthenticationError:
    print("Invalid API key")
except ValidationError as e:
    print(f"Invalid input: {e.details}")
except GnosisError as e:
    print(f"API error: {e}")
```

## Async Support

```python
import asyncio
from gnosis import AsyncGnosisClient

async def main():
    async with AsyncGnosisClient(api_key="...") as client:
        agent = await client.agents.get("agent-123")
        execution = await client.agents.execute(
            agent_id="agent-123",
            input="What is 2+2?"
        )
        print(execution.output)

asyncio.run(main())
```

## Roadmap

### v1.1 (Q2 2026)
- [ ] Full type hints (currently partial)
- [ ] Streaming responses for long-running executions
- [ ] Agent templates library
- [ ] Tool library (web search, email, CRM, etc.)
- [ ] Memory management (long-term context)
- [ ] Advanced agent workflows (chains, nested agents)

### v1.2 (Q3 2026)
- [ ] Voice input/output support
- [ ] Document ingestion (PDF, Word, email)
- [ ] Custom integrations builder
- [ ] Observability hooks (logging, tracing)
- [ ] Agent performance analytics

## Contributing

Contributions welcome! Please see [CONTRIBUTING.md](../CONTRIBUTING.md)

## Support

- **Documentation**: https://gnosis.example.com/docs
- **Issues**: https://github.com/gauthambinoy/gnosis/issues
- **Discord**: https://discord.gg/gnosis

## License

MIT — see [LICENSE](../LICENSE)
