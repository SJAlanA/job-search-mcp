"""
Google OAuth 2.0 authentication.

The consent flow (run_local_server) is interactive: it opens a browser,
you sign in and approve the requested scopes once, and the resulting
token is cached to disk (config.GOOGLE_TOKEN_PATH) so future runs don't
need to prompt again. Run `python -m job_search_mcp.auth` once, from a
real terminal (not over a remote shell), to complete that first consent.

Reference:
- OAuth flow structure adapted from Google's official quickstart:
  https://developers.google.com/gmail/api/quickstart/python
  (Copyright Google LLC, Apache License 2.0)
"""

from __future__ import annotations

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from . import config


def get_credentials() -> Credentials:
    """Return valid user credentials, refreshing or running the interactive
    consent flow as needed. Tokens are read/written via pathlib.Path only.
    """
    creds: Credentials | None = None

    if config.GOOGLE_TOKEN_PATH.exists():
        creds = Credentials.from_authorized_user_file(
            str(config.GOOGLE_TOKEN_PATH), config.GOOGLE_SCOPES
        )

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not config.GOOGLE_CLIENT_SECRET_PATH.exists():
                raise FileNotFoundError(
                    "Google OAuth client secret not found. Download it from Google Cloud "
                    "Console and save it to the path set by GOOGLE_CLIENT_SECRET_PATH in .env."
                )
            flow = InstalledAppFlow.from_client_secrets_file(
                str(config.GOOGLE_CLIENT_SECRET_PATH), config.GOOGLE_SCOPES
            )
            creds = flow.run_local_server(port=0)

        config.GOOGLE_TOKEN_PATH.parent.mkdir(parents=True, exist_ok=True)
        config.GOOGLE_TOKEN_PATH.write_text(creds.to_json())

    return creds


if __name__ == "__main__":
    # One-time interactive setup: `python -m job_search_mcp.auth`
    get_credentials()
    print(f"Authenticated. Token cached at {config.GOOGLE_TOKEN_PATH}")
