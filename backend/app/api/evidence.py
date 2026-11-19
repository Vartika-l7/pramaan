"""Evidence management and safe raw preview API endpoints."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, File, Form, UploadFile, HTTPException, Query
from fastapi.responses import FileResponse, PlainTextResponse

from backend.app.db import get_db_connection
from backend.app.ingest.service import ingest_file

router = APIRouter(prefix="/api/evidence", tags=["evidence"])


@router.post("")
async def upload_evidence(
    file: UploadFile = File(...),
    source_type: Optional[str] = Form(None),
    case_id: Optional[str] = Form(None),
):
    """Upload an evidence file. Hashes first in 1MB chunks, stores read-only, records custody chain."""
    conn = get_db_connection(case_id)
    try:
        result = ingest_file(
            conn=conn,
            file_obj=file.file,
            filename=file.filename or "unknown_file",
            source_type=source_type,
        )
        return result
    finally:
        conn.close()


@router.get("")
def list_evidence(case_id: Optional[str] = Query(None)):
    """List all ingested exhibits with their SHA-256 chips, sizes, and parse statuses."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence ORDER BY exhibit_id ASC;")
        rows = cursor.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/{evidence_id}")
def get_evidence_detail(evidence_id: str, case_id: Optional[str] = Query(None)):
    """Retrieve full exhibit details along with its tamper-evident custody log events."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ? OR exhibit_id = ?;", (evidence_id, evidence_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Exhibit not found")

        ev_id = row["id"]
        cursor.execute(
            "SELECT seq, ts_utc, actor, action, details_json, prev_hash, entry_hash FROM custody_log WHERE evidence_id = ? ORDER BY seq ASC;",
            (ev_id,),
        )
        custody_rows = cursor.fetchall()

        custody_events = []
        for c in custody_rows:
            d = dict(c)
            try:
                d["details"] = json.loads(d.pop("details_json"))
            except Exception:
                d["details"] = {}
            custody_events.append(d)

        res = dict(row)
        if res.get("parse_report_json"):
            try:
                res["parse_report"] = json.loads(res["parse_report_json"])
            except Exception:
                res["parse_report"] = None
        else:
            res["parse_report"] = None
        res["custody_events"] = custody_events
        return res
    finally:
        conn.close()


@router.get("/{evidence_id}/raw-preview")
def get_raw_preview(evidence_id: str, case_id: Optional[str] = Query(None)):
    """Safe raw preview: text lines, images, or extracted PDF text without running arbitrary code."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM evidence WHERE id = ? OR exhibit_id = ?;", (evidence_id, evidence_id))
        row = cursor.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Exhibit not found")

        stored_path = Path(row["stored_path"])
        if not stored_path.exists():
            raise HTTPException(status_code=404, detail="Underlying evidence file missing")

        source_type = row["source_type"]
        lower_name = row["filename"].lower()

        if source_type == "image" or lower_name.endswith((".png", ".jpg", ".jpeg")):
            media_type = "image/png" if lower_name.endswith(".png") else "image/jpeg"
            return FileResponse(path=str(stored_path), media_type=media_type)

        if source_type in ("whatsapp", "calllog", "bank_csv") or lower_name.endswith((".txt", ".csv")):
            with open(stored_path, "r", encoding="utf-8", errors="replace") as f:
                lines = [f.readline() for _ in range(200)]
            return {
                "preview_type": "text",
                "filename": row["filename"],
                "lines": lines,
                "total_lines_previewed": len(lines),
            }

        if source_type == "bank_pdf" or lower_name.endswith(".pdf"):
            try:
                import pdfplumber
                with pdfplumber.open(stored_path) as pdf:
                    first_page_text = pdf.pages[0].extract_text() if pdf.pages else "Empty PDF"
                    num_pages = len(pdf.pages)
                return {
                    "preview_type": "pdf_text",
                    "filename": row["filename"],
                    "pages_count": num_pages,
                    "first_page_preview": first_page_text,
                }
            except Exception as e:
                return {
                    "preview_type": "pdf_fallback",
                    "filename": row["filename"],
                    "error": f"PDF preview error: {str(e)}",
                }

        return {
            "preview_type": "binary",
            "filename": row["filename"],
            "size_bytes": row["size_bytes"],
            "sha256": row["sha256"],
        }
    finally:
        conn.close()

