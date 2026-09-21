"""
Google Calendar event creation, scoped to calendar.events (not full
calendar access) -- this server can create/update events it makes, but
cannot read your existing calendar or delete unrelated events.

Reference:
- google-api-python-client usage pattern adapted from Google's official
  Calendar API quickstart: https://developers.google.com/calendar/api/quickstart/python
  (Copyright Google LLC, Apache License 2.0)
"""

from __future__ import annotations

from googleapiclient.discovery import build

from .auth import get_credentials


def create_interview_event(
    summary: str,
    start_iso: str,
    end_iso: str,
    description: str = "",
) -> dict:
    """Create an event on the user's primary calendar. Datetimes must be
    ISO 8601 strings with timezone offset, e.g. 2026-09-25T14:00:00-04:00.
    """
    creds = get_credentials()
    service = build("calendar", "v3", credentials=creds)

    event_body = {
        "summary": summary,
        "description": description,
        "start": {"dateTime": start_iso},
        "end": {"dateTime": end_iso},
    }
    created = service.events().insert(calendarId="primary", body=event_body).execute()
    return {"event_id": created.get("id"), "html_link": created.get("htmlLink")}
