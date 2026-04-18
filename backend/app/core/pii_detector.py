"""Gnosis PII Detector — Auto-detect and redact PII in agent I/O."""
import re
import logging
from dataclasses import dataclass, field
from typing import List
from datetime import datetime, timezone

logger = logging.getLogger("gnosis.pii")

# PII patterns (regex-based for zero-dependency detection)
PII_PATTERNS = {
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "phone_us": re.compile(r'\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'),
    "ssn": re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
    "credit_card": re.compile(r'\b(?:\d{4}[-\s]?){3}\d{4}\b'),
    "ip_address": re.compile(r'\b(?:\d{1,3}\.){3}\d{1,3}\b'),
    "date_of_birth": re.compile(r'\b(?:DOB|date of birth|born)[:\s]+\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}\b', re.IGNORECASE),
    "passport": re.compile(r'\b[A-Z]{1,2}\d{6,9}\b'),
    "iban": re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{4}\d{7}([A-Z0-9]?){0,16}\b'),
    "api_key": re.compile(r'\b(?:sk|pk|api[_-]?key)[_-][A-Za-z0-9]{20,}\b', re.IGNORECASE),
    "jwt": re.compile(r'\beyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'),
}

REDACTION_MAP = {
    "email": "[EMAIL_REDACTED]",
    "phone_us": "[PHONE_REDACTED]",
    "ssn": "[SSN_REDACTED]",
    "credit_card": "[CC_REDACTED]",
    "ip_address": "[IP_REDACTED]",
    "date_of_birth": "[DOB_REDACTED]",
    "passport": "[PASSPORT_REDACTED]",
    "iban": "[IBAN_REDACTED]",
    "api_key": "[API_KEY_REDACTED]",
    "jwt": "[TOKEN_REDACTED]",
}

@dataclass
class PIIDetection:
    pii_type: str
    value: str
    start: int
    end: int
    confidence: float = 0.9

@dataclass 
class PIIScanResult:
    text: str
    redacted_text: str
    detections: List[PIIDetection] = field(default_factory=list)
    pii_found: bool = False
    scan_time_ms: float = 0
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class PIIDetector:
    def __init__(self, enabled_types: set = None):
        self.enabled_types = enabled_types or set(PII_PATTERNS.keys())
        self._scan_count = 0
        self._detection_count = 0

    def scan(self, text: str) -> PIIScanResult:
        """Scan text for PII and return detections."""
        import time
        start = time.time()
        detections = []
        
        for pii_type, pattern in PII_PATTERNS.items():
            if pii_type not in self.enabled_types:
                continue
            for match in pattern.finditer(text):
                detections.append(PIIDetection(
                    pii_type=pii_type,
                    value=match.group(),
                    start=match.start(),
                    end=match.end(),
                ))
        
        # Sort by position (reverse) for redaction
        detections.sort(key=lambda d: d.start, reverse=True)
        
        # Redact
        redacted = text
        for det in detections:
            replacement = REDACTION_MAP.get(det.pii_type, "[REDACTED]")
            redacted = redacted[:det.start] + replacement + redacted[det.end:]
        
        scan_ms = (time.time() - start) * 1000
        self._scan_count += 1
        self._detection_count += len(detections)
        
        if detections:
            logger.warning(f"PII detected: {len(detections)} items ({', '.join(set(d.pii_type for d in detections))})")
        
        return PIIScanResult(
            text=text,
            redacted_text=redacted,
            detections=detections,
            pii_found=len(detections) > 0,
            scan_time_ms=scan_ms,
        )

    def redact(self, text: str) -> str:
        """Quick redact — returns redacted text only."""
        return self.scan(text).redacted_text

    @property
    def stats(self) -> dict:
        return {
            "total_scans": self._scan_count,
            "total_detections": self._detection_count,
            "enabled_types": list(self.enabled_types),
        }

pii_detector = PIIDetector()
