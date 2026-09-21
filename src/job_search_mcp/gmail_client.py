"""
Read-only Gmail access.

Scoped to gmail.readonly (see config.GOOGLE_SCOPES) -- this module has no
way to send, delete, or modify mail even if a bug let a caller control the
request, because the OAuth token itself doesn't carry that permission.
That's a least-privilege design choice, not just an input-validation one.

Reference:
- google-api-python-client usage pattern adapted from Google's official
  Gmail API quickstart: https://developers.google.com/gmail/api/quickstart/python
  (Copyright Google LLC, Apache License 2.0)
"""

from __future__ import annotations

from googleapiclient.discovery import build

from .auth import get_credentials


def _extract_snippet_fields(msg: dict) -> dict:
    headers = {h["name"].lower(): h["value"] for h in msg.get("payload", {}).get("headers", [])}
    return {
        "id": msg.get("id"),
        "subject": headers.get("subject", "(no subject)"),
        "from": headers.get("from", "(unknown sender)"),
        "date": headers.get("date", ""),
        "snippet": msg.get("snippet", ""),
    }


def search_messages(query: str, max_results: int) -> list[dict]:
    """Search Gmail with a user-supplied query string and return lightweight
    metadata (subject/from/date/snippet) for each match -- never the full
    message body, which keeps what flows into the LLM's context minimal.
    """
    creds = get_credentials()
    service = build("gmail", "v1", credentials=creds)

    resp = (
        service.users()
        .messages()
        .list(userId="me", q=query, maxResults=max_results)
        .execute()
    )
    message_stubs = resp.get("messages", [])

    results = []
    for stub in message_stubs:
        full = (
            service.users()
            .messages()
            .get(userId="me", id=stub["id"], format="metadata",
                 metadataHeaders=["Subject", "From", "Date"])
            .execute()
        )
        results.append(_extract_snippet_fields(full))
    return results
