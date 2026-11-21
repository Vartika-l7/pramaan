"""Tamper-evident AI Run Record storage and Explainability helpers (Phase 4 Part C)."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from backend.app.integrity.custody import append_custody_log, canonical_json


def _compute_run_sha256(payload: Dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def record_ai_run(
    conn: sqlite3.Connection,
    *,
    task: str,
    model_name: str,
    model_version: str,
    parameters: Dict[str, Any],
    prompt: str,
    input_record_ids: List[str],
    raw_output: str,
    verifier_result: Dict[str, Any],
    ts_utc: Optional[str] = None,
    run_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Persist an AI run record and append its SHA-256 to the custody log."""
    ts = ts_utc or datetime.now(timezone.utc).isoformat()
    rid = run_id or f"airun_{hashlib.sha256(f'{task}|{ts}|{prompt[:120]}'.encode('utf-8')).hexdigest()[:16]}"

    canonical_payload = {
        "id": rid,
        "ts_utc": ts,
        "task": task,
        "model_name": model_name,
        "model_version": model_version,
        "parameters": parameters,
        "prompt": prompt,
        "input_record_ids": list(input_record_ids),
        "raw_output": raw_output,
        "verifier_result": verifier_result,
    }
    record_sha256 = _compute_run_sha256(canonical_payload)

    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT OR REPLACE INTO ai_runs
        (id, ts_utc, task, model_name, model_version, parameters_json, prompt, input_record_ids_json, raw_output, verifier_result_json, record_sha256)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        (
            rid,
            ts,
            task,
            model_name,
            model_version,
            json.dumps(parameters, ensure_ascii=True),
            prompt,
            json.dumps(list(input_record_ids), ensure_ascii=True),
            raw_output,
            json.dumps(verifier_result, ensure_ascii=True),
            record_sha256,
        ),
    )

    append_custody_log(
        conn,
        action="AI_RUN_RECORDED",
        actor=model_name,
        details={
            "ai_run_id": rid,
            "task": task,
            "model_name": model_name,
            "model_version": model_version,
            "record_sha256": record_sha256,
        },
        ts_utc=ts,
    )
    conn.commit()
    return {
        "id": rid,
        "ts_utc": ts,
        "task": task,
        "model_name": model_name,
        "model_version": model_version,
        "parameters": parameters,
        "prompt": prompt,
        "input_record_ids": list(input_record_ids),
        "raw_output": raw_output,
        "verifier_result": verifier_result,
        "record_sha256": record_sha256,
    }


def update_ai_run_verifier_result(
    conn: sqlite3.Connection,
    ai_run_id: str,
    verifier_result: Dict[str, Any],
) -> None:
    """Update the verifier result on an AI run and log verification hash to custody log."""
    if not ai_run_id:
        return
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM ai_runs WHERE id = ?;", (ai_run_id,))
    row = cursor.fetchone()
    if not row:
        return

    ver_json = json.dumps(verifier_result, ensure_ascii=True)
    ver_sha256 = hashlib.sha256(ver_json.encode("utf-8")).hexdigest()
    cursor.execute(
        "UPDATE ai_runs SET verifier_result_json = ? WHERE id = ?;",
        (ver_json, ai_run_id),
    )
    append_custody_log(
        conn,
        action="AI_VERIFIER_RECORDED",
        actor="CLAIM_VERIFIER",
        details={
            "ai_run_id": ai_run_id,
            "verifier_result_sha256": ver_sha256,
            "verified_count": verifier_result.get("verified_count", 0),
            "removed_count": verifier_result.get("removed_count", 0),
        },
    )
    conn.commit()


def lookup_exhibits_for_ids(conn: sqlite3.Connection, record_ids: List[str]) -> List[Dict[str, str]]:
    """Resolve event/evidence/anomaly IDs into clickable exhibit descriptors."""
    if not record_ids:
        return []
    cursor = conn.cursor()
    seen = set()
    exhibits: List[Dict[str, str]] = []
    ph = ",".join(["?"] * len(record_ids))

    cursor.execute(
        f"""
        SELECT ev.id AS record_id, evi.exhibit_id, evi.filename
        FROM events ev
        JOIN evidence evi ON ev.evidence_id = evi.id
        WHERE ev.id IN ({ph});
        """,
        record_ids,
    )
    for r in cursor.fetchall():
        key = (r["exhibit_id"], r["record_id"])
        if key not in seen:
            seen.add(key)
            exhibits.append({
                "exhibit_id": r["exhibit_id"],
                "event_id": r["record_id"],
                "filename": r["filename"],
            })

    cursor.execute(
        f"""
        SELECT a.id AS record_id, evi.exhibit_id, evi.filename, a.event_ids_json
        FROM anomalies a
        JOIN evidence evi ON a.evidence_id = evi.id
        WHERE a.id IN ({ph});
        """,
        record_ids,
    )
    for r in cursor.fetchall():
        try:
            eids = json.loads(r["event_ids_json"])
        except Exception:
            eids = []
        ev_id = eids[0] if eids else None
        key = (r["exhibit_id"], ev_id or r["record_id"])
        if key not in seen:
            seen.add(key)
            exhibits.append({
                "exhibit_id": r["exhibit_id"],
                "event_id": ev_id or "",
                "filename": r["filename"],
            })

    return exhibits


