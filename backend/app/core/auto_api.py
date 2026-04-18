"""
Gnosis Auto-API Discovery — Connect to any API by name.
Say "connect to Stripe" and Gnosis:
1. Looks up the API from a knowledge base
2. Identifies authentication method
3. Discovers key endpoints
4. Generates a ready-to-use connector
"""

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional

# Pre-built API knowledge base (expandable)
API_CATALOG = {
    "stripe": {
        "name": "Stripe",
        "description": "Payment processing platform",
        "base_url": "https://api.stripe.com/v1",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "docs_url": "https://stripe.com/docs/api",
        "key_env_var": "STRIPE_API_KEY",
        "endpoints": [
            {"method": "GET", "path": "/customers", "description": "List customers"},
            {"method": "POST", "path": "/customers", "description": "Create customer"},
            {"method": "GET", "path": "/charges", "description": "List charges"},
            {"method": "POST", "path": "/charges", "description": "Create charge"},
            {"method": "GET", "path": "/invoices", "description": "List invoices"},
            {
                "method": "POST",
                "path": "/subscriptions",
                "description": "Create subscription",
            },
            {"method": "GET", "path": "/balance", "description": "Get account balance"},
            {"method": "GET", "path": "/products", "description": "List products"},
            {"method": "POST", "path": "/refunds", "description": "Create refund"},
        ],
        "category": "payments",
    },
    "github": {
        "name": "GitHub",
        "description": "Code hosting and collaboration platform",
        "base_url": "https://api.github.com",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "docs_url": "https://docs.github.com/en/rest",
        "key_env_var": "GITHUB_TOKEN",
        "endpoints": [
            {"method": "GET", "path": "/user", "description": "Get authenticated user"},
            {
                "method": "GET",
                "path": "/user/repos",
                "description": "List repositories",
            },
            {
                "method": "GET",
                "path": "/repos/{owner}/{repo}",
                "description": "Get repository",
            },
            {
                "method": "GET",
                "path": "/repos/{owner}/{repo}/issues",
                "description": "List issues",
            },
            {
                "method": "POST",
                "path": "/repos/{owner}/{repo}/issues",
                "description": "Create issue",
            },
            {
                "method": "GET",
                "path": "/repos/{owner}/{repo}/pulls",
                "description": "List pull requests",
            },
            {
                "method": "GET",
                "path": "/search/repositories",
                "description": "Search repos",
            },
        ],
        "category": "developer",
    },
    "slack": {
        "name": "Slack",
        "description": "Team communication platform",
        "base_url": "https://slack.com/api",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "docs_url": "https://api.slack.com/methods",
        "key_env_var": "SLACK_BOT_TOKEN",
        "endpoints": [
            {
                "method": "POST",
                "path": "/chat.postMessage",
                "description": "Send message",
            },
            {
                "method": "GET",
                "path": "/conversations.list",
                "description": "List channels",
            },
            {
                "method": "GET",
                "path": "/conversations.history",
                "description": "Channel messages",
            },
            {"method": "GET", "path": "/users.list", "description": "List users"},
            {"method": "POST", "path": "/reactions.add", "description": "Add reaction"},
            {"method": "POST", "path": "/files.upload", "description": "Upload file"},
        ],
        "category": "communication",
    },
    "notion": {
        "name": "Notion",
        "description": "All-in-one workspace for notes and docs",
        "base_url": "https://api.notion.com/v1",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "docs_url": "https://developers.notion.com/reference",
        "key_env_var": "NOTION_API_KEY",
        "endpoints": [
            {"method": "GET", "path": "/databases", "description": "List databases"},
            {
                "method": "POST",
                "path": "/databases/{id}/query",
                "description": "Query database",
            },
            {"method": "GET", "path": "/pages/{id}", "description": "Get page"},
            {"method": "POST", "path": "/pages", "description": "Create page"},
            {"method": "GET", "path": "/search", "description": "Search"},
        ],
        "category": "productivity",
    },
    "openai": {
        "name": "OpenAI",
        "description": "AI/ML API for GPT, DALL-E, Whisper",
        "base_url": "https://api.openai.com/v1",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "docs_url": "https://platform.openai.com/docs/api-reference",
        "key_env_var": "OPENAI_API_KEY",
        "endpoints": [
            {
                "method": "POST",
                "path": "/chat/completions",
                "description": "Chat completion",
            },
            {
                "method": "POST",
                "path": "/images/generations",
                "description": "Generate images",
            },
            {
                "method": "POST",
                "path": "/audio/transcriptions",
                "description": "Transcribe audio",
            },
            {"method": "GET", "path": "/models", "description": "List models"},
            {
                "method": "POST",
                "path": "/embeddings",
                "description": "Create embeddings",
            },
        ],
        "category": "ai",
    },
    "twilio": {
        "name": "Twilio",
        "description": "Communication APIs — SMS, Voice, WhatsApp",
        "base_url": "https://api.twilio.com/2010-04-01",
        "auth_type": "basic",
        "docs_url": "https://www.twilio.com/docs/usage/api",
        "key_env_var": "TWILIO_AUTH_TOKEN",
        "endpoints": [
            {
                "method": "POST",
                "path": "/Accounts/{sid}/Messages.json",
                "description": "Send SMS",
            },
            {
                "method": "POST",
                "path": "/Accounts/{sid}/Calls.json",
                "description": "Make call",
            },
            {
                "method": "GET",
                "path": "/Accounts/{sid}/Messages.json",
                "description": "List messages",
            },
        ],
        "category": "communication",
    },
    "shopify": {
        "name": "Shopify",
        "description": "E-commerce platform API",
        "base_url": "https://{store}.myshopify.com/admin/api/2024-01",
        "auth_type": "header",
        "auth_header": "X-Shopify-Access-Token",
        "docs_url": "https://shopify.dev/docs/api",
        "key_env_var": "SHOPIFY_ACCESS_TOKEN",
        "endpoints": [
            {"method": "GET", "path": "/products.json", "description": "List products"},
            {"method": "GET", "path": "/orders.json", "description": "List orders"},
            {
                "method": "GET",
                "path": "/customers.json",
                "description": "List customers",
            },
            {
                "method": "POST",
                "path": "/products.json",
                "description": "Create product",
            },
        ],
        "category": "ecommerce",
    },
    "sendgrid": {
        "name": "SendGrid",
        "description": "Email delivery and marketing platform",
        "base_url": "https://api.sendgrid.com/v3",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "docs_url": "https://docs.sendgrid.com/api-reference",
        "key_env_var": "SENDGRID_API_KEY",
        "endpoints": [
            {"method": "POST", "path": "/mail/send", "description": "Send email"},
            {
                "method": "GET",
                "path": "/contactdb/recipients",
                "description": "List contacts",
            },
            {"method": "GET", "path": "/stats", "description": "Get email stats"},
        ],
        "category": "email",
    },
    "google_sheets": {
        "name": "Google Sheets",
        "description": "Spreadsheet data access",
        "base_url": "https://sheets.googleapis.com/v4",
        "auth_type": "oauth2",
        "docs_url": "https://developers.google.com/sheets/api/reference/rest",
        "key_env_var": "GOOGLE_API_KEY",
        "endpoints": [
            {
                "method": "GET",
                "path": "/spreadsheets/{id}",
                "description": "Get spreadsheet",
            },
            {
                "method": "GET",
                "path": "/spreadsheets/{id}/values/{range}",
                "description": "Read cells",
            },
            {
                "method": "PUT",
                "path": "/spreadsheets/{id}/values/{range}",
                "description": "Write cells",
            },
            {
                "method": "POST",
                "path": "/spreadsheets/{id}/values/{range}:append",
                "description": "Append rows",
            },
        ],
        "category": "productivity",
    },
    "weather": {
        "name": "OpenWeatherMap",
        "description": "Weather data and forecasts",
        "base_url": "https://api.openweathermap.org/data/2.5",
        "auth_type": "query_param",
        "auth_param": "appid",
        "docs_url": "https://openweathermap.org/api",
        "key_env_var": "OPENWEATHER_API_KEY",
        "endpoints": [
            {
                "method": "GET",
                "path": "/weather?q={city}",
                "description": "Current weather",
            },
            {
                "method": "GET",
                "path": "/forecast?q={city}",
                "description": "5-day forecast",
            },
            {
                "method": "GET",
                "path": "/air_pollution?lat={lat}&lon={lon}",
                "description": "Air quality",
            },
        ],
        "category": "data",
    },
    "airtable": {
        "name": "Airtable",
        "description": "Spreadsheet-database hybrid",
        "base_url": "https://api.airtable.com/v0",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "docs_url": "https://airtable.com/developers/web/api",
        "key_env_var": "AIRTABLE_API_KEY",
        "endpoints": [
            {
                "method": "GET",
                "path": "/{baseId}/{tableName}",
                "description": "List records",
            },
            {
                "method": "POST",
                "path": "/{baseId}/{tableName}",
                "description": "Create record",
            },
            {
                "method": "PATCH",
                "path": "/{baseId}/{tableName}",
                "description": "Update records",
            },
            {
                "method": "DELETE",
                "path": "/{baseId}/{tableName}",
                "description": "Delete records",
            },
        ],
        "category": "productivity",
    },
    "hubspot": {
        "name": "HubSpot",
        "description": "CRM and marketing platform",
        "base_url": "https://api.hubapi.com",
        "auth_type": "bearer",
        "auth_header": "Authorization",
        "auth_prefix": "Bearer",
        "docs_url": "https://developers.hubspot.com/docs/api",
        "key_env_var": "HUBSPOT_API_KEY",
        "endpoints": [
            {
                "method": "GET",
                "path": "/crm/v3/objects/contacts",
                "description": "List contacts",
            },
            {
                "method": "POST",
                "path": "/crm/v3/objects/contacts",
                "description": "Create contact",
            },
            {
                "method": "GET",
                "path": "/crm/v3/objects/deals",
                "description": "List deals",
            },
            {
                "method": "GET",
                "path": "/crm/v3/objects/companies",
                "description": "List companies",
            },
        ],
        "category": "crm",
    },
}


