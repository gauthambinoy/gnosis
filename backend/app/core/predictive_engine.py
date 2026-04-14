"""
Predictive Agent Spawning Engine
Predicts what agents users will need BEFORE they ask, based on behavioural patterns.
"""

from __future__ import annotations

import uuid
import asyncio
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

class DayOfWeek(str, Enum):
    MON = "monday"
    TUE = "tuesday"
    WED = "wednesday"
    THU = "thursday"
    FRI = "friday"
    SAT = "saturday"
    SUN = "sunday"


@dataclass
class UserPattern:
    """A detected behavioural pattern for a user."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    time_of_day: str = ""          # e.g. "09:00"
    day_of_week: list[str] = field(default_factory=list)
    action_sequence: list[str] = field(default_factory=list)
    frequency: int = 0             # how many times observed
    last_seen: str = ""
    confidence: float = 0.0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class Prediction:
    """A predicted agent suggestion."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    suggested_agent: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    pattern_source: str = ""       # id of the source UserPattern
    status: str = "pending"        # pending | accepted | dismissed
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


@dataclass
class ActionEvent:
    """A single tracked user action."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    action: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# Pre-built prediction templates
# ---------------------------------------------------------------------------

PREDICTION_TEMPLATES: list[dict[str, Any]] = [
    {
        "name": "morning_routine",
        "description": "Morning routine — email → calendar → standup report",
        "time_of_day": "09:00",
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "sequence": ["check_email", "review_calendar", "generate_standup"],
        "agent": "Morning Briefing Agent",
        "default_confidence": 0.85,
    },
    {
        "name": "weekly_report",
        "description": "Weekly report generation every Friday afternoon",
        "time_of_day": "16:00",
        "days": ["friday"],
        "sequence": ["gather_metrics", "compile_report", "send_summary"],
        "agent": "Weekly Report Agent",
        "default_confidence": 0.90,
    },
    {
        "name": "end_of_day_summary",
        "description": "End-of-day summary of tasks completed",
        "time_of_day": "17:30",
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "sequence": ["review_tasks", "summarise_progress", "plan_tomorrow"],
        "agent": "EOD Summary Agent",
        "default_confidence": 0.80,
    },
    {
        "name": "competitor_monitoring",
        "description": "Monitor competitor news and pricing changes",
        "time_of_day": "10:00",
        "days": ["monday", "wednesday", "friday"],
        "sequence": ["scan_news", "check_pricing", "alert_changes"],
        "agent": "Competitor Watch Agent",
        "default_confidence": 0.75,
    },
    {
        "name": "social_media_posting",
        "description": "Scheduled social media content posting",
        "time_of_day": "11:00",
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "sequence": ["draft_post", "review_content", "schedule_publish"],
        "agent": "Social Media Agent",
        "default_confidence": 0.82,
    },
    {
        "name": "customer_followup",
        "description": "Follow-up reminders for open customer tickets",
        "time_of_day": "14:00",
        "days": ["tuesday", "thursday"],
        "sequence": ["scan_tickets", "draft_followups", "send_reminders"],
        "agent": "Customer Follow-Up Agent",
        "default_confidence": 0.78,
    },
    {
        "name": "data_cleanup",
        "description": "Periodic data hygiene and deduplication",
        "time_of_day": "02:00",
        "days": ["sunday"],
        "sequence": ["scan_duplicates", "merge_records", "archive_stale"],
        "agent": "Data Cleanup Agent",
        "default_confidence": 0.88,
    },
    {
        "name": "performance_review_prep",
        "description": "Prepare materials before quarterly performance reviews",
        "time_of_day": "09:00",
        "days": ["monday"],
        "sequence": ["gather_achievements", "compile_metrics", "draft_review"],
        "agent": "Performance Review Agent",
        "default_confidence": 0.70,
    },
    {
        "name": "invoice_processing",
        "description": "Process incoming invoices and flag anomalies",
        "time_of_day": "08:00",
        "days": ["monday", "wednesday", "friday"],
        "sequence": ["scan_inbox", "extract_data", "validate_amounts", "flag_issues"],
        "agent": "Invoice Processing Agent",
        "default_confidence": 0.86,
    },
    {
        "name": "lead_qualification",
        "description": "Score and qualify new inbound leads",
        "time_of_day": "10:30",
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "sequence": ["fetch_leads", "score_leads", "route_qualified"],
        "agent": "Lead Qualification Agent",
        "default_confidence": 0.83,
    },
    {
        "name": "security_scan",
        "description": "Nightly security vulnerability scan",
        "time_of_day": "03:00",
        "days": ["monday", "wednesday", "friday"],
        "sequence": ["scan_repos", "check_deps", "generate_report"],
        "agent": "Security Scan Agent",
        "default_confidence": 0.91,
    },
    {
        "name": "meeting_prep",
        "description": "Prepare briefs before upcoming meetings",
        "time_of_day": "08:30",
        "days": ["monday", "tuesday", "wednesday", "thursday", "friday"],
        "sequence": ["check_calendar", "gather_context", "create_brief"],
        "agent": "Meeting Prep Agent",
        "default_confidence": 0.77,
    },
]


# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------

class PredictiveEngine:
    """Analyses user behaviour patterns to predict future agent needs."""

    def __init__(self) -> None:
        self._actions: dict[str, list[ActionEvent]] = {}   # user_id -> events
        self._patterns: dict[str, list[UserPattern]] = {}  # user_id -> patterns
        self._predictions: dict[str, Prediction] = {}      # prediction_id -> Prediction
        self._dismissed: set[str] = set()
        self._accepted: set[str] = set()
        self._templates = PREDICTION_TEMPLATES
        self._lock = asyncio.Lock()

    # -- tracking ----------------------------------------------------------

    async def track_action(self, user_id: str, action: str, metadata: dict[str, Any] | None = None) -> ActionEvent:
        async with self._lock:
            event = ActionEvent(user_id=user_id, action=action, metadata=metadata or {})
            self._actions.setdefault(user_id, []).append(event)
            # Re-analyse patterns after every 5 actions
            if len(self._actions[user_id]) % 5 == 0:
                await self._detect_patterns(user_id)
            return event

    # -- pattern detection -------------------------------------------------

    async def _detect_patterns(self, user_id: str) -> None:
        events = self._actions.get(user_id, [])
        if len(events) < 3:
            return

        action_counts: dict[str, int] = {}
        for ev in events:
            action_counts[ev.action] = action_counts.get(ev.action, 0) + 1

        # Simple sequence detection: sliding window of 3
        sequences: dict[tuple[str, ...], int] = {}
        for i in range(len(events) - 2):
            seq = (events[i].action, events[i + 1].action, events[i + 2].action)
            sequences[seq] = sequences.get(seq, 0) + 1

        patterns: list[UserPattern] = []
        for seq, freq in sequences.items():
            if freq >= 2:
                now = datetime.now(timezone.utc)
                patterns.append(UserPattern(
                    user_id=user_id,
                    action_sequence=list(seq),
                    frequency=freq,
                    confidence=min(0.5 + freq * 0.1, 0.99),
                    last_seen=now.isoformat(),
                    time_of_day=now.strftime("%H:%M"),
                    day_of_week=[now.strftime("%A").lower()],
                ))
        self._patterns[user_id] = patterns

    async def analyze_patterns(self, user_id: str) -> list[dict[str, Any]]:
        await self._detect_patterns(user_id)
        return [
            {
                "id": p.id,
                "action_sequence": p.action_sequence,
                "frequency": p.frequency,
                "confidence": p.confidence,
                "time_of_day": p.time_of_day,
                "day_of_week": p.day_of_week,
                "last_seen": p.last_seen,
            }
            for p in self._patterns.get(user_id, [])
        ]

    # -- prediction --------------------------------------------------------

    async def predict_next_action(self, user_id: str) -> str | None:
        events = self._actions.get(user_id, [])
        if len(events) < 2:
            return None
        last_two = (events[-2].action, events[-1].action)
        # Look for a pattern whose first two actions match
        for p in self._patterns.get(user_id, []):
            seq = p.action_sequence
            if len(seq) >= 3 and (seq[0], seq[1]) == last_two:
                return seq[2]
        return None

    async def suggest_agents(self, user_id: str) -> list[dict[str, Any]]:
        now = datetime.now(timezone.utc)
        current_hour = now.strftime("%H:%M")
        current_day = now.strftime("%A").lower()

        suggestions: list[dict[str, Any]] = []

        # Template-based suggestions
        for tpl in self._templates:
            if current_day in tpl["days"]:
                pred = Prediction(
                    user_id=user_id,
                    suggested_agent=tpl["agent"],
                    confidence=tpl["default_confidence"],
                    reasoning=tpl["description"],
                    pattern_source=f"template:{tpl['name']}",
                )
                self._predictions[pred.id] = pred
                suggestions.append(self._prediction_to_dict(pred))

        # Pattern-based suggestions
        next_action = await self.predict_next_action(user_id)
        if next_action:
            pred = Prediction(
                user_id=user_id,
                suggested_agent=f"Auto-Agent: {next_action}",
                confidence=0.72,
                reasoning=f"You usually do '{next_action}' next based on your recent actions",
                pattern_source="learned_sequence",
            )
            self._predictions[pred.id] = pred
            suggestions.append(self._prediction_to_dict(pred))

        return suggestions

    async def pre_warm_agents(self, user_id: str) -> list[str]:
        """Return agent names that should be pre-warmed (high-confidence predictions)."""
        suggestions = await self.suggest_agents(user_id)
        return [s["suggested_agent"] for s in suggestions if s["confidence"] >= 0.80]

    # -- accept / dismiss --------------------------------------------------

    async def accept_prediction(self, prediction_id: str) -> dict[str, Any] | None:
        pred = self._predictions.get(prediction_id)
        if not pred:
            return None
        pred.status = "accepted"
        self._accepted.add(prediction_id)
        return self._prediction_to_dict(pred)

    async def dismiss_prediction(self, prediction_id: str) -> dict[str, Any] | None:
        pred = self._predictions.get(prediction_id)
        if not pred:
            return None
        pred.status = "dismissed"
        self._dismissed.add(prediction_id)
        return self._prediction_to_dict(pred)

    # -- stats -------------------------------------------------------------

    async def get_stats(self, user_id: str) -> dict[str, Any]:
        return {
            "total_actions_tracked": len(self._actions.get(user_id, [])),
            "patterns_detected": len(self._patterns.get(user_id, [])),
            "total_predictions": len(self._predictions),
            "accepted": len(self._accepted),
            "dismissed": len(self._dismissed),
            "templates_available": len(self._templates),
            "accuracy_estimate": round(
                len(self._accepted) / max(len(self._accepted) + len(self._dismissed), 1), 2
            ),
        }

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _prediction_to_dict(p: Prediction) -> dict[str, Any]:
        return {
            "id": p.id,
            "suggested_agent": p.suggested_agent,
            "confidence": p.confidence,
            "reasoning": p.reasoning,
            "pattern_source": p.pattern_source,
            "status": p.status,
            "created_at": p.created_at,
        }


# Module-level singleton
predictive_engine = PredictiveEngine()
