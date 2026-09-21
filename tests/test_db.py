"""Unit tests for the tracker DB layer, including a SQL-injection regression
test that mirrors exploits/exploit_sql_injection.py.
Run with: pytest tests/
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from job_search_mcp import db


def test_upsert_and_get_roundtrip():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        db.init_db(db_path)
        db.upsert_application("Acme", "TPM", "applied", db_path=db_path)
        rows = db.get_applications(db_path=db_path)
        assert len(rows) == 1
        assert rows[0]["company"] == "Acme"
        assert rows[0]["status"] == "applied"


def test_upsert_same_company_role_updates_not_duplicates():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        db.init_db(db_path)
        db.upsert_application("Acme", "TPM", "applied", db_path=db_path)
        db.upsert_application("Acme", "TPM", "interview", db_path=db_path)
        rows = db.get_applications(db_path=db_path)
        assert len(rows) == 1
        assert rows[0]["status"] == "interview"


def test_sql_injection_payload_is_stored_as_inert_text():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        db.init_db(db_path)
        payload = "Acme'); DROP TABLE applications; --"
        db.upsert_application(payload, "TPM", "applied", db_path=db_path)
        # Table must still exist and be queryable.
        rows = db.get_applications(db_path=db_path)
        assert len(rows) == 1
        assert rows[0]["company"] == payload
