"""Digital Crime Scene Reconstruction API endpoints (B7)."""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Query

from backend.app.db import get_db_connection
from backend.app.scene.reconstructor import reconstruct_scene, replay_scene

router = APIRouter(prefix="/api/scene", tags=["scene"])


@router.get("")
def get_scene(
    start_ts: Optional[str] = Query(None),
    end_ts: Optional[str] = Query(None),
    episode_id: Optional[str] = Query(None),
    case_id: Optional[str] = Query(None),
):
    """Reconstruct a digital crime scene for a time window or episode."""
    conn = get_db_connection(case_id)
    try:
        return reconstruct_scene(conn, start_ts=start_ts, end_ts=end_ts, episode_id=episode_id)
    finally:
        conn.close()


@router.get("/replay")
def get_scene_replay(
    start_ts: Optional[str] = Query(None),
    end_ts: Optional[str] = Query(None),
    episode_id: Optional[str] = Query(None),
    case_id: Optional[str] = Query(None),
):
    """Return an ordered step-by-step replay of the crime scene."""
    conn = get_db_connection(case_id)
    try:
        return replay_scene(conn, start_ts=start_ts, end_ts=end_ts, episode_id=episode_id)
    finally:
        conn.close()
