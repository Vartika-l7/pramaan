"""Hash-chained, tamper-evident custody logging for PRAMAAN."""

from __future__ import annotations

import json
import hashlib
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

GENESIS_HASH = "0" * 64


def canonical_json(data: Any) -> str:
    """Return deterministic canonical JSON representation."""
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def get_latest_custody_hash(conn: sqlite3.Connection) -> str:
    """Retrieve the entry_hash of the latest custody log record, or GENESIS_HASH if empty."""
    cursor = conn.cursor()
    cursor.execute("SELECT entry_hash FROM custody_log ORDER BY seq DESC LIMIT 1;")
    row = cursor.fetchone()
    if row and row["entry_hash"]:
        return row["entry_hash"]
    return GENESIS_HASH


def append_custody_log(
    conn: sqlite3.Connection,
    action: str,
    actor: str = "SYSTEM",
    evidence_id: Optional[str] = None,
    details: Optional[Dict[str, Any]] = None,
    ts_utc: Optional[str] = None,
) -> Dict[str, Any]:
    """Append an immutable, hash-chained entry to the custody log."""
    if ts_utc is None:
        ts_utc = datetime.now(timezone.utc).isoformat()
    if details is None:
        details = {}

    prev_hash = get_latest_custody_hash(conn)
    cursor = conn.cursor()
    
    # Calculate next sequence number
    cursor.execute("SELECT COALESCE(MAX(seq), 0) + 1 AS next_seq FROM custody_log;")
    next_seq = cursor.fetchone()["next_seq"]

    entry_payload = {
        "seq": next_seq,
        "ts_utc": ts_utc,
        "actor": actor,
        "action": action,
        "evidence_id": evidence_id,
        "details": details,
    }
    
    payload_str = prev_hash + canonical_json(entry_payload)
    entry_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    cursor.execute(
        """
        INSERT INTO custody_log (seq, ts_utc, actor, action, evidence_id, details_json, prev_hash, entry_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            next_seq,
            ts_utc,
            actor,
            action,
            evidence_id,
            json.dumps(details),
            prev_hash,
            entry_hash,
        ),
    )
    return {
        "seq": next_seq,
        "ts_utc": ts_utc,
        "actor": actor,
        "action": action,
        "evidence_id": evidence_id,
        "prev_hash": prev_hash,
        "entry_hash": entry_hash,
    }


def verify_chain(conn: sqlite3.Connection) -> Tuple[bool, List[Dict[str, Any]], Optional[str]]:
    """Verify the entire custody log hash chain from genesis to head."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM custody_log ORDER BY seq ASC;")
    rows = cursor.fetchall()

    if not rows:
        return True, [], None

    expected_prev = GENESIS_HASH
    verified_entries = []

    for row in rows:
        seq = row["seq"]
        ts_utc = row["ts_utc"]
        actor = row["actor"]
        action = row["action"]
        evidence_id = row["evidence_id"]
        details_json = row["details_json"]
        prev_hash = row["prev_hash"]
        entry_hash = row["entry_hash"]

        try:
            details = json.loads(details_json) if details_json else {}
        except Exception:
            details = {}

        # 1. Check prev_hash linkage
        if prev_hash != expected_prev:
            err_msg = f"Chain link broken at seq {seq}: expected prev_hash {expected_prev}, found {prev_hash}"
            return False, verified_entries, err_msg

        # 2. Recompute entry_hash
        entry_payload = {
            "seq": seq,
            "ts_utc": ts_utc,
            "actor": actor,
            "action": action,
            "evidence_id": evidence_id,
            "details": details,
        }
        recomputed = hashlib.sha256((prev_hash + canonical_json(entry_payload)).encode("utf-8")).hexdigest()
        if recomputed != entry_hash:
            err_msg = f"Hash integrity failure at seq {seq}: expected {recomputed}, recorded {entry_hash}"
            return False, verified_entries, err_msg

        verified_entries.append(dict(row))
        expected_prev = entry_hash

    return True, verified_entries, None

