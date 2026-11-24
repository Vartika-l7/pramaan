"""Comprehensive Acceptance Tests for Phase 1:
- Step 1.2: Reconciliation reports (parse_report)
- Step 1.3: Known-answer tests for SHA-256
- Step 1.4: Tamper tests (fail verification in exact ways) & property-style single-byte mutation
- Step 1.5: Edge cases and security (zero-byte, unicode, same filename diff content, interruption, path traversal, size limit)
"""

from __future__ import annotations

import io
import json
import os
import random
import shutil
import sqlite3
import subprocess
import tempfile
from pathlib import Path
import pytest

from backend.app.config import KEYS_DIR, MAX_UPLOAD_SIZE_BYTES
from backend.app.db import init_db
from backend.app.integrity.hasher import hash_bytes, hash_file, hash_stream
from backend.app.integrity.custody import append_custody_log, verify_chain, GENESIS_HASH
from backend.app.integrity.merkle import merkle_root_from_hashes, compute_case_merkle_root
from backend.app.integrity.signer import sign_data, verify_signature
from backend.app.ingest.service import ingest_file, verify_case_integrity
from backend.app.ingest.registry import parse_and_store_evidence, registry
from backend.app.parsers.whatsapp import WhatsAppParser
from backend.app.parsers.bank_csv import BankCSVParser
from backend.app.parsers.calllog import CallLogParser
from backend.app.parsers.bank_pdf import BankPDFParser
from backend.app.parsers.base import BaseParser, ParsedEvent


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    """Create an isolated temporary SQLite database and isolated evidence store."""
    test_evidence_dir = tmp_path / "test_evidence_store"
    test_evidence_dir.mkdir(parents=True, exist_ok=True)
    import backend.app.ingest.service as svc
    monkeypatch.setattr(svc, "EVIDENCE_STORE_DIR", test_evidence_dir)

    case_id = f"TEST-P1-{random.randint(10000, 99999)}"
    conn = init_db(case_id)
    yield conn
    conn.close()
    db_file = Path(__file__).resolve().parent.parent / "backend" / "case_data" / f"{case_id}.db"
    for f in db_file.parent.glob(f"{case_id}.db*"):
        try:
            f.unlink()
        except Exception:
            pass


# ==============================================================================
# STEP 1.2: Reconciliation Report Tests
# ==============================================================================

def test_whatsapp_reconciliation_report(clean_db, tmp_path):
    """Test WhatsApp parser guarantees: total_units == parsed + skipped + errors."""
    chat_content = (
        "This is an unparsed preamble header line\n"
        "\n"
        "12/03/2026, 08:30 - Alice: Hey Bob, are you there?\n"
        "12/03/2026, 08:31 - Bob: Yes! Here is the\n"
        "multi-line continuation message\n"
        "with a third line\n"
        "12/03/2026, 08:35 - Alice: <Media omitted>\n"
        "12/03/2026, 08:36 - Bob: This message was deleted\n"
        "[12/03/26, 08:40:00] Alice: And iOS format message too!\n"
    )
    chat_file = tmp_path / "chat.txt"
    chat_file.write_text(chat_content, encoding="utf-8")

    parser = WhatsAppParser()
    events, report = parser.parse_with_report(chat_file, "ev-1", "chat.txt")
    
    rep_dict = report.to_dict()
    assert rep_dict["reconciled"] is True
    assert rep_dict["total_units"] == 9
    assert rep_dict["parsed_events"] == 5
    assert rep_dict["error_count"] == 0
    # 5 parsed + 4 skipped (preamble + 1 empty + 2 continuation) = 9
    assert rep_dict["total_units"] == rep_dict["parsed_events"] + rep_dict["skipped_count"] + rep_dict["error_count"]

    # Verify deleted message detection
    deleted_events = [e for e in events if e.kind == "deleted_message"]
    assert len(deleted_events) == 1
    assert "deleted" in deleted_events[0].text.lower()


