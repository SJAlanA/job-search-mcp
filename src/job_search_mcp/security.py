"""
Security helpers shared across tools.

Implements the two best practices for this assignment:

1. Input Sanitization -- validate/normalize every field that crosses the
   MCP tool boundary *before* it reaches the database layer or an outbound
   API call. Combined with parameterized SQL in db.py, this is what blocks
   SQL-injection-style attacks (see exploits/exploit_sql_injection.py).

2. Error Disclosure prevention -- `safe_error()` is the single choke point
   every tool routes exceptions through. It logs the full exception
   (message, type, traceback) to a local file for debugging, but returns
   only a generic, pre-approved message to the MCP client. This stops
   things like OAuth tokens, file paths, or SQL text from ever reaching an
   LLM's context window through a tool's error output
   (see exploits/exploit_error_disclosure.py).
"""

from __future__ import annotations

import logging
import re
import traceback
import uuid
from dataclasses import dataclass

from . import config

config.ensure_dirs()

logging.basicConfig(
    filename=str(config.ERROR_LOG_PATH),
    level=logging.ERROR,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
_logger = logging.getLogger("job_search_mcp")

# Patterns that must never leak into a client-facing message, even in the
# server-side log, as a defense-in-depth measure on top of not returning
# them to the client at all.
_SECRET_PATTERNS = [
    re.compile(r"ya29\.[A-Za-z0-9_\-]+"),  # Google OAuth access tokens
    re.compile(r"1//[A-Za-z0-9_\-]+"),  # Google OAuth refresh tokens
    re.compile(r'"client_secret"\s*:\s*"[^"]+"'),
]


class ValidationError(ValueError):
    """Raised when caller-supplied input fails sanitization."""


def _redact(text: str) -> str:
    for pattern in _SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def sanitize_text(value: str, field_name: str, max_len: int = config.MAX_TEXT_FIELD_LEN) -> str:
    """Normalize and bound-check a free-text field.

    - rejects non-strings and empty-after-strip values
    - strips NUL bytes and other control characters (defends against
      log-injection / terminal-escape tricks riding along in a field)
    - enforces a hard max length so a single tool call can't blow up the
      DB row size or smuggle an oversized payload through the tracker
    """
    if not isinstance(value, str):
        raise ValidationError(f"{field_name} must be a string")
    cleaned = "".join(ch for ch in value if ch >= " " or ch in "\n\t")
    cleaned = cleaned.strip()
    if not cleaned:
        raise ValidationError(f"{field_name} cannot be empty")
    if len(cleaned) > max_len:
        raise ValidationError(f"{field_name} exceeds max length of {max_len} characters")
    return cleaned


def sanitize_status(value: str) -> str:
    if not isinstance(value, str) or value.strip().lower() not in config.ALLOWED_STATUSES:
        raise ValidationError(
            f"status must be one of: {', '.join(sorted(config.ALLOWED_STATUSES))}"
        )
    return value.strip().lower()


def sanitize_query(value: str) -> str:
    return sanitize_text(value, "query", max_len=config.MAX_QUERY_LEN)


@dataclass
class SafeError:
    """What a tool returns to the MCP client on failure -- never the raw exception."""

    ok: bool
    error: str
    error_id: str


def safe_error(exc: Exception, user_message: str) -> SafeError:
    """Log the real exception server-side; return only a generic message + a
    correlation id the user can mention when asking for help, so debugging
    is still possible without ever putting stack traces, file paths, SQL,
    or tokens into the LLM's context window.
    """
    error_id = uuid.uuid4().hex[:8]
    full_detail = _redact(f"{type(exc).__name__}: {exc}\n{traceback.format_exc()}")
    _logger.error("error_id=%s %s", error_id, full_detail)
    return SafeError(ok=False, error=f"{user_message} (ref: {error_id})", error_id=error_id)
