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

from backend.app.config import EVIDENCE_STORE_DIR, DEFAULT_TIMEZONE, MAX_UPLOAD_SIZE_BYTES
from backend.app.integrity.hasher import hash_file
from backend.app.integrity.custody import append_custody_log, verify_chain
from backend.app.integrity.merkle import compute_case_merkle_root
from backend.app.integrity.signer import verify_signature
from backend.app.correlate.base import deterministic_id


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

    # Sanitise filename: extract pure basename to prevent directory traversal
    clean_filename = Path(filename).name
    if not clean_filename or clean_filename in (".", ".."):
        clean_filename = f"exhibit_{uuid.uuid4().hex[:8]}"

    # 1. Stream to a temporary file while enforcing max upload size
    tmp_path: Optional[Path] = None
    try:
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            bytes_written = 0
            while chunk := file_obj.read(1024 * 1024):
                bytes_written += len(chunk)
                if bytes_written > MAX_UPLOAD_SIZE_BYTES:
                    raise ValueError(
                        f"File size exceeds maximum allowed upload limit of {MAX_UPLOAD_SIZE_BYTES} bytes."
                    )
                tmp_file.write(chunk)

        size_bytes = tmp_path.stat().st_size
        sha256_hash = hash_file(tmp_path)

        # 2. Store in evidence_store/<sha256> (content-addressable immutable store)
        stored_path = EVIDENCE_STORE_DIR / sha256_hash
        needs_copy = not stored_path.exists()
        if not needs_copy:
            try:
                if hash_file(stored_path) != sha256_hash:
                    os.chmod(stored_path, 0o644)
                    needs_copy = True
            except Exception:
                needs_copy = True
        if needs_copy:
            shutil.copy2(tmp_path, stored_path)
            # Make read-only
            try:
                os.chmod(stored_path, 0o444)
            except Exception:
                pass

        # 3. Detect source_type via plugin registry if not explicitly provided
        if source_type is None:
            from backend.app.ingest.registry import registry
            source_type = registry.detect_source_type(stored_path, clean_filename)

        # Check if already ingested
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE sha256 = ?;", (sha256_hash,))
        existing = cursor.fetchone()
        if existing:
            # Duplicate upload detected: map to existing exhibit and log custody event
            existing_dict = dict(existing)
            append_custody_log(
                conn,
                action="DUPLICATE_INGEST_ATTEMPT",
                actor=actor,
                evidence_id=existing_dict["id"],
                details={
                    "attempted_filename": clean_filename,
                    "existing_exhibit_id": existing_dict["exhibit_id"],
                    "sha256": sha256_hash,
                    "size_bytes": size_bytes,
                    "note": "Same content already cataloged; re-using existing exhibit record",
                },
                ts_utc=ts_now,
            )
            conn.commit()
            return existing_dict

        # 4. Assign next exhibit ID & deterministic evidence ID & insert into evidence table
        exhibit_id = get_next_exhibit_id(conn)
        evidence_id = deterministic_id("evi", sha256_hash, exhibit_id)

        cursor.execute(
            """
            INSERT INTO evidence (id, exhibit_id, filename, sha256, size_bytes, source_type, received_at_utc, stored_path, parser, parse_status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING');
            """,
            (
                evidence_id,
                exhibit_id,
                clean_filename,
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
            details={"filename": clean_filename, "size_bytes": size_bytes, "source_type": source_type},
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
            "filename": clean_filename,
            "sha256": sha256_hash,
            "size_bytes": size_bytes,
            "source_type": source_type,
            "received_at_utc": ts_now,
            "stored_path": str(stored_path),
            "parse_status": "PENDING",
        }

    finally:
        # Guarantee cleanup of temporary file even if exceptions occur during ingest
        if tmp_path and tmp_path.exists():
            try:
                tmp_path.unlink()
            except Exception:
                pass


def verify_case_integrity(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Perform a rigorous, end-to-end verification of all stored files, Merkle root, custody chain, and manifest signatures."""
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

    # Manifest signature verification if manifests table has records
    cursor.execute("SELECT * FROM manifests ORDER BY rowid DESC LIMIT 1;")
    manifest_row = cursor.fetchone()
    manifest_verified: Optional[bool] = None
    manifest_error: Optional[str] = None

    if manifest_row:
        m_json = manifest_row["manifest_json"]
        sig = manifest_row["signature_b64"]
        pub = manifest_row["public_key_b64"]
        stored_merkle = manifest_row["merkle_root"]

        sig_valid = verify_signature(m_json.encode("utf-8"), sig, pub)
        if not sig_valid:
            manifest_verified = False
            manifest_error = "Ed25519 signature verification failed on manifest"
        elif stored_merkle != merkle_root:
            manifest_verified = False
            manifest_error = f"Manifest Merkle root mismatch: recorded {stored_merkle[:8]}..., recomputed {merkle_root[:8]}..."
        else:
            manifest_verified = True

    is_intact = all_files_pass and chain_ok and (manifest_verified is not False)

    return {
        "intact": is_intact,
        "total_exhibits": len(evidence_rows),
        "merkle_root": merkle_root,
        "chain_intact": chain_ok,
        "chain_error": chain_err,
        "failed_exhibit": failing_exhibit if not all_files_pass else None,
        "manifest_verified": manifest_verified,
        "manifest_error": manifest_error,
        "exhibits": exhibits_result,
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
    }
