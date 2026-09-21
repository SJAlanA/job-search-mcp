"""
job-search-mcp: an MCP server that turns your Gmail inbox and a local
SQLite tracker into a job-search assistant Claude Desktop can talk to.

Domain: Personal Productivity (task tracking + email summarization).

Components (resource + tool + tool + prompt -- exceeds the assignment's
"resource, a tool, and a prompt" minimum by one extra tool, because
splitting read vs. write access into two tools maps directly onto the
least-privilege security boundary described in the README):

  resource  tracker://applications  -- current tracker rows, read-only
  tool      scan_inbox              -- search Gmail (read-only scope)
  tool      update_application      -- write to tracker (+ optional calendar event)
  prompt    triage_inbox            -- instructs the LLM how to safely
                                        chain scan_inbox -> update_application

Reference:
- FastMCP server structure (@mcp.tool / @mcp.resource / @mcp.prompt,
  mcp.run()) adapted from the official MCP Python SDK README quickstart:
  https://github.com/modelcontextprotocol/python-sdk
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from typing import Optional

from mcp.server.fastmcp import FastMCP

from job_search_mcp import config, db, security
from job_search_mcp.calendar_client import create_interview_event
from job_search_mcp.gmail_client import search_messages

mcp = FastMCP("job-search-mcp")


@mcp.resource("tracker://applications")
def applications_resource() -> str:
    """The full job-application tracker as JSON. Read-only: Claude can
    inspect current state here without spending a tool call."""
    try:
        rows = db.get_applications()
        return json.dumps(rows, indent=2)
    except Exception as exc:  # noqa: BLE001 -- deliberately broad, see security.safe_error
        return json.dumps(security.safe_error(exc, "Could not load the tracker.").__dict__)


@mcp.tool()
def scan_inbox(query: str = "subject:(interview OR application OR offer)", max_results: int = 10) -> dict:
    """Search the connected Gmail inbox (read-only) for job-related emails.

    Args:
        query: A Gmail search query (same syntax as the Gmail search box,
            e.g. 'from:greenhouse.io newer_than:14d'). Defaults to a broad
            job-related subject search.
        max_results: How many matching emails to return (capped server-side).

    Returns metadata only (subject/from/date/snippet) for each match --
    never full message bodies -- so review each result yourself before
    calling update_application on it.
    """
    try:
        clean_query = security.sanitize_query(query)
        capped = max(1, min(int(max_results), config.MAX_SCAN_RESULTS))
        results = search_messages(clean_query, capped)
        return {"ok": True, "count": len(results), "messages": results}
    except security.ValidationError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return security.safe_error(exc, "Could not search the inbox right now.").__dict__


@mcp.tool()
def update_application(
    company: str,
    role: str,
    status: str,
    notes: str = "",
    source_email_id: Optional[str] = None,
    interview_datetime: Optional[str] = None,
) -> dict:
    """Create or update a row in the job-application tracker.

    Args:
        company: Company name.
        role: Job title / role applied for.
        status: One of: researching, applied, screening, interview, offer,
            rejected, withdrawn.
        notes: Free-text context (e.g. "recruiter said 2 more rounds").
        source_email_id: Gmail message id this update came from, if any
            (from a prior scan_inbox call) -- kept for traceability.
        interview_datetime: ISO 8601 datetime with timezone offset, e.g.
            "2026-09-25T14:00:00-04:00". If set, also creates a 1-hour
            Google Calendar event so the interview shows up on your calendar.

    All fields are validated and bound as SQL parameters before touching
    the database -- this is the input-sanitization boundary described in
    the README (see exploits/exploit_sql_injection.py for a live demo).
    """
    try:
        clean_company = security.sanitize_text(company, "company")
        clean_role = security.sanitize_text(role, "role")
        clean_status = security.sanitize_status(status)
        clean_notes = security.sanitize_text(notes, "notes", max_len=2000) if notes else ""

        calendar_result = None
        if interview_datetime:
            start = datetime.fromisoformat(interview_datetime)
            end = start + timedelta(hours=1)
            calendar_result = create_interview_event(
                summary=f"Interview: {clean_company} ({clean_role})",
                start_iso=start.isoformat(),
                end_iso=end.isoformat(),
                description=clean_notes,
            )

        row = db.upsert_application(
            company=clean_company,
            role=clean_role,
            status=clean_status,
            notes=clean_notes,
            source_email_id=source_email_id,
            interview_datetime=interview_datetime,
        )
        return {"ok": True, "application": row, "calendar_event": calendar_result}
    except security.ValidationError as exc:
        return {"ok": False, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return security.safe_error(exc, "Could not update the tracker right now.").__dict__


@mcp.prompt()
def triage_inbox() -> str:
    """Prompt template: guides Claude through safely triaging job-related
    emails into the tracker without fabricating data or over-writing status
    without evidence."""
    return (
        "You're helping me keep my job-search tracker current.\n\n"
        "1. Call scan_inbox with a query covering the last 14 days of "
        "job-related mail (applications, interview invites, offers, "
        "rejections, recruiter outreach).\n"
        "2. For each email, read only the subject/from/snippet returned -- "
        "do not guess at content that isn't there.\n"
        "3. Classify each into a status: researching, applied, screening, "
        "interview, offer, rejected, or withdrawn. If you're not confident, "
        "ask me instead of guessing.\n"
        "4. Call update_application for each confident classification, "
        "passing the email's id as source_email_id. If the email mentions "
        "an interview date/time, include interview_datetime so it lands on "
        "my calendar.\n"
        "5. Show me a summary table of what you updated before finishing -- "
        "do not silently make changes I can't review."
    )


def main() -> None:
    mcp.run()


if __name__ == "__main__":
    main()
