"""System capabilities and audit log exploration API endpoints."""

from __future__ import annotations

import json
from typing import Optional
from fastapi import APIRouter, Query
from backend.app.config import OLLAMA_HOST, PRIMARY_MODEL, CHALLENGER_MODEL, USE_INDIC_NER
from backend.app.db import get_db_connection

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/system/capabilities")
def get_system_capabilities():
    """Retrieve live status of offline AI models, OCR engines, and PDF parsers."""
    import httpx

    # 1. Ollama status
    ollama_ok = False
    ollama_models = []
    try:
        r = httpx.get(f"{OLLAMA_HOST}/api/tags", timeout=1.0)
        if r.status_code == 200:
            ollama_ok = True
            ollama_models = [m.get("name") for m in r.json().get("models", [])]
    except Exception:
        pass

    # 2. Tesseract OCR status
    tesseract_ok = False
    tess_langs = []
    try:
        import pytesseract
        tess_langs = pytesseract.get_languages()
        tesseract_ok = True
    except Exception:
        pass

    # 3. PDF Engine status
    pdf_engine_name = "pdfplumber + reportlab (Native Offline)"
    try:
        import weasyprint
        pdf_engine_name = "weasyprint + pdfplumber"
    except Exception:
        pass

    return {
        "ollama": {
            "available": ollama_ok,
            "host": OLLAMA_HOST,
            "primary_model": PRIMARY_MODEL,
            "challenger_model": CHALLENGER_MODEL,
            "models": ollama_models,
        },
        "tesseract": {
            "available": tesseract_ok,
            "languages": tess_langs if tesseract_ok else ["eng", "hin (fallback unavailable)"],
        },
        "pdf_engine": {
            "engine": pdf_engine_name,
            "available": True,
            "notes": "Full PDF parsing and signed report generation enabled.",
        },
        "indic_ner": {
            "enabled": USE_INDIC_NER,
            "notes": "Rule-based Indic gazetteer active (transformers optional).",
        },
    }


@router.get("/audit")
def get_full_audit_log(case_id: Optional[str] = Query(None)):
    """Retrieve full tamper-evident custody log and human adjudication records."""
    conn = get_db_connection(case_id)
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM custody_log ORDER BY seq ASC;")
        custody_rows = [dict(r) for r in cursor.fetchall()]

        cursor.execute("SELECT * FROM reviews ORDER BY rowid ASC;")
        review_rows = [dict(r) for r in cursor.fetchall()]

        return {
            "case_id": case_id or "PRM-2026-0042",
            "total_custody_events": len(custody_rows),
            "total_human_reviews": len(review_rows),
            "custody_log": custody_rows,
            "reviews": review_rows,
        }
    finally:
        conn.close()

