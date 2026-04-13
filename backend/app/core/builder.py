"""Gnosis Agent Builder — converts natural language to AgentConfig."""
from dataclasses import dataclass, field


@dataclass
class AgentConfig:
    name: str
    description: str
    personality: str = "professional"
    trigger_type: str = "manual"
    trigger_config: dict = field(default_factory=dict)
    steps: list[dict] = field(default_factory=list)
    integrations_needed: list[str] = field(default_factory=list)
    approval_rules: list[dict] = field(default_factory=list)
    guardrails: list[str] = field(default_factory=list)


class AgentBuilder:
    """Converts natural language descriptions into structured AgentConfig."""

    async def build_from_description(self, description: str) -> AgentConfig:
        return AgentConfig(name="New Agent", description=description, steps=[{"action": "placeholder", "description": description}])

    async def clarify(self, description: str) -> list[str]:
        return ["Which email account should this agent monitor?", "What should happen with urgent messages?", "Should I auto-reply or just draft responses for your approval?"]
