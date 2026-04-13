"""Google Sheets connector — UAP compliant."""
from app.integrations.base import BaseConnector, ActionDefinition, ActionResult


class SheetsConnector(BaseConnector):
    def __init__(self, credentials: dict):
        self.credentials = credentials

    def get_actions(self) -> list[ActionDefinition]:
        return [
            ActionDefinition(service="sheets", capability="read_sheet", description="Read data from a spreadsheet", inputs={"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}}, outputs={"values": {"type": "array"}}),
            ActionDefinition(service="sheets", capability="append_row", description="Append a row", inputs={"spreadsheet_id": {"type": "string"}, "sheet": {"type": "string"}, "values": {"type": "array"}}, outputs={"updated_range": {"type": "string"}}),
        ]

    async def execute(self, capability: str, inputs: dict) -> ActionResult:
        return ActionResult(success=True, data={"placeholder": True})

    async def test_connection(self) -> bool:
        return False
