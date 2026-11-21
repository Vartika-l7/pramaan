"""Case Packaging, PDF Generation, and Package Download API endpoints."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse

from backend.app.db import get_db_connection
from backend.app.config import BASE_DIR, CASE_DATA_DIR
from backend.app.integrity.merkle import compute_case_merkle_root
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


@router.get("/preview")
def preview_court_report(case_id: Optional[str] = Query(None)):
    """Preview the court report (approved items only, exhibits, event sequence, Section 63 draft)."""
    cid = case_id or "PRM-2026-0042"
    conn = get_db_connection(cid)
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT exhibit_id, filename, source_type, sha256, size_bytes, received_at_utc FROM evidence ORDER BY exhibit_id ASC;"
        )
        exhibits = [dict(r) for r in cursor.fetchall()]

        cursor.execute(
            "SELECT id, text, kind, tier, status, source_refs_json, quotes_json FROM claims WHERE status = 'APPROVED' ORDER BY rowid ASC;"
        )
        approved_claims = []
        for r in cursor.fetchall():
            d = dict(r)
            d["refs"] = json.loads(d.pop("source_refs_json", "[]"))
            d["quotes"] = json.loads(d.pop("quotes_json", "[]"))
            approved_claims.append(d)

        cursor.execute(
            "SELECT id, src, dst, edge_type, reason_text, strength, tier, event_ids_json FROM edges WHERE status = 'APPROVED' ORDER BY strength DESC;"
        )
        approved_edges = []
        for r in cursor.fetchall():
            d = dict(r)
            d["event_ids"] = json.loads(d.pop("event_ids_json", "[]"))
            approved_edges.append(d)

        cursor.execute(
            "SELECT id, title, start_ts_utc, end_ts_utc FROM episodes ORDER BY start_ts_utc ASC;"
        )
        episodes = [dict(r) for r in cursor.fetchall()]

        merkle_root, _ = compute_case_merkle_root(conn)
        return {
            "case_id": cid,
            "exhibits": exhibits,
            "approved_claims": approved_claims,
            "approved_edges": approved_edges,
            "episodes": episodes,
            "merkle_root": merkle_root,
            "section63_draft": {
                "status": "DRAFT — HUMANS MUST SIGN",
                "act": "Bharatiya Sakshya Adhiniyam, 2023 · Section 63(4)",
                "statement": f"Electronic records ({len(exhibits)} exhibits) hashed via SHA-256 at ingest and sealed under Merkle root {merkle_root}.",
            },
            "qr_payload": json.dumps({"case_id": cid, "merkle_root": merkle_root, "exhibits": len(exhibits)}),
        }
    finally:
        conn.close()


@router.post("/verify")
def run_standalone_verifier(case_id: Optional[str] = Query(None)):
    """Execute the standalone offline verifier.py on the assembled case package and return real output."""
    cid = case_id or "PRM-2026-0042"
    pkg_dir = PACKAGES_DIR / f"package_{cid}"
    if not pkg_dir.exists() or not (pkg_dir / "manifest.json").exists():
        conn = get_db_connection(cid)
        try:
            assemble_case_package(conn, case_id=cid)
        finally:
            conn.close()

    verifier_script = BASE_DIR / "verifier" / "verifier.py"
    proc = subprocess.run(
        [sys.executable, str(verifier_script), "--package", str(pkg_dir)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    output = (proc.stdout or "") + (("\n" + proc.stderr) if proc.stderr else "")
    return {
        "case_id": cid,
        "verdict": "PASS" if proc.returncode == 0 else "FAIL",
        "returncode": proc.returncode,
        "output": output.strip(),
        "verified_at_utc": datetime.now(timezone.utc).isoformat(),
    }

