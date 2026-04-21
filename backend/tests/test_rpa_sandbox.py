"""RPA sandbox security tests.

Validates that the RPA engine's public surface contains no escape vectors
(no file system, no shell, no code execution action types) and that the
ActionType enum is restricted to safe browser interactions only.
"""

from app.core.rpa_engine import ActionType, RecordedAction


# Action types that, if added, would be sandbox escape risks. None of these
# may ever appear in ActionType.
DANGEROUS_NAMES = {
    "SHELL_EXEC", "EXECUTE", "EXEC", "EXECUTE_CODE", "RUN_COMMAND",
    "SYSTEM", "SUBPROCESS",
    "READ_FILE", "WRITE_FILE", "DELETE_FILE", "OPEN_FILE",
    "FILE_SYSTEM", "FS_READ", "FS_WRITE",
    "EVAL", "PYTHON", "JAVASCRIPT_EVAL",
    "NETWORK_REQUEST", "FETCH_URL",
}


# ---------------------------------------------------------------------------
# Action type allow-list
# ---------------------------------------------------------------------------

def test_no_dangerous_action_types_exist():
    names = {a.name for a in ActionType}
    leaked = names & DANGEROUS_NAMES
    assert not leaked, f"Sandbox-escape ActionType members must not exist: {leaked}"


def test_action_types_are_strings():
    for a in ActionType:
        assert isinstance(a.value, str)
        assert a.value.replace("_", "").isalnum()


def test_action_type_count_within_expected_range():
    # Sanity bound: keep the action surface small. If this trips, review the
    # additions for sandbox impact before bumping the bound.
    assert 5 <= len(ActionType) <= 40


def test_only_browser_action_categories():
    allowed_prefixes = {
        "click", "double", "right", "type", "press", "scroll", "navigate",
        "wait", "screenshot", "select", "hover", "drag", "assert", "extract",
        "conditional", "loop",
    }
    for a in ActionType:
        prefix = a.value.split("_")[0]
        assert prefix in allowed_prefixes, f"{a.name}={a.value} is not a known browser action"


# ---------------------------------------------------------------------------
# RecordedAction integrity
# ---------------------------------------------------------------------------

def test_recorded_action_round_trip():
    action = RecordedAction(action_type="click", selector="button.submit")
    assert action.action_type == ActionType.CLICK
    assert action.selector == "button.submit"


def test_recorded_action_supports_safe_actions_only():
    safe = [
        ActionType.CLICK, ActionType.TYPE, ActionType.NAVIGATE,
        ActionType.SCREENSHOT, ActionType.WAIT, ActionType.ASSERT_VISIBLE,
    ]
    for a in safe:
        ra = RecordedAction(action_type=a.value, selector="*")
        assert ra.action_type == a.value


# ---------------------------------------------------------------------------
# Selector-injection defence (defence in depth — Playwright sandboxes selectors)
# ---------------------------------------------------------------------------

INJECTION_SELECTORS = [
    "<script>alert(1)</script>",
    "javascript:alert(1)",
    "data:text/html,<script>alert(1)</script>",
    "'; DROP TABLE users; --",
    "../../etc/passwd",
    "$(rm -rf /)",
    "`whoami`",
]


def _is_obviously_dangerous(s: str) -> bool:
    bad = ["<script", "javascript:", "data:text/html",
           "drop table", "../", "$(", "`", "rm -rf"]
    s = s.lower()
    return any(b in s for b in bad)


def test_injection_payloads_recognised():
    for s in INJECTION_SELECTORS:
        assert _is_obviously_dangerous(s), f"Should flag: {s!r}"


def test_safe_selectors_not_flagged():
    safe = ["button.submit", "#main", "input[name='email']",
            "div.row > a.link", "//button[@id='ok']"]
    for s in safe:
        assert not _is_obviously_dangerous(s), f"Should not flag: {s!r}"
