# Code citations

Per the assignment's citation requirement, every piece of code adapted
from an external source is cited inline as a comment at the top of the
file it appears in, and summarized here.

| File | What was adapted | Source |
|---|---|---|
| `src/job_search_mcp/server.py` | FastMCP server structure: `@mcp.tool()` / `@mcp.resource()` / `@mcp.prompt()` decorators, `mcp.run()` entrypoint | [MCP Python SDK README quickstart](https://github.com/modelcontextprotocol/python-sdk) |
| `src/job_search_mcp/auth.py` | OAuth 2.0 `InstalledAppFlow` / token-caching structure | [Google Gmail API Python quickstart](https://developers.google.com/gmail/api/quickstart/python) (Copyright Google LLC, Apache License 2.0) |
| `src/job_search_mcp/gmail_client.py` | `googleapiclient.discovery.build()` usage pattern for listing/getting messages | [Google Gmail API Python quickstart](https://developers.google.com/gmail/api/quickstart/python) (Copyright Google LLC, Apache License 2.0) |
| `src/job_search_mcp/calendar_client.py` | `googleapiclient.discovery.build()` usage pattern for inserting events | [Google Calendar API Python quickstart](https://developers.google.com/calendar/api/quickstart/python) (Copyright Google LLC, Apache License 2.0) |
| `src/job_search_mcp/db.py` | Parameterized-placeholder pattern (`?` binding, never string interpolation) | [Python `sqlite3` docs](https://docs.python.org/3/library/sqlite3.html#how-to-use-placeholders-to-bind-values-in-sql-queries) |
| `src/job_search_mcp/config.py` | `.env` loading pattern via `python-dotenv` | [python-dotenv README](https://github.com/theskumar/python-dotenv#usage) |

Everything else (the tracker schema, the sanitization rules in
`security.py`, the two exploit scripts, the prompt template text, and all
tool/resource wiring specific to this job-search domain) is original for
this assignment, written with Claude (Cowork) as an AI pair-programming
assistant per the assignment's required use of an AI assistant.