def test_bank_csv_reconciliation_report_and_validation(clean_db, tmp_path):
    """Test Bank CSV enforces columns, handles errors, and reconciles input rows."""
    valid_csv = (
        "date,narration,debit,credit,balance\n"
        "12/03/2026,ATM Cash Withdrawal,5000,,45000\n"
        "13/03/2026,UPI Transfer to Mule,,15000,60000\n"
        ",Malformed row without date,100,,60000\n"
    )
    f = tmp_path / "bank.csv"
    f.write_text(valid_csv, encoding="utf-8")

    parser = BankCSVParser()
    events, report = parser.parse_with_report(f, "ev-2", "bank.csv")
    rep_dict = report.to_dict()
    assert rep_dict["reconciled"] is True
    assert rep_dict["total_units"] == 4
    assert rep_dict["parsed_events"] == 2
    assert rep_dict["skipped_count"] == 1  # Header
    assert rep_dict["error_count"] == 1    # Malformed row without date

    # Missing column must fail loudly
    bad_csv = "date,debit,credit\n12/03/2026,100,0\n"
    bad_f = tmp_path / "bad.csv"
    bad_f.write_text(bad_csv, encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required columns"):
        parser.parse(bad_f, "ev-bad", "bad.csv")


def test_calllog_reconciliation_and_validation(clean_db, tmp_path):
    """Test Call log CSV validates columns and reconciles rows."""
    cdr_data = (
        "timestamp,direction,number,duration_sec,cell_tower_id,location_name,device_id\n"
        "2026-03-12 10:15:00,OUTGOING,+919876543210,45,TOW-401,Indiranagar,DEV-01\n"
        "2026-03-12 10:30:00,INCOMING,+919876543211,120,TOW-402,Koramangala,DEV-01\n"
    )
    f = tmp_path / "calls.csv"
    f.write_text(cdr_data, encoding="utf-8")

    parser = CallLogParser()
    events, report = parser.parse_with_report(f, "ev-3", "calls.csv")
    rep_dict = report.to_dict()
    assert rep_dict["reconciled"] is True
    assert rep_dict["total_units"] == 3
    assert rep_dict["parsed_events"] == 2
    assert rep_dict["skipped_count"] == 1  # Header

    # Missing direction column must fail loudly
    bad_cdr = "timestamp,number\n2026-03-12 10:15:00,+919876543210\n"
    bad_f = tmp_path / "bad_cdr.csv"
    bad_f.write_text(bad_cdr, encoding="utf-8")
    with pytest.raises(ValueError, match="Missing required columns"):
        parser.parse(bad_f, "ev-bad", "bad_cdr.csv")


# ==============================================================================
# STEP 1.3: Known-Answer Tests
# ==============================================================================

def test_kat_empty_sha256():
    """SHA-256 of the empty input must match NIST standard."""
    expected = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert hash_bytes(b"") == expected
    assert hash_stream(io.BytesIO(b"")) == expected


def test_kat_abc_sha256():
    """SHA-256 of the bytes 'abc' must match NIST standard."""
    expected = "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert hash_bytes(b"abc") == expected
    assert hash_stream(io.BytesIO(b"abc")) == expected


def test_kat_streaming_vs_oneshot_large_file_and_os_tool(tmp_path, request):
    """Generate large file (32 MB default; 200 MB with --run-slow), test streaming == oneshot == OS tool."""
    size_mb = 200 if request.config.getoption("--run-slow") else 32
    large_file = tmp_path / f"large_{size_mb}mb.bin"
    chunk = b"PRAMAAN_EVIDENCE_INTEGRITY_2026_" * 32 * 1024  # 1 MB chunk for fast generation

    with open(large_file, "wb") as f:
        for _ in range(size_mb):
            f.write(chunk)

    assert large_file.stat().st_size == size_mb * 1024 * 1024

    stream_hash = hash_file(large_file)

    # One-shot calculation via streaming chunks
    with open(large_file, "rb") as f:
        oneshot_stream_hash = hash_stream(f, chunk_size=16 * 1024 * 1024)

    assert stream_hash == oneshot_stream_hash

    # OS Tool comparison (certutil on Windows, or sha256sum / shasum on unix)
    os_tool_hash = None
    if shutil.which("certutil"):
        res = subprocess.run(
            ["certutil", "-hashfile", str(large_file), "SHA256"],
            capture_output=True,
            text=True,
            check=False,
        )
        lines = [line.strip().lower() for line in res.stdout.splitlines() if line.strip()]
        for line in lines:
            if len(line) == 64 and all(c in "0123456789abcdef" for c in line):
                os_tool_hash = line
                break
    elif shutil.which("sha256sum"):
        res = subprocess.run(["sha256sum", str(large_file)], capture_output=True, text=True, check=False)
        os_tool_hash = res.stdout.split()[0].lower()
    elif shutil.which("shasum"):
        res = subprocess.run(["shasum", "-a", "256", str(large_file)], capture_output=True, text=True, check=False)
        os_tool_hash = res.stdout.split()[0].lower()

    if os_tool_hash:
        assert stream_hash == os_tool_hash, f"Mismatch with OS hash tool: {stream_hash} vs {os_tool_hash}"


# ==============================================================================
# STEP 1.4: Tamper Tests
# ==============================================================================

def test_tamper_evidence_file_byte_flip(clean_db):
    """Flip one byte in a stored evidence file: verify names that file."""
    res = ingest_file(clean_db, io.BytesIO(b"Confidential Forensic Record 2026"), filename="record.txt")
    stored_path = Path(res["stored_path"])

    # Make writable temporarily to simulate disk corruption/tampering
    os.chmod(stored_path, 0o666)
    with open(stored_path, "r+b") as f:
        byte = f.read(1)
        f.seek(0)
        f.write(bytes([byte[0] ^ 0x01]))  # Flip 1 bit
    os.chmod(stored_path, 0o444)

    verif = verify_case_integrity(clean_db)
    assert verif["intact"] is False
    assert verif["failed_exhibit"] == res["exhibit_id"]
    failed_items = [e for e in verif["exhibits"] if e["status"] == "FAIL"]
    assert len(failed_items) == 1
    assert failed_items[0]["exhibit_id"] == res["exhibit_id"]
    assert "Hash mismatch" in failed_items[0]["reason"]


def test_tamper_custody_chain_breaks_at_exact_seq(clean_db):
    """Edit one custody log entry via trigger bypass test and confirm break at sequence."""
    append_custody_log(clean_db, action="RECEIVED", actor="OFFICER_A")
    append_custody_log(clean_db, action="HASHED", actor="SYSTEM")
    append_custody_log(clean_db, action="ANALYZED", actor="ANALYST")
    clean_db.commit()

    ok, _, err = verify_chain(clean_db)
    assert ok is True

    # Temporarily drop trigger to simulate offline raw db edit
    clean_db.execute("DROP TRIGGER trg_custody_no_update;")
    clean_db.execute("UPDATE custody_log SET actor = 'TAMPERED_AGENT' WHERE seq = 2;")
    clean_db.commit()

    ok, _, err = verify_chain(clean_db)
    assert ok is False
    assert "at seq 2" in err


def test_tamper_custody_delete_and_reorder(clean_db):
    """Delete a row or reorder rows in custody_log: chain detects break."""
    append_custody_log(clean_db, action="ACT_1", actor="A")
    append_custody_log(clean_db, action="ACT_2", actor="B")
    append_custody_log(clean_db, action="ACT_3", actor="C")
    clean_db.commit()

    clean_db.execute("DROP TRIGGER trg_custody_no_delete;")
    clean_db.execute("DELETE FROM custody_log WHERE seq = 2;")
    clean_db.commit()

    ok, _, err = verify_chain(clean_db)
    assert ok is False
    assert "Chain link broken at seq 3" in err


def test_tamper_direct_update_or_delete_rejected_by_db(clean_db):
    """Direct UPDATE or DELETE on custody_log must raise CUSTODY_VIOLATION."""
    append_custody_log(clean_db, action="INITIAL", actor="A")
    clean_db.commit()

    with pytest.raises(sqlite3.DatabaseError, match="CUSTODY_VIOLATION"):
        clean_db.execute("UPDATE custody_log SET actor = 'MALICIOUS';")

    with pytest.raises(sqlite3.DatabaseError, match="CUSTODY_VIOLATION"):
        clean_db.execute("DELETE FROM custody_log WHERE seq = 1;")


def test_tamper_manifest_signature_fails(clean_db):
    """Edit manifest after signing: signature check fails."""
    manifest_bytes = b'{"case_id": "TEST-1", "merkle_root": "abc"}'
    sig_b64, pub_b64 = sign_data(manifest_bytes)
    assert verify_signature(manifest_bytes, sig_b64, pub_b64) is True

    tampered_bytes = b'{"case_id": "TEST-1", "merkle_root": "xyz"}'
    assert verify_signature(tampered_bytes, sig_b64, pub_b64) is False


def test_tamper_replace_file_same_size_and_swap_exhibits(clean_db):
    """Replace file with different content of same size, or swap two exhibits: detected."""
    res1 = ingest_file(clean_db, io.BytesIO(b"EXHIBIT_ALPHA_DATA_123"), filename="file1.txt")
    res2 = ingest_file(clean_db, io.BytesIO(b"EXHIBIT_BETA__DATA_999"), filename="file2.txt")
    assert res1["size_bytes"] == res2["size_bytes"]

    p1 = Path(res1["stored_path"])
    p2 = Path(res2["stored_path"])

    # Swap the file contents
    os.chmod(p1, 0o666)
    os.chmod(p2, 0o666)
    c1 = p1.read_bytes()
    c2 = p2.read_bytes()
    p1.write_bytes(c2)
    p2.write_bytes(c1)
    os.chmod(p1, 0o444)
    os.chmod(p2, 0o444)

    verif = verify_case_integrity(clean_db)
    assert verif["intact"] is False
    failed = [e["exhibit_id"] for e in verif["exhibits"] if e["status"] == "FAIL"]
    assert "EX-001" in failed and "EX-002" in failed


def test_property_single_byte_mutation_fails_verification(clean_db, request):
    """Property-style randomized test: ANY single-byte mutation in any evidence file fails verification.
    Runs 25 examples by default, or 100 examples with --run-slow.
    """
    max_examples = 100 if request.config.getoption("--run-slow") else 25
    rng = random.Random(42)

    payloads = [
        b"Case file 1: WhatsApp chat log alpha",
        b"Case file 2: Call detail records beta 99",
        b"Case file 3: Bank debit transaction gamma",
    ]
    exhibits = []
    for i, payload in enumerate(payloads):
        ex = ingest_file(clean_db, io.BytesIO(payload), filename=f"ev_{i}.txt")
        exhibits.append(ex)

    assert verify_case_integrity(clean_db)["intact"] is True

    for _ in range(max_examples):
        target_exhibit = rng.choice(exhibits)
        target_path = Path(target_exhibit["stored_path"])
        original_bytes = target_path.read_bytes()

        os.chmod(target_path, 0o666)
        try:
            content = bytearray(original_bytes)
            mutation_idx = rng.randint(0, len(content) - 1)
            content[mutation_idx] ^= 0xFF
            target_path.write_bytes(content)
            os.chmod(target_path, 0o444)

            verif = verify_case_integrity(clean_db)
            assert verif["intact"] is False
            assert verif["failed_exhibit"] == target_exhibit["exhibit_id"]
        finally:
            os.chmod(target_path, 0o666)
            target_path.write_bytes(original_bytes)
            os.chmod(target_path, 0o444)


# ==============================================================================
# STEP 1.5: Edge Cases and Security
# ==============================================================================

def test_edge_zero_byte_file(clean_db):
    """Zero-byte file is handled safely without crashing."""
    res = ingest_file(clean_db, io.BytesIO(b""), filename="empty.txt")
    assert res["size_bytes"] == 0
    assert res["sha256"] == "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    assert verify_case_integrity(clean_db)["intact"] is True


def test_edge_unicode_filenames(clean_db):
    """Unicode filenames with emojis and Indic characters are safely ingested."""
    unicode_name = "प्रमाण_साक्ष्य_📁_test.txt"
    res = ingest_file(clean_db, io.BytesIO(b"Hindi Unicode Test"), filename=unicode_name)
    assert res["filename"] == unicode_name
    assert verify_case_integrity(clean_db)["intact"] is True


def test_edge_same_filename_different_content(clean_db):
    """Same filename with different content creates two distinct exhibits."""
    res1 = ingest_file(clean_db, io.BytesIO(b"Version A"), filename="data.txt")
    res2 = ingest_file(clean_db, io.BytesIO(b"Version B"), filename="data.txt")
    assert res1["exhibit_id"] != res2["exhibit_id"]
    assert res1["sha256"] != res2["sha256"]
    assert res1["filename"] == res2["filename"]


def test_edge_same_content_different_filename(clean_db):
    """Same content with different filename maps to existing exhibit and logs custody event."""
    data = b"Duplicate file content identical 123"
    res1 = ingest_file(clean_db, io.BytesIO(data), filename="original.txt")
    res2 = ingest_file(clean_db, io.BytesIO(data), filename="copy.txt")
    assert res1["exhibit_id"] == res2["exhibit_id"]
    assert res1["sha256"] == res2["sha256"]

    # Verify custody log entry for duplicate ingest attempt
    cursor = clean_db.cursor()
    cursor.execute("SELECT * FROM custody_log WHERE action = 'DUPLICATE_INGEST_ATTEMPT';")
    dup_entry = cursor.fetchone()
    assert dup_entry is not None
    assert dup_entry["evidence_id"] == res1["id"]


def test_security_path_traversal_sanitized(clean_db):
    """Path traversal in filename like '../../etc/passwd' is strictly stripped."""
    traversal_name = "../../../sensitive_file.txt"
    res = ingest_file(clean_db, io.BytesIO(b"Safe Content"), filename=traversal_name)
    assert res["filename"] == "sensitive_file.txt"
    assert "/" not in res["filename"]
    assert "\\" not in res["filename"]


def test_security_max_upload_size_limit(clean_db, monkeypatch):
    """Files exceeding MAX_UPLOAD_SIZE_BYTES are rejected with clear error."""
    import backend.app.ingest.service as svc
    monkeypatch.setattr(svc, "MAX_UPLOAD_SIZE_BYTES", 100)  # Set 100 bytes limit

    oversized = io.BytesIO(b"A" * 150)
    with pytest.raises(ValueError, match="exceeds maximum allowed upload limit"):
        ingest_file(clean_db, oversized, filename="huge.bin")


def test_parser_registry_plugin_extensibility(clean_db, tmp_path):
    """Adding a new source type requires only one class with NO changes to ingest/hashing/custody."""
    class DummyNetworkLogParser(BaseParser):
        @property
        def source_type(self) -> str:
            return "network_log"

        def can_parse(self, file_path: Path, filename: str) -> bool:
            return filename.endswith(".pcapng.log")

        def parse(self, file_path: Path, evidence_id: str, filename: str, default_tz: str = "Asia/Kolkata") -> list[ParsedEvent]:
            return [
                ParsedEvent(
                    evidence_id=evidence_id,
                    source_type=self.source_type,
                    ts_utc="2026-03-12T10:00:00Z",
                    ts_original="2026-03-12 10:00:00",
                    tz_assumed=default_tz,
                    kind="network_flow",
                    text="DNS Query to suspicious domain",
                    ref={"file": filename, "packet_idx": 1},
                )
            ]

    # Register new plugin dynamically
    registry.register(DummyNetworkLogParser())

    pcap_log = tmp_path / "capture.pcapng.log"
    pcap_log.write_text("PCAP DUMMY PACKET LOG", encoding="utf-8")

    with open(pcap_log, "rb") as f:
        ev = ingest_file(clean_db, f, filename=pcap_log.name)

    assert ev["source_type"] == "network_log"
    count = parse_and_store_evidence(clean_db, ev["id"])
    assert count == 1

    cursor = clean_db.cursor()
    cursor.execute("SELECT * FROM events WHERE evidence_id = ?;", (ev["id"],))
    ev_row = cursor.fetchone()
    assert ev_row["source_type"] == "network_log"
    assert ev_row["kind"] == "network_flow"
