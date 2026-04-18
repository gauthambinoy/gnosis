"""Gnosis Guardrail Engine — pre-execution safety checks for all agent actions."""

import logging
import re
import time
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class GuardrailEngine:
    """Pre-execution safety checks for all agent actions."""

    BUILTIN_RULES = [
        {"id": "no-mass-email", "check": "email_recipients <= 10", "severity": "block",
         "description": "Block sending emails to more than 10 recipients."},
        {"id": "cost-limit", "check": "estimated_cost <= 1.0", "severity": "warn",
         "description": "Warn when estimated cost exceeds $1.00."},
        {"id": "no-delete", "check": "action != 'delete'", "severity": "approval_required",
         "description": "Require approval for delete operations."},
        {"id": "pii-check", "check": "no_pii_in_output", "severity": "block",
         "description": "Block actions that expose PII in output."},
        {"id": "rate-limit", "check": "actions_per_minute <= 30", "severity": "block",
         "description": "Block agents exceeding 30 actions per minute."},
    ]

    PII_PATTERNS = [
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),           # SSN
        re.compile(r"\b\d{16}\b"),                        # credit card (16 digits)
        re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # credit card formatted
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b"),  # email in output
    ]

    def __init__(self):
        self._rules: list[dict] = list(self.BUILTIN_RULES)
        self._violations_log: list[dict] = []
        self._action_timestamps: dict[str, list[float]] = {}  # agent_id -> timestamps

    async def check(self, agent_id: str, action: dict, context: dict | None = None) -> dict:
        """Run all guardrails against an action.

        Returns {passed: bool, violations: list, warnings: list}
        """
        context = context or {}
        violations: list[dict] = []
        warnings: list[dict] = []

        for rule in self._rules:
            result = self._evaluate_rule(rule, agent_id, action, context)
            if result is None:
                continue  # rule doesn't apply

            if not result["passed"]:
                entry = {
                    "rule_id": rule["id"],
                    "severity": rule["severity"],
                    "description": rule.get("description", rule["check"]),
                    "details": result.get("details", ""),
                }
                if rule["severity"] == "warn":
                    warnings.append(entry)
                else:
                    violations.append(entry)

        # Log violations
        if violations:
            for v in violations:
                self._violations_log.append({
                    **v,
                    "agent_id": agent_id,
                    "action": action.get("type", str(action)),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })

        passed = len([v for v in violations if v["severity"] == "block"]) == 0
        needs_approval = any(v["severity"] == "approval_required" for v in violations)

        return {
            "passed": passed and not needs_approval,
            "violations": violations,
            "warnings": warnings,
            "requires_approval": needs_approval,
        }

    def add_rule(self, rule: dict):
        """Add a custom guardrail rule."""
        if not rule.get("id") or not rule.get("check") or not rule.get("severity"):
            raise ValueError("Rule must have 'id', 'check', and 'severity' fields.")
        # Remove existing rule with same id
        self._rules = [r for r in self._rules if r["id"] != rule["id"]]
        self._rules.append(rule)

    def remove_rule(self, rule_id: str):
        """Remove a guardrail rule by id."""
        self._rules = [r for r in self._rules if r["id"] != rule_id]

    def get_rules(self) -> list[dict]:
        """Return all active rules."""
        return list(self._rules)

    async def get_violations_log(self, agent_id: str | None = None, limit: int = 50) -> list:
        """Get recent violations, optionally filtered by agent."""
        log = self._violations_log
        if agent_id:
            log = [v for v in log if v.get("agent_id") == agent_id]
        return log[-limit:]

    # ------------------------------------------------------------------
    # Rule evaluation
    # ------------------------------------------------------------------

    def _evaluate_rule(self, rule: dict, agent_id: str, action: dict, context: dict) -> dict | None:
        """Evaluate a single rule. Returns None if rule doesn't apply."""
        rule_id = rule["id"]
        check = rule["check"]

        if rule_id == "no-mass-email" or check == "email_recipients <= 10":
            recipients = action.get("email_recipients", action.get("recipients", 0))
            if isinstance(recipients, list):
                recipients = len(recipients)
            if isinstance(recipients, (int, float)) and recipients > 0:
                passed = recipients <= 10
                return {"passed": passed, "details": f"Recipients: {recipients}"}
            return None

        if rule_id == "cost-limit" or check == "estimated_cost <= 1.0":
            cost = action.get("estimated_cost", context.get("estimated_cost"))
            if cost is not None:
                passed = float(cost) <= 1.0
                return {"passed": passed, "details": f"Estimated cost: ${cost:.2f}"}
            return None

        if rule_id == "no-delete" or check == "action != 'delete'":
            action_type = action.get("type", action.get("action", ""))
            if "delete" in str(action_type).lower():
                return {"passed": False, "details": f"Delete action detected: {action_type}"}
            return None

        if rule_id == "pii-check" or check == "no_pii_in_output":
            output = action.get("output", action.get("result", ""))
            if output:
                for pattern in self.PII_PATTERNS:
                    if pattern.search(str(output)):
                        return {"passed": False, "details": "PII detected in output."}
            return None

        if rule_id == "rate-limit" or check == "actions_per_minute <= 30":
            return self._check_rate_limit(agent_id, max_per_minute=30)

        # Custom rule: try generic evaluation
        return self._evaluate_generic(check, action, context)

    def _check_rate_limit(self, agent_id: str, max_per_minute: int = 30) -> dict:
        """Track and check rate limiting per agent."""
        now = time.time()
        if agent_id not in self._action_timestamps:
            self._action_timestamps[agent_id] = []

        timestamps = self._action_timestamps[agent_id]
        # Prune old entries (> 60s)
        cutoff = now - 60
        timestamps[:] = [t for t in timestamps if t > cutoff]
        timestamps.append(now)

        count = len(timestamps)
        passed = count <= max_per_minute
        return {"passed": passed, "details": f"Actions in last minute: {count}/{max_per_minute}"}

    @staticmethod
    def _evaluate_generic(check_expr: str, action: dict, context: dict) -> dict | None:
        """Best-effort evaluation of simple check expressions."""
        merged = {**context, **action}
        try:
            # Support simple comparisons like "field <= value"
            match = re.match(r"(\w+)\s*(<=|>=|<|>|==|!=)\s*(.+)", check_expr)
            if match:
                field, op, val_str = match.groups()
                if field not in merged:
                    return None
                field_val = merged[field]
                try:
                    compare_val = type(field_val)(val_str.strip().strip("'\""))
                except (ValueError, TypeError):
                    return None

                ops = {"<=": lambda a, b: a <= b, ">=": lambda a, b: a >= b,
                       "<": lambda a, b: a < b, ">": lambda a, b: a > b,
                       "==": lambda a, b: a == b, "!=": lambda a, b: a != b}
                passed = ops[op](field_val, compare_val)
                return {"passed": passed, "details": f"{field}={field_val} {op} {val_str.strip()}"}
        except Exception:
            logger.warning("Guardrail check failed", exc_info=True)
        return None


# Global singleton
guardrail_engine = GuardrailEngine()
