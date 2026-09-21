"""Unit tests for the sanitization/error-disclosure helpers.
Run with: pytest tests/
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

import pytest

from job_search_mcp import security


def test_sanitize_text_strips_and_validates():
    assert security.sanitize_text("  Acme Robotics  ", "company") == "Acme Robotics"


def test_sanitize_text_rejects_empty():
    with pytest.raises(security.ValidationError):
        security.sanitize_text("   ", "company")


def test_sanitize_text_rejects_too_long():
    with pytest.raises(security.ValidationError):
        security.sanitize_text("x" * 1000, "notes", max_len=500)


def test_sanitize_text_strips_control_chars():
    cleaned = security.sanitize_text("Acme\x00Robotics", "company")
    assert "\x00" not in cleaned


def test_sanitize_status_accepts_known_value():
    assert security.sanitize_status("Applied") == "applied"


def test_sanitize_status_rejects_unknown_value():
    with pytest.raises(security.ValidationError):
        security.sanitize_status("ghosted")


def test_safe_error_never_leaks_secret():
    exc = RuntimeError("token ya29.fake-token-value leaked at /some/real/path")
    result = security.safe_error(exc, "Something went wrong.")
    assert "ya29" not in result.error
    assert "/some/real/path" not in result.error
    assert result.error_id in result.error
