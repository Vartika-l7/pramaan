"""Automated Event-Sequence API endpoints (B6)."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse, PlainTextResponse

from backend.app.db import get_db_connection
from backend.app.sequence.generator import (
    generate_event_sequence,
    get_stored_episodes,
    export_sequence_markdown,
)
from backend.app.config import EPISODE_GAP_MINUTES

router = APIRouter(prefix="/api/sequence", tags=["sequence"])


@router.post("/generate")
def generate_sequence(
    case_id: Optional[str] = Query(None),
    gap_minutes: int = Query(EPISODE_GAP_MINUTES, ge=1),
):
    """Deterministically segment the unified timeline into titled episodes."""
    conn = get_db_connection(case_id)
    try:
        episodes = generate_event_sequence(conn, gap_minutes=gap_minutes)
        return {"status": "GENERATED", "episode_count": len(episodes), "episodes": episodes}
    finally:
        conn.close()


@router.get("")
def get_sequence(case_id: Optional[str] = Query(None)):
    """Retrieve the generated event sequence episodes."""
    conn = get_db_connection(case_id)
    try:
        episodes = get_stored_episodes(conn)
        if not episodes:
            episodes = generate_event_sequence(conn)
        return {"episode_count": len(episodes), "episodes": episodes}
    finally:
        conn.close()


@router.get("/export")
def export_sequence(
    format: str = Query("json", pattern="^(json|markdown)$"),
    case_id: Optional[str] = Query(None),
):
    """Export the automated event sequence as JSON or plain Markdown."""
    conn = get_db_connection(case_id)
    try:
        episodes = get_stored_episodes(conn)
        if not episodes:
            episodes = generate_event_sequence(conn)
        if format == "markdown":
            return PlainTextResponse(content=export_sequence_markdown(episodes), media_type="text/markdown")
        return JSONResponse(content={"episode_count": len(episodes), "episodes": episodes})
    finally:
        conn.close()
