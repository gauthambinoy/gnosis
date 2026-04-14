# Gnosis Python SDK

Python client for the Gnosis AI Agent Platform.

## Install

```bash
pip install gnosis-sdk
```

## Quick Start

```python
from gnosis_sdk import GnosisClient

client = GnosisClient("http://localhost:8000")
client.login("user@example.com", "password")

# Create an agent
agent = client.create_agent("Email Helper", "You summarize emails concisely")

# Execute it
result = client.execute_agent(agent["id"], "Summarize today's emails")
print(result)

# Search memory
memories = client.search_memory(agent["id"], "important meetings")

# Create a pipeline
pipeline = client.create_pipeline("Daily Report", steps=[
    {"agent_id": agent["id"], "name": "Collect Data"},
])

# Browse marketplace
market = client.browse_marketplace(category="productivity")
```

## Features

- Full CRUD for agents, pipelines, schedules
- Memory management (store, search)
- RAG document ingestion and search
- Marketplace browsing and cloning
- Collaboration rooms
- Export/import agents
- Health checks
