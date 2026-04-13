"""Slack connector — UAP compliant."""
from app.integrations.base import BaseConnector, ActionDefinition, ActionResult


class SlackConnector(BaseConnector):
    def __init__(self, credentials: dict):
        self.credentials = credentials

    def get_actions(self) -> list[ActionDefinition]:
        return [
            ActionDefinition(service="slack", capability="send_message", description="Send a message to a Slack channel", inputs={"channel": {"type": "string"}, "text": {"type": "string"}}, outputs={"ts": {"type": "string"}}),
            ActionDefinition(service="slack", capability="read_channel", description="Read messages from a channel", inputs={"channel": {"type": "string"}, "limit": {"type": "integer"}}, outputs={"messages": {"type": "array"}}),
        ]

    async def execute(self, capability: str, inputs: dict) -> ActionResult:
        return ActionResult(success=True, data={"placeholder": True})

    async def test_connection(self) -> bool:
        return False
