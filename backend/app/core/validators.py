"""Input validation utilities for the Gnosis platform."""

import re

# Pre-compiled patterns
_EMAIL_RE = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")
_AGENT_NAME_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9 _.-]{0,98}[a-zA-Z0-9]$")
_API_KEY_PATTERNS = [
    re.compile(r"^sk-[a-zA-Z0-9_-]{20,}$"),           # OpenAI style
    re.compile(r"^sk-proj-[a-zA-Z0-9_-]{20,}$"),      # OpenAI project keys
    re.compile(r"^sk-ant-[a-zA-Z0-9_-]{20,}$"),       # Anthropic style
    re.compile(r"^anthropic-[a-zA-Z0-9_-]{20,}$"),    # Anthropic alt
    re.compile(r"^gsk_[a-zA-Z0-9_-]{20,}$"),          # Groq
    re.compile(r"^xai-[a-zA-Z0-9_-]{20,}$"),          # xAI
]

# Dangerous patterns to strip from user input
_DANGEROUS_PATTERNS = [
    (re.compile(r"<script\b[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL), ""),
    (re.compile(r"<[^>]+>"), ""),                       # HTML tags
    (re.compile(r"javascript\s*:", re.IGNORECASE), ""),
    (re.compile(r"on\w+\s*=\s*[\"'][^\"']*[\"']", re.IGNORECASE), ""),
    (re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f]"), ""),  # Control chars (keep \n, \r, \t)
]


def sanitize_input(text: str, max_length: int = 10000) -> str:
    """Strip dangerous patterns and enforce length limits.

    Args:
        text: Raw user input.
        max_length: Maximum allowed length after sanitization.

    Returns:
        Sanitized string, truncated to max_length.
    """
    if not isinstance(text, str):
        return ""

    # Truncate first to avoid processing huge payloads
    text = text[:max_length * 2]

    for pattern, replacement in _DANGEROUS_PATTERNS:
        text = pattern.sub(replacement, text)

    # Normalize whitespace runs but preserve newlines
    text = re.sub(r"[^\S\n]+", " ", text)
    text = text.strip()

    return text[:max_length]


def validate_email(email: str) -> bool:
    """Validate an email address format.

    Args:
        email: The email string to validate.

    Returns:
        True if the email is valid, False otherwise.
    """
    if not isinstance(email, str):
        return False
    if len(email) > 254:
        return False
    return bool(_EMAIL_RE.match(email))


def validate_agent_name(name: str) -> bool:
    """Validate an agent name.

    Rules:
        - 1-100 characters
        - Alphanumeric, spaces, dots, hyphens, underscores allowed
        - Must start and end with alphanumeric
        - No special injection characters

    Args:
        name: The agent name to validate.

    Returns:
        True if the name is valid, False otherwise.
    """
    if not isinstance(name, str):
        return False
    if len(name) == 1:
        return bool(re.match(r"^[a-zA-Z0-9]$", name))
    return bool(_AGENT_NAME_RE.match(name))


def validate_api_key(key: str) -> bool:
    """Validate that an API key matches known provider patterns.

    Supported patterns:
        - OpenAI: sk-*, sk-proj-*
        - Anthropic: sk-ant-*, anthropic-*
        - Groq: gsk_*
        - xAI: xai-*

    Args:
        key: The API key to validate.

    Returns:
        True if the key matches a known pattern, False otherwise.
    """
    if not isinstance(key, str):
        return False
    return any(p.match(key) for p in _API_KEY_PATTERNS)
