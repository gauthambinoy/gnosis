"""Google Sheets connector — UAP compliant, real Sheets API v4 integration."""
import logging
import time
from urllib.parse import quote

import aiohttp

from app.integrations.base import BaseConnector, ActionDefinition, ActionResult
from app.integrations.oauth import oauth_manager

SHEETS_API = "https://sheets.googleapis.com/v4/spreadsheets"
logger = logging.getLogger(__name__)

_TIMEOUT = aiohttp.ClientTimeout(total=15, connect=5)


class SheetsConnector(BaseConnector):
    def __init__(self, credentials: dict | None = None):
        self.credentials = credentials or {}
        self._session: aiohttp.ClientSession | None = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(timeout=_TIMEOUT)
        return self._session

    async def close(self):
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def get_actions(self) -> list[ActionDefinition]:
        return [
            ActionDefinition(
                service="sheets", capability="read_range",
                description="Read data from a spreadsheet range",
                inputs={"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}},
                outputs={"values": {"type": "array"}},
            ),
            ActionDefinition(
                service="sheets", capability="write_range",
                description="Write data to a spreadsheet range",
                inputs={"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}, "values": {"type": "array"}},
                outputs={"updatedCells": {"type": "integer"}},
            ),
            ActionDefinition(
                service="sheets", capability="append_rows",
                description="Append rows to a spreadsheet",
                inputs={"spreadsheet_id": {"type": "string"}, "range": {"type": "string"}, "rows": {"type": "array"}},
                outputs={"updates": {"type": "object"}},
            ),
            ActionDefinition(
                service="sheets", capability="search_cells",
                description="Search for a value across all cells",
                inputs={"spreadsheet_id": {"type": "string"}, "query": {"type": "string"}},
                outputs={"matches": {"type": "array"}},
            ),
            ActionDefinition(
                service="sheets", capability="create_spreadsheet",
                description="Create a new spreadsheet",
                inputs={"title": {"type": "string"}},
                outputs={"spreadsheetId": {"type": "string"}, "spreadsheetUrl": {"type": "string"}},
            ),
        ]

    async def _get_headers(self, user_id: str) -> dict:
        token = await oauth_manager.get_valid_token("google", user_id)
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    # ------------------------------------------------------------------
    # Real Sheets API methods
    # ------------------------------------------------------------------

    async def read_range(self, user_id: str, spreadsheet_id: str, range_: str) -> list[list]:
        headers = await self._get_headers(user_id)
        url = f"{SHEETS_API}/{spreadsheet_id}/values/{quote(range_)}"
        session = await self._get_session()
        async with session.get(url, headers=headers) as resp:
            data = await resp.json()
        return data.get("values", [])

    async def write_range(
        self, user_id: str, spreadsheet_id: str, range_: str, values: list[list]
    ) -> dict:
        headers = await self._get_headers(user_id)
        url = f"{SHEETS_API}/{spreadsheet_id}/values/{quote(range_)}"
        params = {"valueInputOption": "USER_ENTERED"}
        session = await self._get_session()
        async with session.put(
            url, headers={**headers, "Content-Type": "application/json"},
            params=params, json={"range": range_, "majorDimension": "ROWS", "values": values},
        ) as resp:
            data = await resp.json()
        return {
            "updatedRange": data.get("updatedRange"),
            "updatedRows": data.get("updatedRows"),
            "updatedCells": data.get("updatedCells"),
        }

    async def append_rows(
        self, user_id: str, spreadsheet_id: str, range_: str, rows: list[list]
    ) -> dict:
        headers = await self._get_headers(user_id)
        url = f"{SHEETS_API}/{spreadsheet_id}/values/{quote(range_)}:append"
        params = {"valueInputOption": "USER_ENTERED", "insertDataOption": "INSERT_ROWS"}
        session = await self._get_session()
        async with session.post(
            url, headers={**headers, "Content-Type": "application/json"},
            params=params, json={"majorDimension": "ROWS", "values": rows},
        ) as resp:
            data = await resp.json()
        updates = data.get("updates", {})
        return {
            "updatedRange": updates.get("updatedRange"),
            "updatedRows": updates.get("updatedRows"),
            "updatedCells": updates.get("updatedCells"),
        }

    async def search_cells(
        self, user_id: str, spreadsheet_id: str, query: str
    ) -> list[dict]:
        """Read entire spreadsheet and search for matching cells."""
        headers = await self._get_headers(user_id)
        session = await self._get_session()
        async with session.get(f"{SHEETS_API}/{spreadsheet_id}", headers=headers) as resp:
            meta = await resp.json()

        sheets = [s["properties"]["title"] for s in meta.get("sheets", [])]
        matches: list[dict] = []
        query_lower = query.lower()

        for sheet_name in sheets:
            values = await self.read_range(user_id, spreadsheet_id, f"'{sheet_name}'")
            for row_idx, row in enumerate(values):
                for col_idx, cell in enumerate(row):
                    if query_lower in str(cell).lower():
                        matches.append({
                            "sheet": sheet_name,
                            "row": row_idx + 1,
                            "column": col_idx + 1,
                            "value": cell,
                        })
        return matches

    async def create_spreadsheet(self, user_id: str, title: str) -> dict:
        headers = await self._get_headers(user_id)
        session = await self._get_session()
        async with session.post(
            SHEETS_API,
            headers={**headers, "Content-Type": "application/json"},
            json={"properties": {"title": title}},
        ) as resp:
            data = await resp.json()
        return {
            "spreadsheetId": data.get("spreadsheetId"),
            "spreadsheetUrl": data.get("spreadsheetUrl"),
        }

    # ------------------------------------------------------------------
    # UAP interface
    # ------------------------------------------------------------------

    async def execute(self, capability: str, inputs: dict) -> ActionResult:
        start = time.time()
        try:
            dispatch = {
                "read_range": lambda: self.read_range(
                    inputs["user_id"], inputs["spreadsheet_id"], inputs["range"]
                ),
                "write_range": lambda: self.write_range(
                    inputs["user_id"], inputs["spreadsheet_id"], inputs["range"], inputs["values"]
                ),
                "append_rows": lambda: self.append_rows(
                    inputs["user_id"], inputs["spreadsheet_id"], inputs["range"], inputs["rows"]
                ),
                "search_cells": lambda: self.search_cells(
                    inputs["user_id"], inputs["spreadsheet_id"], inputs["query"]
                ),
                "create_spreadsheet": lambda: self.create_spreadsheet(
                    inputs["user_id"], inputs["title"]
                ),
            }
            handler = dispatch.get(capability)
            if not handler:
                return ActionResult(success=False, data={}, error=f"Unknown capability: {capability}")
            result = await handler()
            latency = (time.time() - start) * 1000
            return ActionResult(
                success=True,
                data=result if isinstance(result, dict) else {"values": result},
                latency_ms=latency,
            )
        except Exception as exc:
            latency = (time.time() - start) * 1000
            return ActionResult(success=False, data={}, error=str(exc), latency_ms=latency)

    async def test_connection(self) -> bool:
        try:
            token = await oauth_manager.get_valid_token("google", "default")
            return bool(token)
        except Exception:
            return False
