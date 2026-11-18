"""Acceptance tests for Phase 2: Parsers & Event Store."""

from pathlib import Path
import pytest

from backend.app.db import init_db
from backend.app.ingest.service import ingest_file
from backend.app.ingest.registry import parse_and_store_evidence

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "case_alpha"


@pytest.fixture
def parser_db():
    case_id = "TEST-CASE-PARSERS"
    conn = init_db(case_id)
    yield conn
    conn.close()
    db_file = Path(__file__).resolve().parent.parent / "backend" / "case_data" / f"{case_id}.db"
    for f in db_file.parent.glob(f"{case_id}.db*"):
        try:
            f.unlink()
        except Exception:
            pass


def test_parse_whatsapp_chats(parser_db):
    group_file = DATA_DIR / "whatsapp_group_alpha_wealth.txt"
    with open(group_file, "rb") as f:
        ev_meta = ingest_file(parser_db, f, filename=group_file.name, source_type="whatsapp")

    count = parse_and_store_evidence(parser_db, ev_meta["id"])
    assert count > 500, f"Expected >500 events, parsed {count}"

    cursor = parser_db.cursor()
    cursor.execute("SELECT * FROM events WHERE evidence_id = ? AND kind = 'message' LIMIT 1;", (ev_meta["id"],))
    row = cursor.fetchone()
    assert row is not None
    assert row["tz_assumed"] == "Asia/Kolkata"
    assert "line_start" in row["ref_json"]
    assert "byte_offset" in row["ref_json"]


def test_parse_bank_statements_pdf_and_csv(parser_db):
    # PDF Statement
    pdf_file = DATA_DIR / "bank_statement_meera.pdf"
    with open(pdf_file, "rb") as f:
        ev_meta = ingest_file(parser_db, f, filename=pdf_file.name, source_type="bank_pdf")

    pdf_count = parse_and_store_evidence(parser_db, ev_meta["id"])
    assert pdf_count >= 3, f"Expected at least 3 transactions in Meera statement, found {pdf_count}"

    cursor = parser_db.cursor()
    cursor.execute("SELECT * FROM events WHERE evidence_id = ? AND amount = 50000.0;", (ev_meta["id"],))
    txn = cursor.fetchone()
    assert txn is not None
    assert txn["kind"] == "debit"

    # CSV Statement
    csv_file = DATA_DIR / "bank_statement_mule_B.csv"
    with open(csv_file, "rb") as f:
        csv_meta = ingest_file(parser_db, f, filename=csv_file.name, source_type="bank_csv")

    csv_count = parse_and_store_evidence(parser_db, csv_meta["id"])
    assert csv_count >= 5


def test_parse_call_logs(parser_db):
    call_file = DATA_DIR / "call_log_device1.csv"
    with open(call_file, "rb") as f:
        call_meta = ingest_file(parser_db, f, filename=call_file.name, source_type="calllog")

    count = parse_and_store_evidence(parser_db, call_meta["id"])
    assert count >= 6

    cursor = parser_db.cursor()
    cursor.execute("SELECT * FROM events WHERE evidence_id = ? AND counterparty = '+91 90000 10003';", (call_meta["id"],))
    call_row = cursor.fetchone()
    assert call_row is not None
    assert "TOW-" in call_row["location_id"]


def test_parse_image_metadata(parser_db):
    img_file = DATA_DIR / "screenshot_withdrawal_edited.jpg"
    with open(img_file, "rb") as f:
        img_meta = ingest_file(parser_db, f, filename=img_file.name, source_type="image")

    count = parse_and_store_evidence(parser_db, img_meta["id"])
    assert count == 1

    cursor = parser_db.cursor()
    cursor.execute("SELECT * FROM events WHERE evidence_id = ?;", (img_meta["id"],))
    row = cursor.fetchone()
    assert "PixelMod Editor Pro v2.4" in row["ref_json"]
    assert "phash" in row["ref_json"]

