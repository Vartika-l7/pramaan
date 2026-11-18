"""Media Forensics and Financial Authenticity API endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.app.db import get_db_connection
from backend.app.config import CASE_DATA_DIR
from backend.app.authenticity.statement_checks import get_statement_balance_breakdown

router = APIRouter(prefix="/api/authenticity", tags=["authenticity"])
ELA_DIR = CASE_DATA_DIR / "ela_heatmaps"


@router.get("/image/{evidence_id}")
def get_image_authenticity(evidence_id: str, case_id: Optional[str] = Query(None)):
    """Retrieve side-by-side original and ELA metadata diff for an image exhibit."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ? OR exhibit_id = ?;", (evidence_id, evidence_id))
        ev = cursor.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Image exhibit not found")

        sha256 = ev["sha256"]
        heatmap_file = ELA_DIR / f"{sha256}_ela.png"

        cursor.execute("SELECT ref_json FROM events WHERE evidence_id = ? LIMIT 1;", (ev["id"],))
        ev_row = cursor.fetchone()
        ref = json.loads(ev_row["ref_json"]) if ev_row else {}

        # Fetch anomaly if any
        cursor.execute("SELECT * FROM anomalies WHERE evidence_id = ? AND kind = 'ANOMALY_IMAGE_EDITED';", (ev["id"],))
        anom = cursor.fetchone()
        anomaly_detail = json.loads(anom["detail_json"]) if anom else None

        return {
            "exhibit_id": ev["exhibit_id"],
            "filename": ev["filename"],
            "sha256": sha256,
            "has_ela_heatmap": heatmap_file.exists(),
            "heatmap_url": f"/api/authenticity/image/{ev['exhibit_id']}/heatmap",
            "exif": ref.get("exif", {}),
            "phash": ref.get("phash"),
            "dimensions": ref.get("dimensions"),
            "anomaly": anomaly_detail,
        }
    finally:
        conn.close()


@router.get("/image/{evidence_id}/heatmap")
def get_image_ela_heatmap_file(evidence_id: str, case_id: Optional[str] = Query(None)):
    """Serve the ELA heatmap PNG directly for side-by-side frontend inspection."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT sha256 FROM evidence WHERE id = ? OR exhibit_id = ?;", (evidence_id, evidence_id))
        ev = cursor.fetchone()
        if not ev:
            raise HTTPException(status_code=404, detail="Exhibit not found")

        heatmap_file = ELA_DIR / f"{ev['sha256']}_ela.png"
        if not heatmap_file.exists():
            raise HTTPException(status_code=404, detail="ELA heatmap not generated yet")

        return FileResponse(path=str(heatmap_file), media_type="image/png")
    finally:
        conn.close()


@router.get("/statement/{evidence_id}")
def get_statement_balance_checks(evidence_id: str, case_id: Optional[str] = Query(None)):
    """Retrieve row-by-row balance arithmetic breakdown for bank statements."""
    conn = get_db_connection(case_id)
    try:
        res = get_statement_balance_breakdown(conn, evidence_id)
        if "error" in res:
            raise HTTPException(status_code=404, detail=res["error"])
        return res
    finally:
        conn.close()

