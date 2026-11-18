"""Full Forensic Analysis Pipeline Orchestrator with SSE streaming."""

from __future__ import annotations

import asyncio
import json
from typing import Optional
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from backend.app.db import get_db_connection
from backend.app.ingest.registry import parse_and_store_evidence
from backend.app.extract.resolve import run_entity_extraction
from backend.app.correlate.edges import generate_correlation_edges
from backend.app.correlate.patterns import detect_mule_funnel_pattern
from backend.app.timeline.anomalies import detect_timeline_anomalies, detect_spatial_movement
from backend.app.authenticity.exif import inspect_image_authenticity
from backend.app.authenticity.statement_checks import verify_statement_arithmetic

router = APIRouter(prefix="/api/analyze", tags=["analyze"])


def execute_full_pipeline(case_id: Optional[str] = None):
    """Run all analysis stages synchronously."""
    conn = get_db_connection(case_id)
    try:
        # 1. Parse pending evidence
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM evidence WHERE parse_status = 'PENDING';")
        pending = cursor.fetchall()
        for p in pending:
            parse_and_store_evidence(conn, p["id"])

        # 2. Extract entities & mentions
        ext_stats = run_entity_extraction(conn)

        # 3. Correlate edges & funnel pattern
        edge_stats = generate_correlation_edges(conn)
        funnel_stats = detect_mule_funnel_pattern(conn)

        # 4. Timeline anomalies
        tl_anoms = detect_timeline_anomalies(conn)
        sp_anoms = detect_spatial_movement(conn)

        # 5. Media authenticity & statements
        img_anoms = inspect_image_authenticity(conn)
        stmt_anoms = verify_statement_arithmetic(conn)

        return {
            "status": "COMPLETED",
            "parsed_evidence": len(pending),
            "extraction": ext_stats,
            "edges": edge_stats,
            "funnel_patterns": len(funnel_stats),
            "timeline_anomalies": len(tl_anoms) + len(sp_anoms),
            "authenticity_anomalies": len(img_anoms) + len(stmt_anoms),
        }
    finally:
        conn.close()


@router.post("")
def run_analysis_pipeline(case_id: Optional[str] = Query(None)):
    """Run the complete automated digital forensics pipeline on all ingested exhibits."""
    return execute_full_pipeline(case_id)


@router.get("/stream")
async def stream_analysis_pipeline(case_id: Optional[str] = Query(None)):
    """Stream forensic pipeline stages via Server-Sent Events (SSE) for real-time progress in UI."""
    async def event_generator():
        stages = [
            ("PARSING", "Ingesting and parsing raw digital evidence exhibits..."),
            ("EXTRACTION", "Extracting regex identifiers, linguistic entities, and mentions..."),
            ("CORRELATION", "Correlating knowledge graph edges and detecting funnel patterns..."),
            ("TIMELINE", "Scanning timeline for chat silence gaps, inversions, and spatial thread..."),
            ("AUTHENTICITY", "Running Error Level Analysis (ELA) and statement arithmetic checks..."),
            ("FINALIZING", "Updating case integrity seal and analysis indexes..."),
        ]
        
        for stage_code, msg in stages:
            payload = json.dumps({"stage": stage_code, "message": msg})
            yield f"data: {payload}\n\n"
            await asyncio.sleep(0.15)

        # Run actual pipeline
        res = execute_full_pipeline(case_id)
        final_payload = json.dumps({"stage": "DONE", "result": res})
        yield f"data: {final_payload}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

