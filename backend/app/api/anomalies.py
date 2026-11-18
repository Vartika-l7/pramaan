"""Forensic Anomalies Exploration API endpoints."""

from __future__ import annotations

import json
from typing import Optional, List
from fastapi import APIRouter, Query
from backend.app.db import get_db_connection

router = APIRouter(prefix="/api/anomalies", tags=["anomalies"])


@router.get("")
def list_anomalies(
    case_id: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    kind: Optional[str] = Query(None),
):
    """List detected forensic anomalies (chat gaps, edited images, broken balances, funnel patterns)."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        query = [
            """
            SELECT a.*, ev.exhibit_id, ev.filename
            FROM anomalies a
            JOIN evidence ev ON a.evidence_id = ev.id
            WHERE 1=1
            """
        ]
        params = []

        if severity:
            query.append("AND a.severity = ?")
            params.append(severity.upper())
        if kind:
            query.append("AND a.kind = ?")
            params.append(kind)

        query.append("ORDER BY CASE a.severity WHEN 'HIGH' THEN 1 WHEN 'MEDIUM' THEN 2 ELSE 3 END, a.rowid ASC;")

        cursor.execute(" ".join(query), params)
        rows = cursor.fetchall()

        results = []
        for r in rows:
            d = dict(r)
            try:
                d["event_ids"] = json.loads(d.pop("event_ids_json", "[]"))
            except Exception:
                d["event_ids"] = []
            try:
                d["detail"] = json.loads(d.pop("detail_json", "{}"))
            except Exception:
                d["detail"] = {}
            results.append(d)

        return results
    finally:
        conn.close()

