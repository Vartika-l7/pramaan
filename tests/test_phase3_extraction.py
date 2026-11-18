"""Acceptance tests for Phase 3: Extraction, Entities, Mentions & Resolution."""

from pathlib import Path
import pytest

from backend.app.db import init_db
from backend.app.ingest.service import ingest_file
from backend.app.ingest.registry import parse_and_store_evidence
from backend.app.extract.patterns import extract_all_identifiers
from backend.app.extract.language import detect_script, transliterate_devanagari_to_latin
from backend.app.extract.names import clean_person_name, extract_persons
from backend.app.extract.resolve import run_entity_extraction

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "case_alpha"


@pytest.fixture
def extract_db():
    case_id = "TEST-CASE-EXTRACTION"
    conn = init_db(case_id)
    yield conn
    conn.close()
    db_file = Path(__file__).resolve().parent.parent / "backend" / "case_data" / f"{case_id}.db"
    for f in db_file.parent.glob(f"{case_id}.db*"):
        try:
            f.unlink()
        except Exception:
            pass


def test_pattern_extractors():
    sample_text = (
        "Please transfer 50,000 INR to our treasury VPA: vikram.alpha@okaxis. "
        "Helpline is +91 90000 10001 or 9000010002. Also Account No: 912345678901 "
        "IFSC PUNB0123456 on Device D1. Visit https://alpha-wealth-club.fake-invest.in"
    )
    matches = extract_all_identifiers(sample_text)
    types_found = {m.type for m in matches}
    assert "UPI" in types_found
    assert "PHONE" in types_found
    assert "ACCOUNT" in types_found
    assert "IFSC" in types_found
    assert "DEVICE" in types_found
    assert "URL" in types_found

    # Verify specific normalized values
    vpas = [m.value_norm for m in matches if m.type == "UPI"]
    assert "vikram.alpha@okaxis" in vpas

    phones = [m.value_norm for m in matches if m.type == "PHONE"]
    assert "+919000010001" in phones


def test_script_and_transliteration():
    dev_text = "विक्रम शर्मा"
    assert detect_script(dev_text) == "DEVANAGARI"
    trans = transliterate_devanagari_to_latin(dev_text)
    assert "vikram" in trans.lower() or "sharma" in trans.lower()


def test_person_extraction_and_fuzzy_resolution(extract_db):
    # Ingest chat and parse
    chat_file = DATA_DIR / "whatsapp_chat_meera_vikram.txt"
    with open(chat_file, "rb") as f:
        ev_meta = ingest_file(extract_db, f, filename=chat_file.name, source_type="whatsapp")
    parse_and_store_evidence(extract_db, ev_meta["id"])

    # Run extraction
    stats = run_entity_extraction(extract_db)
    assert stats["new_entities"] > 0
    assert stats["total_mentions"] > 0

    cursor = extract_db.cursor()
    cursor.execute("SELECT * FROM entities WHERE value_norm = 'vikram.alpha@okaxis';")
    upi_ent = cursor.fetchone()
    assert upi_ent is not None
    assert upi_ent["type"] == "UPI"

    # Verify mentions have character spans
    cursor.execute("SELECT * FROM mentions WHERE entity_id = ?;", (upi_ent["id"],))
    mentions = cursor.fetchall()
    assert len(mentions) > 0
    assert mentions[0]["char_end"] > mentions[0]["char_start"]
    assert mentions[0]["tier"] == "VERIFIED BY CODE"

