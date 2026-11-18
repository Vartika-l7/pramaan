"""Chronological Event Store and Source Viewer API endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query
from backend.app.db import get_db_connection

router = APIRouter(prefix="/api/events", tags=["events"])


@router.get("")
def list_events(
    case_id: Optional[str] = Query(None),
    from_ts: Optional[str] = Query(None, alias="from"),
    to_ts: Optional[str] = Query(None, alias="to"),
    source: Optional[str] = Query(None),
    actor: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
    limit: int = Query(500, ge=1, le=5000),
):
    """Retrieve the unified chronological event sequence with flexible filtering."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        query = ["SELECT e.*, ev.exhibit_id, ev.filename FROM events e JOIN evidence ev ON e.evidence_id = ev.id WHERE 1=1"]
        params = []

        if from_ts:
            query.append("AND e.ts_utc >= ?")
            params.append(from_ts)
        if to_ts:
            query.append("AND e.ts_utc <= ?")
            params.append(to_ts)
        if source:
            query.append("AND e.source_type = ?")
            params.append(source)
        if actor:
            query.append("AND (e.actor LIKE ? OR e.counterparty LIKE ?)")
            params.extend([f"%{actor}%", f"%{actor}%"])
        if kind:
            query.append("AND e.kind = ?")
            params.append(kind)

        query.append("ORDER BY e.ts_utc ASC LIMIT ?")
        params.append(limit)

        cursor.execute(" ".join(query), params)
        rows = cursor.fetchall()

        results = []
        for r in rows:
            d = dict(r)
            try:
                d["ref"] = json.loads(d.pop("ref_json"))
            except Exception:
                d["ref"] = {}
            results.append(d)

        return results
    finally:
        conn.close()


@router.get("/{event_id}/source")
def get_event_source_context(event_id: str, case_id: Optional[str] = Query(None)):
    """Source Viewer: returns the exact record, 5 lines context before/after, evidence SHA-256, and custody log."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.*, ev.exhibit_id, ev.filename, ev.sha256, ev.stored_path, ev.parser
            FROM events e
            JOIN evidence ev ON e.evidence_id = ev.id
            WHERE e.id = ?;
            """,
            (event_id,),
        )
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Event not found")

        event_data = dict(row)
        ref = json.loads(event_data.pop("ref_json", "{}"))
        stored_path = Path(event_data["stored_path"])

        context_before: List[str] = []
        target_lines: List[str] = []
        context_after: List[str] = []

        if stored_path.exists() and event_data["source_type"] in ("whatsapp", "calllog", "bank_csv"):
            try:
                with open(stored_path, "r", encoding="utf-8", errors="replace") as f:
                    all_lines = f.readlines()

                line_start = ref.get("line_start", ref.get("row_index", 1))
                line_end = ref.get("line_end", line_start)

                start_idx = max(0, line_start - 1)
                end_idx = min(len(all_lines), line_end)

                before_start = max(0, start_idx - 5)
                context_before = [l.rstrip("\r\n") for l in all_lines[before_start:start_idx]]
                target_lines = [l.rstrip("\r\n") for l in all_lines[start_idx:end_idx]]
                after_end = min(len(all_lines), end_idx + 5)
                context_after = [l.rstrip("\r\n") for l in all_lines[end_idx:after_end]]
            except Exception:
                target_lines = [event_data.get("text") or ""]
        else:
            target_lines = [event_data.get("text") or ""]

        # Fetch custody events for the parent exhibit
        cursor.execute(
            "SELECT seq, ts_utc, actor, action, details_json, prev_hash, entry_hash FROM custody_log WHERE evidence_id = ? ORDER BY seq ASC;",
            (event_data["evidence_id"],),
        )
        custody_rows = [dict(c) for c in cursor.fetchall()]

        return {
            "event_id": event_id,
            "exhibit_id": event_data["exhibit_id"],
            "filename": event_data["filename"],
            "sha256": event_data["sha256"],
            "parser": event_data["parser"],
            "source_type": event_data["source_type"],
            "ts_utc": event_data["ts_utc"],
            "ts_original": event_data["ts_original"],
            "tz_assumed": event_data["tz_assumed"],
            "kind": event_data["kind"],
            "actor": event_data["actor"],
            "ref": ref,
            "context_before": context_before,
            "target_lines": target_lines,
            "context_after": context_after,
            "custody_events": custody_rows,
        }
    finally:
        conn.close()

