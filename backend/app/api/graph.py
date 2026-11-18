"""Knowledge Graph and 'Why this Link' API endpoints."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from backend.app.db import get_db_connection
from backend.app.correlate.graph import get_cytoscape_graph

router = APIRouter(prefix="/api/graph", tags=["graph"])


@router.get("")
def get_graph(
    case_id: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    tier: Optional[str] = Query(None),
    min_strength: float = Query(0.0, ge=0.0, le=1.0),
):
    """Retrieve full knowledge graph nodes and edges formatted for Cytoscape.js."""
    conn = get_db_connection(case_id)
    try:
        return get_cytoscape_graph(conn, type_filter=type, tier_filter=tier, min_strength=min_strength)
    finally:
        conn.close()


@router.get("/edges/{edge_id}")
def get_edge_explanation(edge_id: str, case_id: Optional[str] = Query(None)):
    """'Why this Link' panel: provides reasoning, basis, strength, tier, and supporting exhibit chips."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM edges WHERE id = ?;", (edge_id,))
        edge = cursor.fetchone()
        if not edge:
            raise HTTPException(status_code=404, detail="Edge not found")

        edge_data = dict(edge)
        try:
            event_ids = json.loads(edge_data.pop("event_ids_json", "[]"))
        except Exception:
            event_ids = []

        supporting_events = []
        if event_ids:
            placeholders = ",".join(["?"] * len(event_ids))
            cursor.execute(
                f"""
                SELECT ev.id, ev.ts_utc, ev.text, ev.kind, evi.exhibit_id, evi.filename, evi.sha256
                FROM events ev
                JOIN evidence evi ON ev.evidence_id = evi.id
                WHERE ev.id IN ({placeholders});
                """,
                event_ids,
            )
            supporting_events = [dict(r) for r in cursor.fetchall()]

        edge_data["supporting_events"] = supporting_events
        return edge_data
    finally:
        conn.close()


@router.post("/edges/{edge_id}/review")
def review_edge(
    edge_id: str,
    decision: str = Body(..., embed=True),  # APPROVED or REJECTED
    note: Optional[str] = Body(None, embed=True),
    reviewer: str = Body("INVESTIGATOR", embed=True),
    case_id: Optional[str] = Query(None),
):
    """Human-in-the-loop review: promote a LEAD edge to APPROVED or REJECTED."""
    decision = decision.upper()
    if decision not in ("APPROVED", "REJECTED", "LEAD"):
        raise HTTPException(status_code=400, detail="Decision must be APPROVED, REJECTED, or LEAD")

    tier = "APPROVED" if decision == "APPROVED" else "LEAD"
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "UPDATE edges SET status = ?, tier = ? WHERE id = ?;",
            (decision, tier, edge_id),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Edge not found")

        # Record review
        import uuid
        rev_id = str(uuid.uuid4())
        ts_now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO reviews (id, item_type, item_id, decision, reviewer, ts, note)
            VALUES (?, 'edge', ?, ?, ?, ?, ?);
            """,
            (rev_id, edge_id, decision, reviewer, ts_now, note),
        )
        conn.commit()
        return {"status": "SUCCESS", "edge_id": edge_id, "decision": decision, "tier": tier}
    finally:
        conn.close()

