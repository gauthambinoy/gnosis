"""
LLM Output Validator — Sanitize and validate responses from LLM providers.

This module ensures that LLM-generated content is safe before being used in:
- Tool invocations (code execution, API calls)
- Subsequent prompts (multi-turn conversations)
- Storage (execution logs, memory)
- Client responses (preventing data exfiltration)

Defends against:
1. Prompt injection via tool parameters
2. Code injection in generated code snippets
3. Data exfiltration via indirect attacks
4. XSS via stored LLM output
"""

from __future__ import annotations

import json
import re
from typing import Any
from enum import Enum

from app.core.logger import get_logger
from app.core.error_handling import ValidationError

logger = get_logger("llm.validator")


class ContentType(str, Enum):
    """Types of content that LLM output can be used for."""

    TOOL_PARAMETER = "tool_parameter"
    CODE_EXECUTION = "code_execution"
    SQL_QUERY = "sql_query"
    SYSTEM_COMMAND = "system_command"
    PROMPT_INJECTION = "prompt_injection"
    JSON_OUTPUT = "json_output"
    HTML_RENDERING = "html_rendering"
    FREE_TEXT = "free_text"


class LLMOutputValidator:
    """Validates LLM output for safety before use."""

    # Dangerous patterns that should not appear in LLM output
    DANGEROUS_PATTERNS = {
        # Shell injection
        "shell": [
            r"rm\s+-rf\s+/",
            r"mkfs\.",
            r"dd\s+if=/dev/zero",
            r"chmod\s+-R\s+777",
            r"find\s+.*\s+-exec",
        ],
        # SQL injection
        "sql": [
            r"DROP\s+DATABASE",
            r"DELETE\s+FROM\s+\w+\s+WHERE\s+1=1",
            r"TRUNCATE",
            r"EXEC\s+sp_",
        ],
        # Code injection
        "code": [
            r"__import__\(",
            r"eval\(",
            r"exec\(",
            r"subprocess\.",
            r"os\.system",
        ],
        # Prompt injection markers
        "injection": [
            r"SYSTEM:\s*ignore",
            r"forget\s+your\s+instructions",
            r"follow\s+these\s+instructions\s+instead",
            r"<instructions>",
            r"\[SYSTEM\]",
        ],
    }

    # Maximum reasonable lengths for different output types
    MAX_LENGTHS = {
        ContentType.TOOL_PARAMETER: 2000,
        ContentType.CODE_EXECUTION: 50000,
        ContentType.SQL_QUERY: 10000,
        ContentType.SYSTEM_COMMAND: 5000,
        ContentType.JSON_OUTPUT: 100000,
        ContentType.HTML_RENDERING: 50000,
        ContentType.FREE_TEXT: 100000,
    }

    # Patterns that indicate untrusted formatting
    SUSPICIOUS_MARKERS = [
        "```",  # Code blocks (could contain injection)
        "<?php",  # PHP tags
        "<%",  # ASP tags
        "${",  # Template injection
        "{{",  # Template injection
        "<!--",  # HTML comments (could hide instructions)
    ]

    @classmethod
    def validate(
        cls,
        content: str | None,
        content_type: ContentType = ContentType.FREE_TEXT,
        *,
        allow_multiline: bool = True,
        max_length: int | None = None,
    ) -> str:
        """
        Validate LLM output for safety.

        Args:
            content: LLM-generated text
            content_type: How the content will be used
            allow_multiline: Whether multiline content is acceptable
            max_length: Override default max length for this type

        Returns:
            Validated (and optionally sanitized) content

        Raises:
            ValidationError: If content fails validation

        Examples:
            >>> validate_tool_param = LLMOutputValidator.validate(
            ...     '{"user_id": 123}',
            ...     ContentType.TOOL_PARAMETER
            ... )
            >>> validate_sql = LLMOutputValidator.validate(
            ...     'SELECT * FROM users WHERE id = ?',
            ...     ContentType.SQL_QUERY
            ... )
        """
        if content is None:
            raise ValidationError("LLM output is None")

        if not isinstance(content, str):
            content = str(content)

        content = content.strip()

        if not content:
            raise ValidationError("LLM output is empty")

        # Check length
        max_len = max_length or cls.MAX_LENGTHS.get(content_type, 100000)
        if len(content) > max_len:
            raise ValidationError(
                f"LLM output exceeds max length ({len(content)} > {max_len})",
                detail={"content_type": content_type, "length": len(content)},
            )

        # Check for newlines if not allowed
        if not allow_multiline and "\n" in content:
            raise ValidationError(
                "LLM output contains newlines (not allowed for this type)",
                detail={"content_type": content_type},
            )

        # Scan for dangerous patterns
        cls._check_dangerous_patterns(content, content_type)

        # Type-specific validation
        if content_type == ContentType.JSON_OUTPUT:
            cls._validate_json(content)
        elif content_type == ContentType.SQL_QUERY:
            cls._validate_sql(content)
        elif content_type == ContentType.SYSTEM_COMMAND:
            cls._validate_system_command(content)
        elif content_type == ContentType.HTML_RENDERING:
            cls._validate_html(content)

        return content

    @classmethod
    def validate_tool_parameters(cls, params: dict[str, Any]) -> dict[str, Any]:
        """
        Validate parameters before passing to tool execution.

        Each parameter is validated to prevent injection attacks.

        Args:
            params: Tool parameters from LLM output

        Returns:
            Validated parameters dict

        Raises:
            ValidationError: If any parameter fails validation
        """
        validated: dict[str, Any] = {}

        for key, value in params.items():
            # Validate parameter name
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", key):
                raise ValidationError(
                    f"Invalid parameter name: {key}",
                    detail={"parameter": key},
                )

            # Validate parameter value
            if isinstance(value, str):
                validated[key] = cls.validate(
                    value,
                    ContentType.TOOL_PARAMETER,
                    allow_multiline=False,
                )
            elif isinstance(value, (int, float, bool)):
                validated[key] = value
            elif isinstance(value, list):
                validated[key] = [
                    cls.validate(str(v), ContentType.TOOL_PARAMETER)
                    if isinstance(v, str)
                    else v
                    for v in value
                ]
            elif isinstance(value, dict):
                validated[key] = cls.validate_tool_parameters(value)
            elif value is None:
                validated[key] = None
            else:
                raise ValidationError(
                    f"Invalid parameter type for {key}: {type(value)}",
                    detail={"parameter": key, "type": type(value).__name__},
                )

        return validated

    @classmethod
    def _check_dangerous_patterns(cls, content: str, content_type: ContentType):
        """Check for known dangerous patterns in content."""
        content_lower = content.lower()

        # Pattern checking is always strict for these contexts
        always_strict = {
            ContentType.TOOL_PARAMETER,
            ContentType.CODE_EXECUTION,
            ContentType.SQL_QUERY,
            ContentType.SYSTEM_COMMAND,
            ContentType.JSON_OUTPUT,
            ContentType.PROMPT_INJECTION,
        }

        # Check all dangerous patterns
        for pattern_category, patterns in cls.DANGEROUS_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, content_lower, re.IGNORECASE):
                    # For FREE_TEXT and HTML, only warn on non-injection patterns
                    if content_type not in always_strict:
                        if pattern_category == "injection":
                            # Always reject injection attempts
                            pass
                        else:
                            logger.warning(
                                "Dangerous pattern detected in non-execution context: %s in %s",
                                pattern_category,
                                content_type,
                            )
                            continue

                    logger.warning(
                        "Dangerous pattern detected: %s in %s",
                        pattern_category,
                        content_type,
                        extra={"pattern": pattern, "content_type": content_type},
                    )
                    raise ValidationError(
                        f"LLM output contains dangerous {pattern_category} pattern",
                        detail={
                            "pattern_category": pattern_category,
                            "content_type": content_type,
                        },
                    )

        # Check for suspicious markers
        for marker in cls.SUSPICIOUS_MARKERS:
            if marker in content:
                if content_type != ContentType.CODE_EXECUTION and marker in [
                    "```",
                    "<?php",
                    "<%",
                ]:
                    logger.warning(
                        "Suspicious marker detected: %s in %s output",
                        marker,
                        content_type,
                    )
                    # Don't fail, but log for monitoring

    @classmethod
    def _validate_json(cls, content: str):
        """Validate JSON output."""
        try:
            json.loads(content)
        except json.JSONDecodeError as e:
            raise ValidationError(
                f"LLM output is not valid JSON: {e}",
                detail={"error": str(e)},
            )

    @classmethod
    def _validate_sql(cls, content: str):
        """Validate SQL queries."""
        content_upper = content.upper().strip()

        # Only allow SELECT by default (safest)
        if not content_upper.startswith("SELECT"):
            raise ValidationError(
                "SQL queries must be SELECT statements",
                detail={"first_word": content_upper.split()[0]},
            )

        # Reject known dangerous SQL operations
        dangerous_keywords = [
            "DROP",
            "DELETE",
            "TRUNCATE",
            "EXEC",
            "EXECUTE",
            "INTO OUTFILE",
        ]
        for keyword in dangerous_keywords:
            if keyword in content_upper:
                raise ValidationError(
                    f"SQL query contains dangerous keyword: {keyword}",
                )

    @classmethod
    def _validate_system_command(cls, content: str):
        """Validate system commands."""
        # System commands should never come from LLM output in production
        # They should use the explicit command whitelist from system_control.py
        logger.error("System command validation requested — this should use system_control whitelist")
        raise ValidationError(
            "System commands cannot be generated from LLM output",
            detail={"reason": "Use system_control.py whitelist instead"},
        )

    @classmethod
    def _validate_html(cls, content: str):
        """Validate HTML output."""
        # Check for potentially dangerous HTML
        dangerous_html_patterns = [
            r"<script[^>]*>",
            r"on\w+\s*=",  # Event handlers like onclick
            r"javascript:",
            r"<iframe[^>]*>",
            r"<object[^>]*>",
            r"<embed[^>]*>",
        ]

        for pattern in dangerous_html_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                logger.warning("Dangerous HTML pattern detected: %s", pattern)
                raise ValidationError(
                    "HTML output contains dangerous patterns",
                    detail={"pattern": pattern},
                )


# Public API
def validate_llm_output(
    content: str | None,
    content_type: ContentType = ContentType.FREE_TEXT,
    *,
    allow_multiline: bool = True,
    max_length: int | None = None,
) -> str:
    """
    Public function to validate LLM output.

    See LLMOutputValidator.validate() for details.
    """
    return LLMOutputValidator.validate(
        content,
        content_type,
        allow_multiline=allow_multiline,
        max_length=max_length,
    )


def validate_llm_tool_parameters(params: dict[str, Any]) -> dict[str, Any]:
    """
    Public function to validate LLM-generated tool parameters.

    See LLMOutputValidator.validate_tool_parameters() for details.
    """
    return LLMOutputValidator.validate_tool_parameters(params)