def get_approval_info(conn: sqlite3.Connection, item_type: str, item_id: str) -> Dict[str, Any]:
    """Return reviewer and timestamp if approved, else 'not yet approved'."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT decision, reviewer, ts, note
        FROM reviews
        WHERE item_type = ? AND item_id = ?
        ORDER BY rowid DESC LIMIT 1;
        """,
        (item_type, item_id),
    )
    row = cursor.fetchone()
    if row and row["decision"] in ("APPROVED", "EDIT"):
        return {
            "approved": True,
            "decision": row["decision"],
            "reviewer": row["reviewer"],
            "ts": row["ts"],
            "label": f"{row['reviewer']} at {row['ts']}",
        }
    if row and row["decision"] == "REJECTED":
        return {
            "approved": False,
            "decision": row["decision"],
            "reviewer": row["reviewer"],
            "ts": row["ts"],
            "label": f"Rejected by {row['reviewer']} at {row['ts']}",
        }
    return {
        "approved": False,
        "decision": None,
        "reviewer": None,
        "ts": None,
        "label": "not yet approved",
    }


def build_explain_payload(
    conn: sqlite3.Connection,
    *,
    record_ids: List[str],
    ai_run_id: Optional[str] = None,
    fallback_model: str = "DeterministicProvider",
    fallback_raw: str = "",
    kept_items: Optional[List[Dict[str, Any]]] = None,
    removed_items: Optional[List[Dict[str, Any]]] = None,
    verifier_notes: Optional[str] = None,
    item_type: str = "claim",
    item_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Construct the 4-part Explain panel payload required by Phase 4 Part C."""
    run_row = None
    if ai_run_id:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM ai_runs WHERE id = ?;", (ai_run_id,))
        run_row = cursor.fetchone()

    saw_ids = list(record_ids)
    if run_row:
        try:
            run_ids = json.loads(run_row["input_record_ids_json"])
            if not saw_ids:
                saw_ids = run_ids
        except Exception:
            pass

    exhibits = lookup_exhibits_for_ids(conn, saw_ids)

    if run_row:
        try:
            params = json.loads(run_row["parameters_json"])
        except Exception:
            params = {"temperature": 0, "seed": 42}
        try:
            ver_res = json.loads(run_row["verifier_result_json"])
        except Exception:
            ver_res = {}
        what_model_said = {
            "ai_run_id": run_row["id"],
            "record_sha256": run_row["record_sha256"],
            "model_name": run_row["model_name"],
            "model_version": run_row["model_version"],
            "parameters": params,
            "raw_output": run_row["raw_output"],
            "ts_utc": run_row["ts_utc"],
        }
    else:
        ver_res = {}
        what_model_said = {
            "ai_run_id": ai_run_id,
            "record_sha256": None,
            "model_name": fallback_model,
            "model_version": "deterministic-v1",
            "parameters": {"temperature": 0, "seed": 42},
            "raw_output": fallback_raw,
            "ts_utc": None,
        }

    kept = kept_items if kept_items is not None else ver_res.get("verified_claims", [])
    removed = removed_items if removed_items is not None else ver_res.get("removed_claims", [])

    approval = (
        get_approval_info(conn, item_type, item_id)
        if item_id
        else {"approved": False, "decision": None, "reviewer": None, "ts": None, "label": "not yet approved"}
    )

    return {
        "what_model_saw": {
            "record_ids": saw_ids,
            "exhibits": exhibits,
        },
        "what_model_said": what_model_said,
        "what_verifier_kept_and_removed": {
            "notes": verifier_notes,
            "kept": kept,
            "removed": removed,
        },
        "who_approved": approval,
    }
