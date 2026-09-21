"""
Central configuration for the job-search MCP server.

Secrets and paths are loaded via python-dotenv + pathlib.Path, per the
assignment's secret-management requirement (no os.path, no credentials
stored directly as OS environment variables checked into anything).

Reference:
- python-dotenv usage pattern adapted from the project's own README quickstart:
  https://github.com/theskumar/python-dotenv#usage
"""

from pathlib import Path
from dotenv import load_dotenv
import os

# Project root = two levels up from this file (src/job_search_mcp/config.py -> project root)
BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

# Load variables from a local .env file (never committed; see .env.example)
load_dotenv(BASE_DIR / ".env")

# --- Google OAuth ---------------------------------------------------------
# Path to the OAuth *client* secret downloaded from Google Cloud Console
# (identifies the app, not the user). Never commit this file.
GOOGLE_CLIENT_SECRET_PATH: Path = Path(
    os.getenv("GOOGLE_CLIENT_SECRET_PATH", str(BASE_DIR / "credentials" / "client_secret.json"))
)

# Path where the user's cached OAuth token (refresh + access token) is stored
# after the first interactive consent flow. Never commit this file.
GOOGLE_TOKEN_PATH: Path = Path(
    os.getenv("GOOGLE_TOKEN_PATH", str(BASE_DIR / "credentials" / "token.json"))
)

# Minimum scopes needed. Gmail is read-only by design (the server never
# sends, deletes, or modifies mail) -- least privilege for a tool that only
# needs to *observe* your inbox to keep the tracker current.
GOOGLE_SCOPES: list[str] = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar.events",
]

# --- Local data ------------------------------------------------------------
DATA_DIR: Path = Path(os.getenv("JOB_SEARCH_DATA_DIR", str(BASE_DIR / "data")))
DB_PATH: Path = DATA_DIR / "tracker.db"
ERROR_LOG_PATH: Path = DATA_DIR / "server_errors.log"

# --- Limits / sanitization ---------------------------------------------------
MAX_TEXT_FIELD_LEN: int = 500
MAX_QUERY_LEN: int = 200
MAX_SCAN_RESULTS: int = 25

ALLOWED_STATUSES: set[str] = {
    "researching",
    "applied",
    "screening",
    "interview",
    "offer",
    "rejected",
    "withdrawn",
}


def ensure_dirs() -> None:
    """Create data/credentials directories on first run."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    GOOGLE_CLIENT_SECRET_PATH.parent.mkdir(parents=True, exist_ok=True)
