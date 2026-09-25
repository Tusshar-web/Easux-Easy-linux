"""
Redaction engine to strip sensitive credentials, tokens, private keys, and secrets.
"""

import re
from typing import List, Tuple

REDACTION_PATTERNS: List[Tuple[re.Pattern, str]] = [
    # Multi-line private keys
    (
        re.compile(r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----", re.MULTILINE),
        "[REDACTED_PRIVATE_KEY]"
    ),
    # GitHub Tokens
    (
        re.compile(r"gh[pousr]_[A-Za-z0-9_]{36,255}"),
        "[REDACTED_GITHUB_TOKEN]"
    ),
    # AWS Access Key
    (
        re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
        "[REDACTED_AWS_KEY]"
    ),
    # JWT Tokens
    (
        re.compile(r"\bey[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\b"),
        "[REDACTED_JWT]"
    ),
    # Bearer tokens in headers or strings
    (
        re.compile(r"(?i)\bBearer\s+[A-Za-z0-9._\-]{16,}\b"),
        "Bearer [REDACTED_TOKEN]"
    ),
    # Basic auth embedded in URLs
    (
        re.compile(r"(https?://)([^:\s/@]+):([^@\s/]+)(@)"),
        r"\1\2:[REDACTED]\4"
    ),
    # Generic key-value secret assignments (e.g., API_KEY=xyz, DB_PASSWORD="abc")
    (
        re.compile(
            r"""(?i)\b[a-z0-9_-]*(?:api[_-]?key|secret[_-]?key|access[_-]?token|auth[_-]?token|password|passwd|pwd|private[_-]?key)\s*([:=])\s*(['"]?)([^'"\s&;]{6,})\2""",
        ),
        r"[REDACTED_SECRET]"
    ),
    # Generic Slack token
    (
        re.compile(r"\bxox[baprs]-[0-9a-zA-Z-]{10,}\b"),
        "[REDACTED_SLACK_TOKEN]"
    ),
]


class Redactor:
    """Detects and redacts sensitive data from commands, errors, and previews."""

    @classmethod
    def redact(cls, text: str) -> str:
        if not text:
            return text
        result = text
        for pattern, replacement in REDACTION_PATTERNS:
            result = pattern.sub(replacement, result)
        return result


def redact_secrets(text: str) -> str:
    return Redactor.redact(text)
