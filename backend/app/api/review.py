"""Human-in-the-Loop Review Queue and Decision Audit API endpoints."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, Body
from backend.app.db import get_db_connection
from backend.app.ai.run_records import build_explain_payload

router = APIRouter(prefix="/api/review", tags=["review"])


@router.get("/queue")
def get_review_queue(case_id: Optional[str] = Query(None)):
    """Retrieve risk-sorted items (claims, anomalies, leads) awaiting human adjudication."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()

        # 1. Claims awaiting approval (status = 'VERIFIED')
        cursor.execute("SELECT * FROM claims WHERE status = 'VERIFIED' ORDER BY rowid ASC;")
        claim_rows = cursor.fetchall()
        claims = []
        for r in claim_rows:
            d = dict(r)
            d["refs"] = json.loads(d.pop("source_refs_json", "[]"))
            d["quotes"] = json.loads(d.pop("quotes_json", "[]"))
            d["item_type"] = "claim"
            d["explain"] = build_explain_payload(
                conn,
                record_ids=d["refs"],
                ai_run_id=d.get("ai_run_id"),
                fallback_model=d.get("generated_by", "AI_DRAFT"),
                fallback_raw=d.get("text", ""),
                verifier_notes=d.get("verifier_notes"),
                item_type="claim",
                item_id=d["id"],
            )
            claims.append(d)

        # 2. Top Lead Edges awaiting approval
        cursor.execute("SELECT * FROM edges WHERE status = 'LEAD' ORDER BY strength DESC LIMIT 20;")
        edge_rows = cursor.fetchall()
        edges = []
        for r in edge_rows:
            d = dict(r)
            d["event_ids"] = json.loads(d.pop("event_ids_json", "[]"))
            d["item_type"] = "edge"
            edges.append(d)

        cursor.execute("SELECT COUNT(*) FROM claims WHERE status = 'APPROVED';")
        approved_claims_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM claims WHERE status != 'REMOVED';")
        total_claims_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM edges WHERE status = 'APPROVED';")
        approved_edges_count = cursor.fetchone()[0]
        cursor.execute("SELECT COUNT(*) FROM edges;")
        total_edges_count = cursor.fetchone()[0]

        return {
            "total_pending": len(claims) + len(edges),
            "approved_count": approved_claims_count + approved_edges_count,
            "total_reviewable": total_claims_count + total_edges_count,
            "approved_claims_count": approved_claims_count,
            "approved_edges_count": approved_edges_count,
            "claims": claims,
            "edges": edges,
        }
    finally:
        conn.close()


@router.post("/bulk")
def submit_bulk_review(
    items: List[Dict[str, str]] = Body(..., embed=True),
    decision: str = Body(..., embed=True),
    reviewer: str = Body("CHIEF_INVESTIGATOR", embed=True),
    note: Optional[str] = Body(None, embed=True),
    case_id: Optional[str] = Query(None),
):
    """Bulk approve or reject a group of claims or edges."""
    decision = decision.upper()
    if decision not in ("APPROVED", "REJECTED"):
        raise HTTPException(status_code=400, detail="Bulk decision must be APPROVED or REJECTED")

    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        ts_now = datetime.now(timezone.utc).isoformat()
        updated = 0
        for item in items:
            item_id = item.get("item_id")
            item_type = item.get("item_type", "claim")
            if not item_id:
                continue
            new_tier = "APPROVED" if decision == "APPROVED" else "LEAD"
            if item_type == "claim":
                cursor.execute(
                    "UPDATE claims SET status = ?, tier = ? WHERE id = ?;",
                    (decision, new_tier, item_id),
                )
            elif item_type == "edge":
                cursor.execute(
                    "UPDATE edges SET status = ?, tier = ? WHERE id = ?;",
                    (decision, new_tier, item_id),
                )
            if cursor.rowcount > 0:
                updated += 1
                cursor.execute(
                    """
                    INSERT INTO reviews (id, item_type, item_id, decision, reviewer, ts, note)
                    VALUES (?, ?, ?, ?, ?, ?, ?);
                    """,
                    (str(uuid.uuid4()), item_type, item_id, decision, reviewer, ts_now, note or "Bulk review"),
                )
        conn.commit()
        return {"status": "SUCCESS", "updated": updated, "decision": decision}
    finally:
        conn.close()


@router.post("/{item_id}")
def submit_review_decision(
    item_id: str,
    decision: str = Body(..., embed=True),  # APPROVED, REJECTED, EDIT
    item_type: str = Body("claim", embed=True),
    edited_text: Optional[str] = Body(None, embed=True),
    note: Optional[str] = Body(None, embed=True),
    reviewer: str = Body("CHIEF_INVESTIGATOR", embed=True),
    case_id: Optional[str] = Query(None),
):
    """Record an immutable human review decision. Only APPROVED items may enter the court report."""
    decision = decision.upper()
    if decision not in ("APPROVED", "REJECTED", "LEAD", "EDIT"):
        raise HTTPException(status_code=400, detail="Invalid decision")

    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        ts_now = datetime.now(timezone.utc).isoformat()
        rev_id = str(uuid.uuid4())

        if item_type == "claim":
            new_status = "APPROVED" if decision in ("APPROVED", "EDIT") else "REJECTED"
            new_tier = "APPROVED" if decision in ("APPROVED", "EDIT") else "LEAD"
            update_sql = "UPDATE claims SET status = ?, tier = ?"
            params = [new_status, new_tier]
            if edited_text:
                update_sql += ", text = ?"
                params.append(edited_text)
            update_sql += " WHERE id = ?;"
            params.append(item_id)

            cursor.execute(update_sql, params)
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Claim not found")

        elif item_type == "edge":
            new_status = "APPROVED" if decision == "APPROVED" else "REJECTED"
            new_tier = "APPROVED" if decision == "APPROVED" else "LEAD"
            cursor.execute(
                "UPDATE edges SET status = ?, tier = ? WHERE id = ?;",
                (new_status, new_tier, item_id),
            )
            if cursor.rowcount == 0:
                raise HTTPException(status_code=404, detail="Edge not found")

        # Insert audit trail into reviews table
        cursor.execute(
            """
            INSERT INTO reviews (id, item_type, item_id, decision, reviewer, ts, note)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (rev_id, item_type, item_id, decision, reviewer, ts_now, note),
        )
        conn.commit()

        return {
            "status": "SUCCESS",
            "review_id": rev_id,
            "item_id": item_id,
            "decision": decision,
            "recorded_at": ts_now,
        }
    finally:
        conn.close()

