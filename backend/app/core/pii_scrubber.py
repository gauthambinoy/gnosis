"""PII scrubber for log sanitization."""
import re

_PATTERNS = [
    (re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'), '[EMAIL]'),
    (re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'), '[PHONE]'),
    (re.compile(r'\b(?:Bearer\s+)?eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b'), '[JWT]'),
    (re.compile(r'\b(?:sk-|pk-)[A-Za-z0-9]{20,}\b'), '[API_KEY]'),
    (re.compile(r'\bpassword["\s:=]+[^\s,}]+', re.IGNORECASE), 'password=[REDACTED]'),
    (re.compile(r'\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b'), '[CARD]'),
    (re.compile(r'\b\d{3}-\d{2}-\d{4}\b'), '[SSN]'),
]


def scrub(text: str) -> str:
    """Remove PII from text."""
    if not isinstance(text, str):
        return text
    for pattern, replacement in _PATTERNS:
        text = pattern.sub(replacement, text)
    return text


def scrub_dict(d: dict) -> dict:
    """Recursively scrub PII from dict values."""
    result = {}
    for k, v in d.items():
        if isinstance(v, str):
            result[k] = scrub(v)
        elif isinstance(v, dict):
            result[k] = scrub_dict(v)
        elif isinstance(v, list):
            result[k] = [scrub(i) if isinstance(i, str) else i for i in v]
        else:
            result[k] = v
    return result
