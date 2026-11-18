"""Integrity verification API endpoints."""

from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query
from backend.app.db import get_db_connection
from backend.app.ingest.service import verify_case_integrity

router = APIRouter(prefix="/api/integrity", tags=["integrity"])

_CACHED_STATUS: Optional[Dict[str, Any]] = None


@router.post("/verify")
def run_integrity_verification(case_id: Optional[str] = Query(None)):
    """Recomputes every stored file hash, verifies the hash chain and Merkle root."""
    global _CACHED_STATUS
    conn = get_db_connection(case_id)
    try:
        result = verify_case_integrity(conn)
        _CACHED_STATUS = result
        return result
    finally:
        conn.close()


@router.get("/status")
def get_integrity_status(case_id: Optional[str] = Query(None)):
    """Retrieve the cached integrity status for the top Case Bar seal."""
    global _CACHED_STATUS
    if _CACHED_STATUS is None:
        conn = get_db_connection(case_id)
        try:
            _CACHED_STATUS = verify_case_integrity(conn)
        finally:
            conn.close()
    return _CACHED_STATUS

