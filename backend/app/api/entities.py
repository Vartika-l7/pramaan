"""Entity and Mention Exploration API endpoints."""

from __future__ import annotations

import json
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Query
from backend.app.db import get_db_connection

router = APIRouter(prefix="/api/entities", tags=["entities"])


@router.get("")
def list_entities(
    case_id: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    q: Optional[str] = Query(None),
):
    """List extracted entities with their mention counts across all exhibits."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        query = [
            """
            SELECT e.*, COUNT(m.id) as mention_count
            FROM entities e
            LEFT JOIN mentions m ON e.id = m.entity_id
            WHERE 1=1
            """
        ]
        params = []

        if type:
            query.append("AND e.type = ?")
            params.append(type.upper())
        if q:
            query.append("AND (e.value_norm LIKE ? OR e.display LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])

        query.append("GROUP BY e.id ORDER BY mention_count DESC, e.display ASC;")

        cursor.execute(" ".join(query), params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{entity_id}")
def get_entity_detail(entity_id: str, case_id: Optional[str] = Query(None)):
    """Retrieve full entity profile along with all mentions and highlighting offsets across evidence."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM entities WHERE id = ?;", (entity_id,))
        ent = cursor.fetchone()
        if not ent:
            raise HTTPException(status_code=404, detail="Entity not found")

        cursor.execute(
            """
            SELECT m.*, ev.text, ev.ts_utc, ev.source_type, evi.exhibit_id, evi.filename, evi.sha256
            FROM mentions m
            JOIN events ev ON m.event_id = ev.id
            JOIN evidence evi ON ev.evidence_id = evi.id
            WHERE m.entity_id = ?
            ORDER BY ev.ts_utc ASC;
            """,
            (entity_id,),
        )
        mention_rows = cursor.fetchall()

        result = dict(ent)
        result["mentions"] = [dict(m) for m in mention_rows]
        return result
    finally:
        conn.close()

