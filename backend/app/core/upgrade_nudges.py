"""Smart upgrade nudges based on usage patterns."""
import uuid, logging
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Set

logger = logging.getLogger("gnosis.nudges")

@dataclass
class Nudge:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    type: str = ""
    title: str = ""
    message: str = ""
    action_url: str = ""
    priority: int = 0
    dismissed: bool = False

class NudgeEngine:
    def __init__(self):
        self._dismissed: Dict[str, Set[str]] = {}

    def evaluate_nudges(self, user_id: str) -> List[dict]:
        nudges = [
            Nudge(id="nudge-quota", type="quota_warning", title="Approaching Execution Limit", message="You've used 80% of your monthly executions", action_url="/billing", priority=3),
            Nudge(id="nudge-feature", type="feature_unlock", title="Try Agent Pipelines", message="Chain agents together for complex workflows", action_url="/pipelines", priority=2),
            Nudge(id="nudge-memory", type="feature_unlock", title="Enable Memory", message="Your agents can learn from past interactions", action_url="/settings", priority=1),
            Nudge(id="nudge-security", type="feature_unlock", title="Enable PII Detection", message="Protect sensitive data automatically", action_url="/security", priority=2),
        ]
        dismissed = self._dismissed.get(user_id, set())
        return [asdict(n) for n in nudges if n.id not in dismissed]

    def dismiss_nudge(self, user_id: str, nudge_id: str):
        if user_id not in self._dismissed:
            self._dismissed[user_id] = set()
        self._dismissed[user_id].add(nudge_id)

nudge_engine = NudgeEngine()
