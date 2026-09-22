# job-search-mcp

A local MCP server that turns your Gmail inbox and Google Calendar into a
job-application tracker Claude Desktop can query and update on request.
Ask Claude to "check my inbox for job updates," and it searches Gmail
(read-only), classifies what it finds, and writes structured rows to a
local SQLite tracker -- creating a calendar event automatically when it
spots an interview time.

Built for Cornell ENMGT (MCP Assignment). Domain: **Personal Productivity**
(task tracking + email summarization).

> **AI disclaimer:** The idea for this project was conceived by the author (SJAlanA). The implementation was coded with the assistance of Claude Sonnet.

## What it exposes

| Type     | Name                  | Purpose                                                             |
|----------|-----------------------|----------------------------------------------------------------------|
| Resource | `tracker://applications` | Read the current tracker as JSON, no tool call needed.            |
| Tool     | `scan_inbox`          | Search Gmail (read-only) for job-related emails.                     |
| Tool     | `update_application`  | Create/update a tracker row; optionally creates a Calendar event.    |
| Prompt   | `triage_inbox`        | Template that walks Claude through safely chaining the two tools.    |

(The architecture diagram, the domain/best-practices summary table, and
the reflection are submitted separately to Canvas per the assignment
instructions, not included in this repository.) See
[`CITATIONS.md`](CITATIONS.md) for where each piece of external reference
code came from.

## Security / best practices implemented

1. **Input Sanitization** (`src/job_search_mcp/security.py` +
   parameterized SQL in `src/job_search_mcp/db.py`) -- every field is
   validated/normalized before it reaches the database, and all SQL uses
   `?` placeholders, never string interpolation. Demo:
   `python exploits/exploit_sql_injection.py`.
2. **Error Disclosure prevention** (`security.safe_error()`) -- every tool
   routes exceptions through one function that logs full detail locally
   (with secrets redacted even there) but returns only a generic message
   + a short correlation id to the MCP client. Demo:
   `python exploits/exploit_error_disclosure.py`.

Both exploit scripts print a clear before/after and assert the block
actually held -- they exit non-zero if a regression ever reopens the hole.

## Setup

### 1. Prerequisites

- Python 3.10+
- [uv](https://docs.astral.sh/uv/) (recommended) or Anaconda
- A Google account, and a Google Cloud project with the **Gmail API** and
  **Google Calendar API** enabled

### 2. Google Cloud OAuth setup (one-time, ~15 min)

1. Go to [Google Cloud Console](https://console.cloud.google.com/) and
   create (or reuse) a project.
2. Under **APIs & Services > Library**, enable **Gmail API** and
   **Google Calendar API**.
3. Under **APIs & Services > OAuth consent screen**, configure an
   External app in Testing mode, and add your own Google account under
   **Test users**.
4. Under **APIs & Services > Credentials**, click **Create Credentials >
   OAuth client ID**, choose **Desktop app**, and download the resulting
   JSON.
5. Save that file as `credentials/client_secret.json` in this project
   (create the `credentials/` folder -- it's gitignored, never commit it).

### 3. Python environment

```bash
uv venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
uv pip install -r requirements.txt
```

### 4. Configure secrets

```bash
cp .env.example .env
```

The defaults in `.env` already point at `./credentials/client_secret.json`
and `./credentials/token.json` -- only change them if you moved the files.
All paths are loaded via `pathlib.Path` in `src/job_search_mcp/config.py`,
per the assignment's secret-management requirement (no `os.path`, no
credentials stored as raw OS environment variables).

### 5. First-time Google sign-in

Run this once, from a real terminal (it opens a browser window and needs
you to click "Allow"):

```bash
python -m job_search_mcp.auth
```

This caches a refresh token to `credentials/token.json` so you won't be
prompted again.

### 6. Run the server directly (sanity check)

```bash
uv run mcp dev src/job_search_mcp/server.py
```

This opens the MCP Inspector in your browser so you can call
`scan_inbox` / `update_application` / read the resource by hand before
wiring it into Claude Desktop.

### 7. Run the tests and exploit demos

```bash
python -m pytest tests/ -v
python exploits/exploit_sql_injection.py
python exploits/exploit_error_disclosure.py
```

### 8. Connect to Claude Desktop

Copy the block from [`claude_desktop_config.json`](claude_desktop_config.json)
into your Claude Desktop config file
(`~/Library/Application Support/Claude/claude_desktop_config.json` on
macOS), fixing the two `<...>` placeholders to absolute paths on your
machine, then restart Claude Desktop. You should see "job-search-mcp"
listed under the hammer/MCP icon.

Try asking Claude: *"Use triage_inbox to check my email for job search
updates from the last two weeks."*

## Project structure

```
src/job_search_mcp/
  config.py           # paths + secrets (pathlib + .env, no os.path)
  security.py          # input sanitization + safe_error()
  db.py                 # SQLite tracker, parameterized queries
  auth.py               # Google OAuth flow + token caching
  gmail_client.py       # Gmail read-only search
  calendar_client.py    # Calendar event creation
  server.py             # FastMCP server: resource, tools, prompt
tests/                   # pytest unit tests, incl. an injection regression test
exploits/                # standalone exploit demo scripts (see Security section)
```

## Design notes

`scan_inbox` and `update_application` are deliberately two separate
tools rather than one combined "sync my inbox" tool, because they sit on
opposite sides of a real security boundary: `scan_inbox` only needs the
`gmail.readonly` OAuth scope and can never write anything, while
`update_application` is the only place that touches the database or
creates calendar events. Read vs. write access is enforced at the OAuth
scope level, not just in application code -- so even a bug in the server
can't turn a "read my inbox" request into a "send/delete mail" action.

## Limitations

- Email -> status classification is done by the calling LLM (Claude), not
  by this server -- `scan_inbox` returns raw metadata and leaves
  interpretation to the model, per the `triage_inbox` prompt's
  instructions. This keeps the server simple and auditable, but means
  classification quality depends on the client LLM.
- No rate limiting is implemented (out of scope for this submission --
  see the assignment's best-practices requirement of two, not four).
- Single-user, local-only: credentials and the tracker DB are stored on
  disk with no encryption at rest, which is acceptable for a personal
  local tool but not for a shared/multi-user deployment.
