"""Investigator Assistant API endpoints (Phase 2C)."""

from __future__ import annotations

import json
import uuid
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Body, Query
from fastapi.responses import StreamingResponse

from backend.app.db import get_db_connection
from backend.app.assistant.engine import ask_assistant
from backend.app.assistant.tools import (
    get_starter_chips,
    suggest_next_leads,
    draft_case_diary,
)
from backend.app.verify.challenger import run_challenger_analysis

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
        return {"leads": suggest_next_leads(conn)}
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
    case_id: Optional[str] = Query(None),
):
    """Add an assistant answer to the Review Queue as a PROPOSED claim."""
    conn = get_db_connection(case_id)
    try:
        cid = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO claims (id, text, kind, tier, status, source_refs_json, quotes_json, generated_by, verifier_notes)
            VALUES (?, ?, ?, 'LEAD', 'PROPOSED', ?, '[]', 'INVESTIGATOR_ASSISTANT', 'Promoted from Investigator Assistant');
            """,
            (cid, text, kind, json.dumps(refs)),
        )
        conn.commit()
        return {"status": "PROPOSED", "claim_id": cid}
    finally:
        conn.close()
