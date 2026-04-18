"""
Gnosis RPA Engine — Record & Replay Browser Automation
Records user actions (click, type, scroll, navigate, wait, screenshot)
and replays them via Playwright or generates executable scripts.
"""

import asyncio
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Optional
from enum import Enum


class ActionType(str, Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    PRESS_KEY = "press_key"
    SCROLL = "scroll"
    NAVIGATE = "navigate"
    WAIT = "wait"
    WAIT_FOR_SELECTOR = "wait_for_selector"
    SCREENSHOT = "screenshot"
    SELECT = "select"
    HOVER = "hover"
    DRAG_DROP = "drag_drop"
    ASSERT_TEXT = "assert_text"
    ASSERT_VISIBLE = "assert_visible"
    EXTRACT_TEXT = "extract_text"
    EXTRACT_ATTRIBUTE = "extract_attribute"
    CONDITIONAL = "conditional"
    LOOP = "loop"


@dataclass
class RecordedAction:
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    action_type: str = "click"
    selector: str = ""  # CSS selector
    xpath: str = ""  # XPath alternative
    value: str = ""  # For type/navigate/select
    description: str = ""  # Human-readable description
    x: int = 0  # Click coordinates (fallback)
    y: int = 0
    timestamp: float = field(default_factory=time.time)
    wait_before_ms: int = 0
    wait_after_ms: int = 500
    screenshot_before: bool = False
    screenshot_after: bool = False
    # For conditional/loop
    condition: str = ""  # JS expression
    max_iterations: int = 10
    children: list = field(default_factory=list)  # Nested actions for loop/conditional
    # Metadata
    page_url: str = ""
    element_tag: str = ""
    element_text: str = ""
    element_id: str = ""
    element_class: str = ""


@dataclass
class AutomationWorkflow:
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    name: str = "Untitled Workflow"
    description: str = ""
    created_by: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    actions: list[dict] = field(default_factory=list)
    variables: dict = field(default_factory=dict)  # User-defined variables
    start_url: str = ""
    tags: list[str] = field(default_factory=list)
    schedule: str = ""  # Cron expression for scheduled runs
    status: str = "draft"  # draft, active, paused, archived
    last_run_at: float = 0
    last_run_status: str = ""
    run_count: int = 0
    avg_duration_ms: float = 0


@dataclass
class ExecutionResult:
    workflow_id: str = ""
    run_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])
    status: str = "pending"  # pending, running, completed, failed, stopped
    started_at: float = field(default_factory=time.time)
    completed_at: float = 0
    duration_ms: float = 0
    actions_total: int = 0
    actions_completed: int = 0
    actions_failed: int = 0
    current_action: str = ""
    error: str = ""
    screenshots: list[str] = field(default_factory=list)
    extracted_data: list[dict] = field(default_factory=list)
    logs: list[dict] = field(default_factory=list)


