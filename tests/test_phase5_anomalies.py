"""Acceptance tests for Phase 5: Anomalies & Authenticity Checks."""

from pathlib import Path
import pytest

from backend.app.db import init_db
from backend.app.ingest.service import ingest_file
from backend.app.api.analyze import execute_full_pipeline

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "case_alpha"


@pytest.fixture
def anomaly_db():
    case_id = "TEST-CASE-ANOMALIES"
    conn = init_db(case_id)
    yield conn
    conn.close()
    db_file = Path(__file__).resolve().parent.parent / "backend" / "case_data" / f"{case_id}.db"
    for f in db_file.parent.glob(f"{case_id}.db*"):
        try:
            f.unlink()
        except Exception:
            pass


def test_anomaly_detection_planted_facts(anomaly_db):
    test_files = [
        ("whatsapp_group_alpha_wealth.txt", "whatsapp"),
        ("bank_statement_mule_A.pdf", "bank_pdf"),
        ("call_log_device1.csv", "calllog"),
        ("call_log_device2.csv", "calllog"),
        ("screenshot_withdrawal_edited.jpg", "image"),
    ]

    for fname, stype in test_files:
        fpath = DATA_DIR / fname
        with open(fpath, "rb") as f:
            ingest_file(anomaly_db, f, filename=fname, source_type=stype)

    # Run complete analysis
    results = execute_full_pipeline("TEST-CASE-ANOMALIES")
    assert results["status"] == "COMPLETED"

    cursor = anomaly_db.cursor()
    cursor.execute("SELECT kind, severity, description, detail_json FROM anomalies;")
    anomalies = cursor.fetchall()
    kinds_found = {a["kind"] for a in anomalies}

    # Verify GT-04: Chat Gap
    assert "ANOMALY_CHAT_GAP" in kinds_found, "GT-04: Chat gap not detected"
    gap_rows = [a for a in anomalies if a["kind"] == "ANOMALY_CHAT_GAP"]
    assert any("6h 14m" in a["description"] or "374" in a["detail_json"] for a in gap_rows), (
        f"GT-04: 6h 14m planted gap on night 3 not found in gap anomalies: {[g['description'] for g in gap_rows]}"
    )

    # Verify GT-05: Out of order
    assert "ANOMALY_OUT_OF_ORDER" in kinds_found, "GT-05: Out-of-order timestamp not detected"

    # Verify GT-06: Edited image
    assert "ANOMALY_IMAGE_EDITED" in kinds_found, "GT-06: Edited image not detected"
    img_row = next(a for a in anomalies if a["kind"] == "ANOMALY_IMAGE_EDITED")
    assert "PixelMod" in img_row["description"] or "PixelMod" in img_row["detail_json"]

    # Verify GT-08: Statement balance mismatch
    assert "ANOMALY_BALANCE_MISMATCH" in kinds_found, "GT-08: Bank balance arithmetic mismatch not detected"
    stmt_row = next(a for a in anomalies if a["kind"] == "ANOMALY_BALANCE_MISMATCH")
    assert "190,000" in stmt_row["description"] or "220,000" in stmt_row["description"]

    # Verify GT-10: Spatial thread
    assert "SPATIAL_THREAD" in kinds_found, "GT-10: Spatial movement not detected"
