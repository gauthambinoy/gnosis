"""Gnosis Agent Builder — converts natural language to structured AgentConfig via LLM."""

from dataclasses import dataclass, field, asdict


AVAILABLE_INTEGRATIONS = ["gmail", "sheets", "slack", "http", "webhook", "schedule"]
TRIGGER_TYPES = ["manual", "schedule", "webhook", "email_received", "slack_message"]

BUILDER_PROMPT = """You are the Gnosis Agent Builder. Convert the user's description into a structured agent configuration.

Available integrations: {integrations}
Available triggers: {triggers}

Respond with ONLY valid JSON matching this schema:
{{
  "name": "short agent name",
  "description": "what the agent does",
  "personality": "professional|friendly|analytical|creative",
  "trigger_type": "one of the trigger types",
  "trigger_config": {{}},
  "steps": [{{"action": "description of step", "integration": "service_name", "capability": "action_name"}}],
  "integrations_needed": ["list of services"],
  "approval_rules": [{{"condition": "when to ask human", "threshold": 0.8}}],
  "guardrails": ["safety constraints"]
}}"""


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
        """Parse a natural language description into an agent config using LLM or heuristics."""
        config = self._heuristic_build(description)
        return config

    def _heuristic_build(self, description: str) -> AgentConfig:
        """Extract agent config from description using keyword analysis."""
        desc_lower = description.lower()

        name = self._extract_name(desc_lower)

        trigger_type = "manual"
        trigger_config = {}
        if any(
            w in desc_lower for w in ["every day", "daily", "every morning", "schedule"]
        ):
            trigger_type = "schedule"
            trigger_config = {"cron": "0 9 * * *"}
        elif any(
            w in desc_lower for w in ["when email", "new email", "inbox", "gmail"]
        ):
            trigger_type = "email_received"
        elif any(w in desc_lower for w in ["when message", "slack message", "channel"]):
            trigger_type = "slack_message"
        elif any(w in desc_lower for w in ["webhook", "api call"]):
            trigger_type = "webhook"

        integrations = []
        if any(w in desc_lower for w in ["email", "gmail", "inbox", "send email"]):
            integrations.append("gmail")
        if any(
            w in desc_lower for w in ["sheet", "spreadsheet", "google sheet", "log to"]
        ):
            integrations.append("sheets")
        if any(w in desc_lower for w in ["slack", "channel", "message"]):
            integrations.append("slack")

        steps = self._extract_steps(description, integrations)

        guardrails = ["Never send emails without draft approval on first 10 executions"]
        if "money" in desc_lower or "payment" in desc_lower or "invoice" in desc_lower:
            guardrails.append(
                "Flag any action involving money over $100 for human approval"
            )
        if "delete" in desc_lower:
            guardrails.append("Never delete data without explicit confirmation")

        return AgentConfig(
            name=name,
            description=description,
            personality="professional",
            trigger_type=trigger_type,
            trigger_config=trigger_config,
            steps=steps,
            integrations_needed=integrations,
            approval_rules=[{"condition": "confidence < 0.7", "threshold": 0.7}],
            guardrails=guardrails,
        )

    def _extract_name(self, desc: str) -> str:
        """Generate a concise agent name."""
        if "email" in desc and "invoice" in desc:
            return "Invoice Tracker"
        if "email" in desc and "reply" in desc:
            return "Email Responder"
        if "slack" in desc and "summarize" in desc:
            return "Slack Summarizer"
        if "schedule" in desc or "meeting" in desc:
            return "Schedule Manager"
        if "report" in desc:
            return "Report Generator"
        if "monitor" in desc:
            return "Monitor Agent"
        words = [w for w in desc.split()[:5] if len(w) > 3]
        return " ".join(words[:3]).title() or "New Agent"

    def _extract_steps(self, description: str, integrations: list[str]) -> list[dict]:
        """Extract action steps from description."""
        steps = []
        desc_lower = description.lower()

        if "gmail" in integrations:
            if "read" in desc_lower or "monitor" in desc_lower or "check" in desc_lower:
                steps.append(
                    {
                        "action": "Read incoming emails",
                        "integration": "gmail",
                        "capability": "read_inbox",
                    }
                )
            if "send" in desc_lower or "reply" in desc_lower:
                steps.append(
                    {
                        "action": "Send/reply to email",
                        "integration": "gmail",
                        "capability": "send_email",
                    }
                )

        if "sheets" in integrations:
            if "log" in desc_lower or "write" in desc_lower or "append" in desc_lower:
                steps.append(
                    {
                        "action": "Log data to spreadsheet",
                        "integration": "sheets",
                        "capability": "append_row",
                    }
                )
            if "read" in desc_lower:
                steps.append(
                    {
                        "action": "Read spreadsheet data",
                        "integration": "sheets",
                        "capability": "read_sheet",
                    }
                )

        if "slack" in integrations:
            if "send" in desc_lower or "post" in desc_lower or "notify" in desc_lower:
                steps.append(
                    {
                        "action": "Send Slack notification",
                        "integration": "slack",
                        "capability": "send_message",
                    }
                )

        if not steps:
            steps.append(
                {"action": description, "integration": "manual", "capability": "custom"}
            )

        return steps

    async def clarify(self, description: str) -> list[str]:
        """Generate clarifying questions for vague descriptions."""
        questions = []
        desc_lower = description.lower()

        if "email" in desc_lower and not any(
            w in desc_lower for w in ["gmail", "outlook"]
        ):
            questions.append(
                "Which email provider should I connect to? (Gmail, Outlook, etc.)"
            )

        if not any(w in desc_lower for w in ["when", "every", "schedule", "trigger"]):
            questions.append(
                "When should this agent run? (On schedule, when triggered by an event, or manually?)"
            )

        if any(w in desc_lower for w in ["important", "urgent", "priority"]):
            questions.append(
                "How should I determine what counts as 'important'? Any specific keywords or senders?"
            )

        if not questions:
            questions.append(
                "Can you give me more details about exactly what actions this agent should take?"
            )

        return questions

    def to_dict(self, config: AgentConfig) -> dict:
        return asdict(config)