class RPAEngine:
    """Records and replays browser automation workflows."""

    def __init__(self):
        self._workflows: dict[str, AutomationWorkflow] = {}
        self._recordings: dict[str, list[RecordedAction]] = {}  # session_id -> actions
        self._executions: dict[str, ExecutionResult] = {}
        self._running: dict[str, bool] = {}  # workflow_id -> is_running
        self._playwright_available = False
        self._check_playwright()

    def _check_playwright(self):
        try:
            import playwright  # noqa: F401

            self._playwright_available = True
        except ImportError:
            self._playwright_available = False

    # ─── Recording ───

    def start_recording(self, user_id: str = "", start_url: str = "") -> str:
        """Start a new recording session. Returns session_id."""
        session_id = uuid.uuid4().hex[:12]
        self._recordings[session_id] = []
        return session_id

    def record_action(self, session_id: str, action: dict) -> dict:
        """Record a single action from the browser."""
        if session_id not in self._recordings:
            return {"error": "Invalid session"}

        recorded = RecordedAction(
            action_type=action.get("action_type", "click"),
            selector=action.get("selector", ""),
            xpath=action.get("xpath", ""),
            value=action.get("value", ""),
            description=action.get("description", ""),
            x=action.get("x", 0),
            y=action.get("y", 0),
            wait_before_ms=action.get("wait_before_ms", 0),
            wait_after_ms=action.get("wait_after_ms", 500),
            page_url=action.get("page_url", ""),
            element_tag=action.get("element_tag", ""),
            element_text=action.get("element_text", ""),
            element_id=action.get("element_id", ""),
            element_class=action.get("element_class", ""),
        )
        self._recordings[session_id].append(recorded)
        return {
            "action_id": recorded.id,
            "index": len(self._recordings[session_id]) - 1,
        }

    def stop_recording(
        self, session_id: str, name: str = "", description: str = ""
    ) -> Optional[dict]:
        """Stop recording and save as a workflow."""
        if session_id not in self._recordings:
            return None

        actions = self._recordings.pop(session_id)
        if not actions:
            return {"error": "No actions recorded"}

        workflow = AutomationWorkflow(
            name=name or f"Recording {time.strftime('%Y-%m-%d %H:%M')}",
            description=description or f"Recorded {len(actions)} actions",
            actions=[asdict(a) for a in actions],
            start_url=actions[0].page_url if actions else "",
        )
        self._workflows[workflow.id] = workflow
        return asdict(workflow)

    def get_recording_actions(self, session_id: str) -> list[dict]:
        """Get actions recorded so far in a session."""
        actions = self._recordings.get(session_id, [])
        return [asdict(a) for a in actions]

    # ─── Workflow CRUD ───

    def create_workflow(self, data: dict) -> dict:
        wf = AutomationWorkflow(
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            actions=data.get("actions", []),
            variables=data.get("variables", {}),
            start_url=data.get("start_url", ""),
            tags=data.get("tags", []),
            schedule=data.get("schedule", ""),
            created_by=data.get("created_by", ""),
        )
        self._workflows[wf.id] = wf
        return asdict(wf)

    def get_workflow(self, workflow_id: str) -> Optional[dict]:
        wf = self._workflows.get(workflow_id)
        return asdict(wf) if wf else None

    def list_workflows(self, tag: str = "", status: str = "") -> list[dict]:
        workflows = list(self._workflows.values())
        if tag:
            workflows = [w for w in workflows if tag in w.tags]
        if status:
            workflows = [w for w in workflows if w.status == status]
        workflows.sort(key=lambda w: w.updated_at, reverse=True)
        return [asdict(w) for w in workflows]

    def update_workflow(self, workflow_id: str, data: dict) -> Optional[dict]:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return None
        for key in [
            "name",
            "description",
            "actions",
            "variables",
            "start_url",
            "tags",
            "schedule",
            "status",
        ]:
            if key in data:
                setattr(wf, key, data[key])
        wf.updated_at = time.time()
        return asdict(wf)

    def delete_workflow(self, workflow_id: str) -> bool:
        return self._workflows.pop(workflow_id, None) is not None

    def duplicate_workflow(self, workflow_id: str) -> Optional[dict]:
        wf = self._workflows.get(workflow_id)
        if not wf:
            return None
        new_wf = AutomationWorkflow(
            name=f"{wf.name} (Copy)",
            description=wf.description,
            actions=wf.actions.copy(),
            variables=wf.variables.copy(),
            start_url=wf.start_url,
            tags=wf.tags.copy(),
            created_by=wf.created_by,
        )
        self._workflows[new_wf.id] = new_wf
        return asdict(new_wf)

    # ─── Execution ───

    async def execute_workflow(self, workflow_id: str, variables: dict = None) -> dict:
        """Execute a workflow. Uses Playwright if available, otherwise simulates."""
        wf = self._workflows.get(workflow_id)
        if not wf:
            return {"error": "Workflow not found"}

        result = ExecutionResult(
            workflow_id=workflow_id,
            actions_total=len(wf.actions),
            status="running",
        )
        self._executions[result.run_id] = result
        self._running[workflow_id] = True

        # Merge variables
        exec_vars = {**wf.variables, **(variables or {})}

        try:
            if self._playwright_available:
                await self._execute_with_playwright(wf, result, exec_vars)
            else:
                await self._execute_simulated(wf, result, exec_vars)

            result.status = (
                "completed" if result.actions_failed == 0 else "completed_with_errors"
            )
        except Exception as e:
            result.status = "failed"
            result.error = str(e)
        finally:
            result.completed_at = time.time()
            result.duration_ms = (result.completed_at - result.started_at) * 1000
            self._running[workflow_id] = False

            # Update workflow stats
            wf.last_run_at = time.time()
            wf.last_run_status = result.status
            wf.run_count += 1
            if wf.avg_duration_ms == 0:
                wf.avg_duration_ms = result.duration_ms
            else:
                wf.avg_duration_ms = (wf.avg_duration_ms * 0.8) + (
                    result.duration_ms * 0.2
                )

        return asdict(result)

    async def _execute_with_playwright(self, wf, result, variables):
        """Execute using real Playwright browser automation."""
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            if wf.start_url:
                url = self._interpolate(wf.start_url, variables)
                await page.goto(url)
                result.logs.append({"action": "navigate", "url": url, "status": "ok"})

            for i, action_data in enumerate(wf.actions):
                if not self._running.get(wf.id, False):
                    result.logs.append({"action": "stopped", "index": i})
                    break

                action_type = action_data.get("action_type", "")
                selector = self._interpolate(action_data.get("selector", ""), variables)
                value = self._interpolate(action_data.get("value", ""), variables)
                result.current_action = f"{action_type}: {selector or value}"

                wait_before = action_data.get("wait_before_ms", 0)
                if wait_before > 0:
                    await asyncio.sleep(wait_before / 1000)

                try:
                    if action_type == "click":
                        await page.click(selector, timeout=10000)
                    elif action_type == "double_click":
                        await page.dblclick(selector, timeout=10000)
                    elif action_type == "type":
                        await page.fill(selector, value, timeout=10000)
                    elif action_type == "press_key":
                        await page.keyboard.press(value)
                    elif action_type == "navigate":
                        await page.goto(value)
                    elif action_type == "wait":
                        await asyncio.sleep(float(value) / 1000 if value else 1)
                    elif action_type == "wait_for_selector":
                        await page.wait_for_selector(selector, timeout=30000)
                    elif action_type == "screenshot":
                        path = f"gnosis_screenshot_{result.run_id}_{i}.png"
                        await page.screenshot(path=path)
                        result.screenshots.append(path)
                    elif action_type == "select":
                        await page.select_option(selector, value)
                    elif action_type == "hover":
                        await page.hover(selector, timeout=10000)
                    elif action_type == "scroll":
                        await page.evaluate(
                            f"window.scrollBy(0, {action_data.get('y', 300)})"
                        )
                    elif action_type == "extract_text":
                        text = await page.text_content(selector)
                        result.extracted_data.append(
                            {"selector": selector, "text": text, "index": i}
                        )
                    elif action_type == "extract_attribute":
                        attr = action_data.get("value", "href")
                        val = await page.get_attribute(selector, attr)
                        result.extracted_data.append(
                            {
                                "selector": selector,
                                "attribute": attr,
                                "value": val,
                                "index": i,
                            }
                        )
                    elif action_type == "assert_text":
                        text = await page.text_content(selector)
                        if value not in (text or ""):
                            raise AssertionError(f"Expected '{value}' in '{text}'")
                    elif action_type == "assert_visible":
                        visible = await page.is_visible(selector)
                        if not visible:
                            raise AssertionError(f"Element {selector} not visible")

                    result.actions_completed += 1
                    result.logs.append(
                        {
                            "action": action_type,
                            "selector": selector,
                            "status": "ok",
                            "index": i,
                        }
                    )

                except Exception as e:
                    result.actions_failed += 1
                    result.logs.append(
                        {
                            "action": action_type,
                            "selector": selector,
                            "status": "error",
                            "error": str(e),
                            "index": i,
                        }
                    )

                wait_after = action_data.get("wait_after_ms", 500)
                if wait_after > 0:
                    await asyncio.sleep(wait_after / 1000)

            await browser.close()

    async def _execute_simulated(self, wf, result, variables):
        """Simulate execution when Playwright is not available."""
        for i, action_data in enumerate(wf.actions):
            if not self._running.get(wf.id, False):
                break
            action_type = action_data.get("action_type", "")
            selector = action_data.get("selector", "")
            result.current_action = f"{action_type}: {selector}"
            await asyncio.sleep(0.1)  # Simulate action time
            result.actions_completed += 1
            result.logs.append(
                {
                    "action": action_type,
                    "selector": selector,
                    "status": "simulated",
                    "index": i,
                    "note": "Install playwright for real browser automation: pip install playwright && playwright install chromium",
                }
            )
        result.status = "completed_simulated"

    def _interpolate(self, text: str, variables: dict) -> str:
        """Replace {{variable}} placeholders with values."""
        for key, value in variables.items():
            text = text.replace(f"{{{{{key}}}}}", str(value))
        return text

    def stop_execution(self, workflow_id: str) -> bool:
        if workflow_id in self._running:
            self._running[workflow_id] = False
            return True
        return False

    def get_execution(self, run_id: str) -> Optional[dict]:
        ex = self._executions.get(run_id)
        return asdict(ex) if ex else None

    def list_executions(self, workflow_id: str = "") -> list[dict]:
        execs = list(self._executions.values())
        if workflow_id:
            execs = [e for e in execs if e.workflow_id == workflow_id]
        execs.sort(key=lambda e: e.started_at, reverse=True)
        return [asdict(e) for e in execs]

    # ─── Script Generation ───

    def generate_playwright_script(self, workflow_id: str) -> Optional[str]:
        """Generate a standalone Playwright Python script from a workflow."""
        wf = self._workflows.get(workflow_id)
        if not wf:
            return None

        lines = [
            '"""Auto-generated by Gnosis RPA Engine"""',
            "import asyncio",
            "from playwright.async_api import async_playwright",
            "",
            f"# Workflow: {wf.name}",
            f"# {wf.description}",
            "",
            "async def run():",
            "    async with async_playwright() as p:",
            "        browser = await p.chromium.launch(headless=False)",
            "        page = await browser.new_page()",
            "",
        ]

        if wf.start_url:
            lines.append(f'        await page.goto("{wf.start_url}")')
            lines.append("")

        for action in wf.actions:
            at = action.get("action_type", "")
            sel = action.get("selector", "")
            val = action.get("value", "")
            desc = action.get("description", "")

            if desc:
                lines.append(f"        # {desc}")

            wait = action.get("wait_before_ms", 0)
            if wait > 0:
                lines.append(f"        await asyncio.sleep({wait / 1000})")

            if at == "click":
                lines.append(f'        await page.click("{sel}")')
            elif at == "double_click":
                lines.append(f'        await page.dblclick("{sel}")')
            elif at == "type":
                lines.append(f'        await page.fill("{sel}", "{val}")')
            elif at == "press_key":
                lines.append(f'        await page.keyboard.press("{val}")')
            elif at == "navigate":
                lines.append(f'        await page.goto("{val}")')
            elif at == "wait":
                lines.append(
                    f"        await asyncio.sleep({float(val) / 1000 if val else 1})"
                )
            elif at == "wait_for_selector":
                lines.append(f'        await page.wait_for_selector("{sel}")')
            elif at == "screenshot":
                lines.append(
                    f'        await page.screenshot(path="screenshot_{action.get("id", "")}.png")'
                )
            elif at == "select":
                lines.append(f'        await page.select_option("{sel}", "{val}")')
            elif at == "hover":
                lines.append(f'        await page.hover("{sel}")')
            elif at == "scroll":
                lines.append(
                    f'        await page.evaluate("window.scrollBy(0, {action.get("y", 300)})")'
                )
            elif at == "extract_text":
                lines.append(f'        text = await page.text_content("{sel}")')
                lines.append('        print(f"Extracted: {text}")')
            elif at == "assert_text":
                lines.append(
                    f'        assert "{val}" in await page.text_content("{sel}")'
                )
            elif at == "assert_visible":
                lines.append(f'        assert await page.is_visible("{sel}")')

            wait_after = action.get("wait_after_ms", 500)
            if wait_after > 0:
                lines.append(f"        await asyncio.sleep({wait_after / 1000})")
            lines.append("")

        lines.extend(
            [
                "        await browser.close()",
                "",
                "asyncio.run(run())",
            ]
        )
        return "\n".join(lines)

    def get_stats(self) -> dict:
        total_runs = len(self._executions)
        completed = sum(1 for e in self._executions.values() if "completed" in e.status)
        failed = sum(1 for e in self._executions.values() if e.status == "failed")
        return {
            "total_workflows": len(self._workflows),
            "active_recordings": len(self._recordings),
            "total_runs": total_runs,
            "completed_runs": completed,
            "failed_runs": failed,
            "playwright_available": self._playwright_available,
        }


# Singleton
rpa_engine = RPAEngine()