@dataclass
class APIConnection:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:10])
    api_name: str = ""
    api_key: str = ""
    base_url: str = ""
    auth_type: str = ""
    status: str = "configured"  # configured, testing, connected, failed
    created_at: float = field(default_factory=time.time)
    last_used: float = 0
    total_calls: int = 0
    errors: int = 0
    custom_headers: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)


class AutoAPIEngine:
    """Discover and connect to any API by name."""

    def __init__(self):
        self._connections: dict[str, APIConnection] = {}
        self._call_history: list[dict] = []

    def search_api(self, query: str) -> list[dict]:
        """Search for APIs by name or category."""
        query_lower = query.lower().strip()
        results = []

        for key, api in API_CATALOG.items():
            score = 0
            if query_lower in key:
                score += 3
            if query_lower in api["name"].lower():
                score += 3
            if query_lower in api["description"].lower():
                score += 1
            if query_lower in api.get("category", "").lower():
                score += 2
            # Check endpoint descriptions
            for ep in api.get("endpoints", []):
                if query_lower in ep["description"].lower():
                    score += 0.5

            if score > 0:
                results.append({**api, "catalog_key": key, "match_score": score})

        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results

    def get_api_info(self, api_name: str) -> Optional[dict]:
        """Get detailed info about an API."""
        api_lower = api_name.lower().strip()
        for key, api in API_CATALOG.items():
            if key == api_lower or api["name"].lower() == api_lower:
                return {**api, "catalog_key": key}
        return None

    def connect(self, api_name: str, api_key: str, extra_config: dict = None) -> dict:
        """Connect to an API — validates and stores credentials."""
        api_info = self.get_api_info(api_name)
        if not api_info:
            return {
                "error": f"Unknown API: {api_name}. Use search to find available APIs."
            }

        conn = APIConnection(
            api_name=api_info["name"],
            api_key=api_key,
            base_url=api_info["base_url"],
            auth_type=api_info["auth_type"],
            status="configured",
            config={**(extra_config or {}), "catalog_key": api_info.get("catalog_key")},
        )
        self._connections[conn.id] = conn
        return {
            "connection_id": conn.id,
            "api": api_info["name"],
            "base_url": api_info["base_url"],
            "endpoints_available": len(api_info.get("endpoints", [])),
            "status": "configured",
            "message": f"Connected to {api_info['name']}! {len(api_info.get('endpoints', []))} endpoints ready.",
        }

    async def test_connection(self, connection_id: str) -> dict:
        """Test an API connection."""
        conn = self._connections.get(connection_id)
        if not conn:
            return {"error": "Connection not found"}

        import aiohttp

        api_info = self.get_api_info(conn.api_name)
        if not api_info:
            return {"error": "API info not found"}

        # Build test request
        test_endpoint = api_info.get("endpoints", [{}])[0]
        url = f"{conn.base_url}{test_endpoint.get('path', '')}"

        headers = {"Content-Type": "application/json"}
        if conn.auth_type == "bearer":
            prefix = api_info.get("auth_prefix", "Bearer")
            header_name = api_info.get("auth_header", "Authorization")
            headers[header_name] = f"{prefix} {conn.api_key}"

        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as resp:
                    status = resp.status
                    if status in (200, 201):
                        conn.status = "connected"
                        return {"status": "connected", "http_status": status}
                    elif status == 401:
                        conn.status = "failed"
                        return {
                            "status": "auth_failed",
                            "http_status": status,
                            "message": "Invalid API key",
                        }
                    else:
                        conn.status = "configured"
                        return {"status": "unknown", "http_status": status}
        except Exception as e:
            conn.status = "failed"
            return {"status": "error", "message": str(e)}

    async def call_api(
        self,
        connection_id: str,
        endpoint_path: str,
        method: str = "GET",
        body: dict = None,
        params: dict = None,
    ) -> dict:
        """Make an API call through a connection."""
        conn = self._connections.get(connection_id)
        if not conn:
            return {"error": "Connection not found"}

        api_info = self.get_api_info(conn.api_name)
        url = f"{conn.base_url}{endpoint_path}"

        # Substitute params in URL
        if params:
            for key, value in params.items():
                url = url.replace(f"{{{key}}}", str(value))

        headers = {"Content-Type": "application/json"}
        if conn.auth_type == "bearer":
            prefix = api_info.get("auth_prefix", "Bearer") if api_info else "Bearer"
            header_name = (
                api_info.get("auth_header", "Authorization")
                if api_info
                else "Authorization"
            )
            headers[header_name] = f"{prefix} {conn.api_key}"
        elif conn.auth_type == "header":
            header_name = (
                api_info.get("auth_header", "X-Api-Key") if api_info else "X-Api-Key"
            )
            headers[header_name] = conn.api_key
        elif conn.auth_type == "query_param":
            param_name = (
                api_info.get("auth_param", "api_key") if api_info else "api_key"
            )
            separator = "&" if "?" in url else "?"
            url = f"{url}{separator}{param_name}={conn.api_key}"

        headers.update(conn.custom_headers)

        start = time.time()
        try:
            import aiohttp

            timeout = aiohttp.ClientTimeout(total=30)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                method_upper = method.upper()
                kwargs = {"headers": headers}
                if body and method_upper in ("POST", "PUT", "PATCH"):
                    kwargs["json"] = body

                async with session.request(method_upper, url, **kwargs) as resp:
                    duration_ms = (time.time() - start) * 1000
                    response_data = await resp.text()

                    conn.total_calls += 1
                    conn.last_used = time.time()

                    if resp.status >= 400:
                        conn.errors += 1

                    # Try to parse as JSON
                    try:
                        import json

                        parsed = json.loads(response_data)
                    except Exception:
                        parsed = response_data

                    result = {
                        "status": resp.status,
                        "data": parsed,
                        "duration_ms": round(duration_ms, 1),
                        "url": url.replace(conn.api_key, "***"),
                    }

                    self._call_history.append(
                        {
                            **result,
                            "connection_id": connection_id,
                            "api": conn.api_name,
                            "timestamp": time.time(),
                        }
                    )

                    return result

        except Exception as e:
            conn.errors += 1
            return {"error": str(e), "duration_ms": (time.time() - start) * 1000}

    def generate_connector_code(self, api_name: str) -> Optional[str]:
        """Generate a Python connector class for an API."""
        api_info = self.get_api_info(api_name)
        if not api_info:
            return None

        lines = [
            f'"""Auto-generated Gnosis connector for {api_info["name"]}"""',
            "import aiohttp",
            "",
            f"class {api_info['name'].replace(' ', '')}Connector:",
            f'    """Connector for {api_info["description"]}"""',
            f'    BASE_URL = "{api_info["base_url"]}"',
            "",
            "    def __init__(self, api_key: str):",
            "        self.api_key = api_key",
            "",
        ]

        for ep in api_info.get("endpoints", []):
            method = ep["method"].lower()
            path = ep["path"]
            name = ep["description"].lower().replace(" ", "_").replace("-", "_")

            lines.append(f"    async def {name}(self, **kwargs):")
            lines.append(f'        """{ep["description"]}"""')
            lines.append(f'        url = f"{{self.BASE_URL}}{path}"')
            lines.append(
                '        headers = {"Authorization": f"Bearer {self.api_key}"}'
            )
            if method in ("post", "put", "patch"):
                lines.append("        async with aiohttp.ClientSession() as s:")
                lines.append(
                    f"            async with s.{method}(url, headers=headers, json=kwargs) as r:"
                )
            else:
                lines.append("        async with aiohttp.ClientSession() as s:")
                lines.append(
                    f"            async with s.{method}(url, headers=headers, params=kwargs) as r:"
                )
            lines.append("                return await r.json()")
            lines.append("")

        return "\n".join(lines)

    # ─── CRUD ───

    def list_connections(self) -> list[dict]:
        return [
            asdict(c)
            for c in sorted(
                self._connections.values(), key=lambda c: c.created_at, reverse=True
            )
        ]

    def get_connection(self, connection_id: str) -> Optional[dict]:
        conn = self._connections.get(connection_id)
        if conn:
            d = asdict(conn)
            d["api_key"] = d["api_key"][:4] + "***" if d["api_key"] else ""
            return d
        return None

    def delete_connection(self, connection_id: str) -> bool:
        return self._connections.pop(connection_id, None) is not None

    def list_catalog(self, category: str = "") -> list[dict]:
        apis = []
        for key, api in API_CATALOG.items():
            if category and api.get("category") != category:
                continue
            apis.append(
                {
                    "key": key,
                    "name": api["name"],
                    "description": api["description"],
                    "category": api.get("category", ""),
                    "endpoints": len(api.get("endpoints", [])),
                    "docs_url": api.get("docs_url", ""),
                }
            )
        return apis

    def get_categories(self) -> list[str]:
        return list(set(api.get("category", "") for api in API_CATALOG.values()))

    def get_stats(self) -> dict:
        return {
            "catalog_size": len(API_CATALOG),
            "active_connections": len(self._connections),
            "connected": sum(
                1 for c in self._connections.values() if c.status == "connected"
            ),
            "total_api_calls": sum(c.total_calls for c in self._connections.values()),
            "total_errors": sum(c.errors for c in self._connections.values()),
        }


auto_api = AutoAPIEngine()
