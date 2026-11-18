"""Case Packaging, PDF Generation, and Package Download API endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.app.db import get_db_connection
from backend.app.config import CASE_DATA_DIR
from backend.app.report.package import assemble_case_package, PACKAGES_DIR

router = APIRouter(prefix="/api/report", tags=["report"])


@router.post("/build")
def build_case_package_endpoint(case_id: Optional[str] = Query(None)):
    """Build the complete court report PDF, sign manifests, and package into a standalone ZIP."""
    cid = case_id or "PRM-2026-0042"
    conn = get_db_connection(cid)
    try:
        zip_path = assemble_case_package(conn, case_id=cid)
        return {
            "status": "BUILT",
            "case_id": cid,
            "zip_filename": zip_path.name,
            "size_bytes": zip_path.stat().st_size,
            "download_url": f"/api/report/download?case_id={cid}",
        }
    finally:
        conn.close()


@router.get("/download")
def download_case_package(case_id: Optional[str] = Query(None)):
    """Download the signed, standalone case package ZIP."""
    cid = case_id or "PRM-2026-0042"
    zip_path = PACKAGES_DIR / f"case_{cid}_package.zip"
    if not zip_path.exists():
        conn = get_db_connection(cid)
        try:
            zip_path = assemble_case_package(conn, case_id=cid)
        finally:
            conn.close()

    return FileResponse(
        path=str(zip_path),
        media_type="application/zip",
        filename=f"case_{cid}_package.zip",
    )


@router.get("/pdf")
def view_case_report_pdf(case_id: Optional[str] = Query(None)):
    """Serve the generated court report PDF for direct viewing."""
    cid = case_id or "PRM-2026-0042"
    pkg_dir = PACKAGES_DIR / f"package_{cid}"
    pdf_path = pkg_dir / "report.pdf"
    if not pdf_path.exists():
        conn = get_db_connection(cid)
        try:
            assemble_case_package(conn, case_id=cid)
        finally:
            conn.close()

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename=f"court_report_{cid}.pdf",
    )

