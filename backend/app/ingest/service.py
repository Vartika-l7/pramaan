"""Evidence Ingest and Integrity Verification Service for PRAMAAN."""

from __future__ import annotations

import os
import shutil
import sqlite3
import tempfile
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import BinaryIO, Dict, Any, List, Optional, Tuple

from backend.app.config import EVIDENCE_STORE_DIR, DEFAULT_TIMEZONE
from backend.app.integrity.hasher import hash_file
from backend.app.integrity.custody import append_custody_log, verify_chain
from backend.app.integrity.merkle import compute_case_merkle_root


def get_next_exhibit_id(conn: sqlite3.Connection) -> str:
    """Generate the next deterministic exhibit ID (e.g. EX-001, EX-002)."""
    cursor = conn.cursor()
    cursor.execute("SELECT exhibit_id FROM evidence ORDER BY rowid DESC LIMIT 1;")
    row = cursor.fetchone()
    if not row:
        return "EX-001"
    last_id = row["exhibit_id"]
    try:
        num = int(last_id.split("-")[1])
        return f"EX-{num + 1:03d}"
    except Exception:
        return f"EX-{uuid.uuid4().hex[:6].upper()}"


def ingest_file(
    conn: sqlite3.Connection,
    file_obj: BinaryIO,
    filename: str,
    source_type: Optional[str] = None,
    actor: str = "INVESTIGATOR",
) -> Dict[str, Any]:
    """Ingest a raw evidence file into the secure, read-only content-addressable evidence store."""
    EVIDENCE_STORE_DIR.mkdir(parents=True, exist_ok=True)
    ts_now = datetime.now(timezone.utc).isoformat()

    # 1. Stream to a temporary file while hashing in 1MB chunks
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_path = Path(tmp_file.name)
        shutil.copyfileobj(file_obj, tmp_file)

    try:
        sha256_hash = hash_file(tmp_path)
        size_bytes = tmp_path.stat().st_size

        # 2. Store in evidence_store/<sha256>
        stored_path = EVIDENCE_STORE_DIR / sha256_hash
        if not stored_path.exists():
            shutil.copy2(tmp_path, stored_path)
            # Make read-only
            try:
                os.chmod(stored_path, 0o444)
            except Exception:
                pass

        # 3. Detect or assign source_type
        lower_name = filename.lower()
        if source_type is None:
            if lower_name.endswith(".txt"):
                source_type = "whatsapp"
            elif lower_name.endswith(".pdf"):
                source_type = "bank_pdf"
            elif lower_name.endswith(".csv"):
                if "call" in lower_name:
                    source_type = "calllog"
                else:
                    source_type = "bank_csv"
            elif lower_name.endswith((".png", ".jpg", ".jpeg")):
                source_type = "image"
            else:
                source_type = "unknown"

        # Check if already ingested
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE sha256 = ?;", (sha256_hash,))
        existing = cursor.fetchone()
        if existing:
            return dict(existing)

        # 4. Assign next exhibit ID & insert into evidence table
        exhibit_id = get_next_exhibit_id(conn)
        evidence_id = str(uuid.uuid4())

        cursor.execute(
            """
            INSERT INTO evidence (id, exhibit_id, filename, sha256, size_bytes, source_type, received_at_utc, stored_path, parser, parse_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING');
            """,
            (
                evidence_id,
                exhibit_id,
                filename,
                sha256_hash,
                size_bytes,
                source_type,
                ts_now,
                str(stored_path),
                source_type,
            ),
        )

        # 5. Append custody log records: RECEIVED, HASHED, and timezone assumption
        append_custody_log(
            conn,
            action="RECEIVED",
            actor=actor,
            evidence_id=evidence_id,
            details={"filename": filename, "size_bytes": size_bytes, "source_type": source_type},
            ts_utc=ts_now,
        )

        append_custody_log(
            conn,
            action="HASHED",
            actor="SYSTEM",
            evidence_id=evidence_id,
            details={"sha256": sha256_hash, "exhibit_id": exhibit_id, "algorithm": "SHA-256"},
            ts_utc=ts_now,
        )

        append_custody_log(
            conn,
            action="TIMEZONE_ASSUMED",
            actor="SYSTEM",
            evidence_id=evidence_id,
            details={"tz_assumed": DEFAULT_TIMEZONE, "reason": "Standard Indian evidence ingest assumption"},
            ts_utc=ts_now,
        )

        conn.commit()

        return {
            "id": evidence_id,
            "exhibit_id": exhibit_id,
            "filename": filename,
            "sha256": sha256_hash,
            "size_bytes": size_bytes,
            "source_type": source_type,
            "received_at_utc": ts_now,
            "stored_path": str(stored_path),
            "parse_status": "PENDING",
        }

    finally:
        if tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def verify_case_integrity(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Perform a rigorous, end-to-end verification of all stored files, Merkle root, and custody chain."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evidence ORDER BY exhibit_id ASC;")
    evidence_rows = cursor.fetchall()

    exhibits_result = []
    all_files_pass = True
    failing_exhibit = None

    for row in evidence_rows:
        exhibit_id = row["exhibit_id"]
        expected_sha = row["sha256"]
        stored_path = Path(row["stored_path"])

        if not stored_path.exists():
            all_files_pass = False
            if failing_exhibit is None:
                failing_exhibit = exhibit_id
            exhibits_result.append({
                "exhibit_id": exhibit_id,
                "filename": row["filename"],
                "sha256": expected_sha,
                "status": "FAIL",
                "reason": f"Stored evidence file missing at {stored_path}",
            })
            continue

        try:
            recomputed_sha = hash_file(stored_path)
            if recomputed_sha != expected_sha:
                all_files_pass = False
                if failing_exhibit is None:
                    failing_exhibit = exhibit_id
                exhibits_result.append({
                    "exhibit_id": exhibit_id,
                    "filename": row["filename"],
                    "sha256": expected_sha,
                    "status": "FAIL",
                    "reason": f"Hash mismatch: expected {expected_sha[:8]}..., found {recomputed_sha[:8]}...",
                })
            else:
                exhibits_result.append({
                    "exhibit_id": exhibit_id,
                    "filename": row["filename"],
                    "sha256": expected_sha,
                    "status": "PASS",
                    "reason": "SHA-256 verified identical to initial custody record",
                })
        except Exception as e:
            all_files_pass = False
            if failing_exhibit is None:
                failing_exhibit = exhibit_id
            exhibits_result.append({
                "exhibit_id": exhibit_id,
                "filename": row["filename"],
                "sha256": expected_sha,
                "status": "FAIL",
                "reason": f"Read error: {str(e)}",
            })

    chain_ok, _, chain_err = verify_chain(conn)
    merkle_root, _ = compute_case_merkle_root(conn)

    is_intact = all_files_pass and chain_ok

    return {
        "intact": is_intact,
        "total_exhibits": len(evidence_rows),
        "merkle_root": merkle_root,
        "chain_intact": chain_ok,
        "chain_error": chain_err,
        "failed_exhibit": failing_exhibit if not all_files_pass else None,
        "exhibits": exhibits_result,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
    }

