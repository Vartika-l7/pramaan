"""Acceptance tests for Phase 1: Ingest, Hashing, Custody Log Chain, Merkle Root, and Signing."""

import io
import os
import sqlite3
import tempfile
from pathlib import Path
import pytest

from backend.app.db import init_db
from backend.app.integrity.hasher import hash_bytes, hash_file, hash_stream
from backend.app.integrity.custody import append_custody_log, verify_chain, GENESIS_HASH
from backend.app.integrity.merkle import merkle_root_from_hashes, compute_case_merkle_root
from backend.app.integrity.signer import sign_data, verify_signature
from backend.app.ingest.service import ingest_file, verify_case_integrity


@pytest.fixture
def test_db():
    """Create an isolated temporary SQLite database for testing."""
    test_case_id = "TEST-CASE-INTEGRITY"
    conn = init_db(test_case_id)
    yield conn
    conn.close()
    # Cleanup DB file
    db_file = Path(__file__).resolve().parent.parent / "backend" / "case_data" / f"{test_case_id}.db"
    for f in db_file.parent.glob(f"{test_case_id}.db*"):
        try:
            f.unlink()
        except Exception:
            pass


def test_streaming_hasher():
    content = b"PRAMAAN Offline Digital Forensics Framework 2026" * 1000
    expected_hash = hash_bytes(content)
    
    stream = io.BytesIO(content)
    assert hash_stream(stream) == expected_hash

    with tempfile.NamedTemporaryFile(delete=False) as tf:
        tf.write(content)
        tf_path = Path(tf.name)

    try:
        assert hash_file(tf_path) == expected_hash
    finally:
        tf_path.unlink()


def test_custody_log_triggers_prevent_update_and_delete(test_db):
    """Ensure SQLite triggers strictly forbid UPDATE and DELETE operations on custody_log."""
    # Append valid entries
    e1 = append_custody_log(test_db, action="RECEIVED", actor="OFFICER_A", details={"note": "first"})
    e2 = append_custody_log(test_db, action="HASHED", actor="SYSTEM", details={"note": "second"})
    test_db.commit()

    # Attempt UPDATE -> Must be rejected by trigger
    with pytest.raises(sqlite3.DatabaseError, match="CUSTODY_VIOLATION"):
        test_db.execute("UPDATE custody_log SET actor = 'TAMPERED' WHERE seq = 1;")

    # Attempt DELETE -> Must be rejected by trigger
    with pytest.raises(sqlite3.DatabaseError, match="CUSTODY_VIOLATION"):
        test_db.execute("DELETE FROM custody_log WHERE seq = 1;")


def test_custody_chain_verification(test_db):
    """Verify hash chaining detects broken links or alterations."""
    append_custody_log(test_db, action="RECEIVED", actor="AGENT_1")
    append_custody_log(test_db, action="HASHED", actor="SYSTEM")
    append_custody_log(test_db, action="PARSED", actor="PARSER_WHATSAPP")
    test_db.commit()

    ok, entries, err = verify_chain(test_db)
    assert ok is True
    assert len(entries) == 3
    assert err is None
    assert entries[0]["prev_hash"] == GENESIS_HASH
    assert entries[1]["prev_hash"] == entries[0]["entry_hash"]
    assert entries[2]["prev_hash"] == entries[1]["entry_hash"]


def test_merkle_root_computation():
    hashes = [
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        "ca978112ca1bbdcafac231b39a23dc4da786eff8147c4e72b9807785afee48bb",
        "3e23e8160039594a33894f6564e1b1348bbd7a0088d42c4acb73eeaed59c009d",
    ]
    root = merkle_root_from_hashes(hashes)
    assert isinstance(root, str)
    assert len(root) == 64

    # Single leaf
    single_root = merkle_root_from_hashes([hashes[0]])
    assert single_root == hashes[0]


def test_ed25519_signing_and_verification():
    payload = b"PRAMAAN_EVIDENCE_MANIFEST_ROOT_HASH_9812938123"
    sig_b64, pub_b64 = sign_data(payload)
    
    assert verify_signature(payload, sig_b64, pub_b64) is True
    # Tampered payload fails
    assert verify_signature(payload + b"_TAMPERED", sig_b64, pub_b64) is False


def test_ingest_and_integrity_verification(test_db):
    raw_data = b"Hello, Investigator! Transaction ID 607211001234"
    stream = io.BytesIO(raw_data)
    
    res = ingest_file(test_db, stream, filename="evidence_sample.txt", source_type="whatsapp")
    assert res["exhibit_id"] == "EX-001"
    assert res["sha256"] == hash_bytes(raw_data)
    assert res["parse_status"] == "PENDING"

    # Verify integrity passes
    verification = verify_case_integrity(test_db)
    assert verification["intact"] is True
    assert verification["total_exhibits"] == 1
    assert verification["chain_intact"] is True
    assert verification["exhibits"][0]["status"] == "PASS"

