"""Gnosis Trust Engine — auto-evolving trust levels."""

TRUST_LEVELS = {
    0: {"name": "Observer", "description": "Watches and suggests, never acts", "auto_approve": False},
    1: {"name": "Apprentice", "description": "Handles routine, asks for complex", "auto_approve": False},
    2: {"name": "Associate", "description": "80% autonomous, escalates edge cases", "auto_approve": True},
    3: {"name": "Autonomous", "description": "Full autonomy within guardrails", "auto_approve": True},
}

PROMOTION_THRESHOLDS = {
    1: {"min_correct": 50, "max_error_rate": 0.05},
    2: {"min_correct": 200, "max_error_rate": 0.03},
    3: {"min_correct": 500, "max_error_rate": 0.02},
}


class TrustEngine:
    async def evaluate_trust(self, agent_id: str) -> int:
        return 0

    async def should_require_approval(self, agent_id: str, action_type: str, confidence: float) -> bool:
        return True
