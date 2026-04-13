"""Gmail connector — UAP compliant."""
from app.integrations.base import BaseConnector, ActionDefinition, ActionResult


class GmailConnector(BaseConnector):
    def __init__(self, credentials: dict):
        self.credentials = credentials

    def get_actions(self) -> list[ActionDefinition]:
        return [
            ActionDefinition(service="gmail", capability="read_inbox", description="List emails from inbox", inputs={"query": {"type": "string"}, "max_results": {"type": "integer"}}, outputs={"emails": {"type": "array"}}),
            ActionDefinition(service="gmail", capability="send_email", description="Send an email", inputs={"to": {"type": "email"}, "subject": {"type": "string"}, "body": {"type": "string"}}, outputs={"message_id": {"type": "string"}}),
        ]

    async def execute(self, capability: str, inputs: dict) -> ActionResult:
        return ActionResult(success=True, data={"placeholder": True})

    async def test_connection(self) -> bool:
        return False
