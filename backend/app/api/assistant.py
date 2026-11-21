"""Investigator Assistant API endpoints (Phase 2C)."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, HTTPException, Query
from fastapi.responses import StreamingResponse

from backend.app.db import get_db_connection
from backend.app.ai.run_records import record_ai_run, build_explain_payload
from backend.app.assistant.engine import ask_assistant
from backend.app.assistant.tools import (
    get_starter_chips,
    suggest_next_leads,
    draft_case_diary,
)
from backend.app.verify.challenger import run_challenger_analysis
from backend.app.verify.claim_verifier import verify_claims

router = APIRouter(prefix="/api/assistant", tags=["assistant"])


@router.post("/ask")
def assistant_ask(
    question: str = Body(..., embed=True),
    session_id: str = Body("default", embed=True),
    focus_entity: Optional[str] = Body(None, embed=True),
    language: str = Body("en", embed=True),
    case_id: Optional[str] = Query(None),
):
    conn = get_db_connection(case_id)
    try:
        return ask_assistant(conn, question, session_id=session_id, focus_entity=focus_entity, language=language)
    finally:
        conn.close()


@router.get("/stream")
async def assistant_stream(
    question: str = Query(...),
    session_id: str = Query("default"),
    focus_entity: Optional[str] = Query(None),
    language: str = Query("en"),
    case_id: Optional[str] = Query(None),
):
    async def event_gen():
        yield f"data: {json.dumps({'stage': 'PLANNING', 'message': 'Planning read-only evidence queries...'})}\n\n"
        conn = get_db_connection(case_id)
        try:
            res = ask_assistant(conn, question, session_id=session_id, focus_entity=focus_entity, language=language)
        finally:
            conn.close()
        yield f"data: {json.dumps({'stage': 'DONE', 'result': res})}\n\n"

    return StreamingResponse(event_gen(), media_type="text/event-stream")


@router.get("/starters")
def assistant_starters(case_id: Optional[str] = Query(None)):
    conn = get_db_connection(case_id)
    try:
        return {"starters": get_starter_chips(conn)}
    finally:
        conn.close()


@router.get("/leads")
def assistant_leads(case_id: Optional[str] = Query(None)):
    conn = get_db_connection(case_id)
    try:
        leads = suggest_next_leads(conn)
        all_refs = [ref for l in leads for ref in l.get("evidence_refs", [])]
        run_rec = record_ai_run(
            conn,
            task="suggest_next_leads",
            model_name="DeterministicLeadSuggester",
            model_version="deterministic-v1",
            parameters={"temperature": 0, "seed": 42},
            prompt="Suggest next investigative leads from unresolved anomalies.",
            input_record_ids=all_refs,
            raw_output=json.dumps(leads, ensure_ascii=False),
            verifier_result={"leads_count": len(leads), "status": "LEAD_ONLY"},
        )
        for idx, l in enumerate(leads):
            l["id"] = l.get("id") or f"LEAD-{idx + 1:03d}"
            l["explain"] = build_explain_payload(
                conn,
                record_ids=l.get("evidence_refs", []),
                ai_run_id=run_rec["id"],
                fallback_model="DeterministicLeadSuggester",
                fallback_raw=l.get("reason", ""),
                kept_items=[{"id": l["id"], "text": l["title"]}],
                removed_items=[],
                verifier_notes="Investigative LEAD only; requires corroboration and human approval.",
                item_type="lead",
                item_id=l["id"],
            )
        return {"leads": leads, "ai_run_id": run_rec["id"], "record_sha256": run_rec["record_sha256"]}
    finally:
        conn.close()


@router.get("/challenge")
def assistant_challenge(case_id: Optional[str] = Query(None)):
    conn = get_db_connection(case_id)
    try:
        return run_challenger_analysis(conn)
    finally:
        conn.close()


@router.get("/diary")
def assistant_diary(
    from_ts: Optional[str] = Query(None),
    to_ts: Optional[str] = Query(None),
    case_id: Optional[str] = Query(None),
):
    conn = get_db_connection(case_id)
    try:
        return {"entries": draft_case_diary(conn, from_ts=from_ts, to_ts=to_ts)}
    finally:
        conn.close()


@router.post("/promote")
def promote_to_review_queue(
    text: str = Body(..., embed=True),
    refs: List[str] = Body(default=[], embed=True),
    kind: str = Body("assistant_finding", embed=True),
    ai_run_id: Optional[str] = Body(None, embed=True),
    case_id: Optional[str] = Query(None),
):
    """Verify an assistant answer against Rules V1-V5 and add it to the Review Queue."""
    if not refs:
        raise HTTPException(
            status_code=400,
            detail="Cannot add to review queue without cited source record IDs (Rule V4: No source, no claim).",
        )
    conn = get_db_connection(case_id)
    try:
        cid = str(uuid.uuid4())
        ver = verify_claims(
            conn,
            [
                {
                    "id": cid,
                    "text": text,
                    "kind": kind,
                    "refs": refs,
                    "quotes": [],
                    "generated_by": "INVESTIGATOR_ASSISTANT",
                    "ai_run_id": ai_run_id,
                }
            ],
        )
        if ver["verified_count"] == 0:
            reason = ver["removed_claims"][0]["reason"] if ver["removed_claims"] else "Failed deterministic verification"
            raise HTTPException(status_code=400, detail=reason)
        return {"status": "VERIFIED", "claim_id": cid}
    finally:
        conn.close()
