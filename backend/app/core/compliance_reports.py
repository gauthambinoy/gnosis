"""Compliance Report Generator — generate GDPR, SOC2, HIPAA compliance reports."""
from dataclasses import dataclass, field, asdict
from typing import Dict, List
from datetime import datetime, timezone
import uuid


REPORT_TYPES = {"gdpr", "soc2", "hipaa"}

CHECKS = {
    "gdpr": [
        ("Data inventory maintained", True),
        ("Consent management active", True),
        ("Right to erasure implemented", True),
        ("Data breach notification process", False),
        ("DPA with all processors", True),
    ],
    "soc2": [
        ("Access controls implemented", True),
        ("Audit logging enabled", True),
        ("Encryption at rest", True),
        ("Incident response plan", False),
        ("Vendor management", True),
    ],
    "hipaa": [
        ("PHI access controls", True),
        ("Audit trail for PHI", True),
        ("Encryption in transit", True),
        ("BAA with associates", False),
        ("Risk assessment completed", True),
    ],
}


@dataclass
class ComplianceReport:
    id: str
    type: str  # gdpr / soc2 / hipaa
    workspace_id: str
    generated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sections: List[dict] = field(default_factory=list)
    score: int = 0
    issues: List[str] = field(default_factory=list)


class ComplianceReportEngine:
    def __init__(self):
        self._reports: Dict[str, ComplianceReport] = {}

    def generate_report(self, workspace_id: str, report_type: str) -> ComplianceReport:
        if report_type not in REPORT_TYPES:
            raise ValueError(f"Invalid report type: {report_type}. Must be one of {REPORT_TYPES}")
        checks = CHECKS.get(report_type, [])
        sections = []
        issues = []
        passed = 0
        for check_name, check_pass in checks:
            sections.append({"check": check_name, "passed": check_pass})
            if check_pass:
                passed += 1
            else:
                issues.append(f"FAIL: {check_name}")
        score = int((passed / len(checks)) * 100) if checks else 0
        report = ComplianceReport(
            id=str(uuid.uuid4()),
            type=report_type,
            workspace_id=workspace_id,
            sections=sections,
            score=score,
            issues=issues,
        )
        self._reports[report.id] = report
        return report

    def get_report(self, report_id: str) -> ComplianceReport:
        report = self._reports.get(report_id)
        if not report:
            raise KeyError(f"Report {report_id} not found")
        return report

    def list_reports(self, workspace_id: str = "") -> List[dict]:
        reports = self._reports.values()
        if workspace_id:
            reports = [r for r in reports if r.workspace_id == workspace_id]
        return [asdict(r) for r in reports]


compliance_engine = ComplianceReportEngine()
