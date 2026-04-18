"""Gnosis Drift Detector — Detect when agent behavior drifts from baseline."""
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from collections import defaultdict

logger = logging.getLogger("gnosis.drift_detector")


@dataclass
class DriftReport:
    agent_id: str = ""
    metric: str = ""
    baseline: float = 0.0
    current: float = 0.0
    drift_pct: float = 0.0
    severity: str = "low"  # low/medium/high/critical
    detected_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class DriftDetectorEngine:
    SEVERITY_THRESHOLDS = {"low": 0.1, "medium": 0.25, "high": 0.5, "critical": 0.75}
    BASELINE_WINDOW = 20  # number of initial samples to establish baseline

    def __init__(self):
        self._metrics: Dict[str, Dict[str, List[float]]] = defaultdict(lambda: defaultdict(list))

    def record_metric(self, agent_id: str, metric: str, value: float) -> dict:
        self._metrics[agent_id][metric].append(value)
        logger.info(f"Recorded metric {metric}={value} for agent {agent_id}")
        return {"agent_id": agent_id, "metric": metric, "value": value,
                "total_samples": len(self._metrics[agent_id][metric])}

    def _get_baseline(self, values: List[float]) -> float:
        baseline_values = values[:self.BASELINE_WINDOW]
        return sum(baseline_values) / len(baseline_values) if baseline_values else 0.0

    def _get_current(self, values: List[float], window: int = 5) -> float:
        recent = values[-window:]
        return sum(recent) / len(recent) if recent else 0.0

    def _classify_severity(self, drift_pct: float) -> str:
        abs_drift = abs(drift_pct)
        if abs_drift >= self.SEVERITY_THRESHOLDS["critical"]:
            return "critical"
        elif abs_drift >= self.SEVERITY_THRESHOLDS["high"]:
            return "high"
        elif abs_drift >= self.SEVERITY_THRESHOLDS["medium"]:
            return "medium"
        return "low"

    def check_drift(self, agent_id: str) -> List[dict]:
        if agent_id not in self._metrics:
            return []
        reports = []
        for metric, values in self._metrics[agent_id].items():
            if len(values) < self.BASELINE_WINDOW + 1:
                continue
            baseline = self._get_baseline(values)
            current = self._get_current(values)
            if baseline == 0:
                drift_pct = 0.0
            else:
                drift_pct = round((current - baseline) / abs(baseline), 4)
            severity = self._classify_severity(drift_pct)
            if abs(drift_pct) >= self.SEVERITY_THRESHOLDS["low"]:
                report = DriftReport(
                    agent_id=agent_id, metric=metric,
                    baseline=round(baseline, 4), current=round(current, 4),
                    drift_pct=drift_pct, severity=severity,
                )
                reports.append(asdict(report))
        return reports

    def get_metrics_summary(self, agent_id: str) -> dict:
        if agent_id not in self._metrics:
            return {"agent_id": agent_id, "metrics": {}}
        summary = {}
        for metric, values in self._metrics[agent_id].items():
            summary[metric] = {
                "count": len(values),
                "baseline": round(self._get_baseline(values), 4) if len(values) >= self.BASELINE_WINDOW else None,
                "current": round(self._get_current(values), 4),
            }
        return {"agent_id": agent_id, "metrics": summary}


drift_detector_engine = DriftDetectorEngine()
