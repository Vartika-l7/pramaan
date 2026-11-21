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
from backend.app.sequence.generator import generate_event_sequence
from backend.app.ai.provider import get_ai_provider
from backend.app.ai.run_records import record_ai_run
from backend.app.verify.claim_verifier import verify_claims

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

        # 3. Timeline anomalies (run before correlation so TimeWindowCorrelator links chat gaps)
        tl_anoms = detect_timeline_anomalies(conn)
        sp_anoms = detect_spatial_movement(conn)

        # 4. Correlate edges & funnel pattern
        edge_stats = generate_correlation_edges(conn)
        funnel_stats = detect_mule_funnel_pattern(conn)

        # 5. Media authenticity & statements
        img_anoms = inspect_image_authenticity(conn)
        stmt_anoms = verify_statement_arithmetic(conn)

        # 6. Automated event-sequence generation
        episodes = generate_event_sequence(conn)

        # 7. Draft & verify claims for the human Review Queue (never auto-approved)
        cursor.execute("SELECT id, ts_utc, kind, text, amount, actor, counterparty FROM events ORDER BY ts_utc ASC, id ASC LIMIT 200;")
        ev_rows = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT id, kind, severity, description FROM anomalies ORDER BY id ASC;")
        anom_rows = [dict(r) for r in cursor.fetchall()]
        cursor.execute("SELECT id, src, dst, edge_type, reason_text FROM edges ORDER BY id ASC;")
        edge_rows = [dict(r) for r in cursor.fetchall()]

        claims_verified = 0
        claims_removed = 0
        if ev_rows or anom_rows or edge_rows:
            provider = get_ai_provider()
            drafted = provider.draft_claims({"events": ev_rows, "anomalies": anom_rows, "edges": edge_rows})
            input_ids = [e["id"] for e in ev_rows] + [a["id"] for a in anom_rows] + [e["id"] for e in edge_rows]
            run_rec = record_ai_run(
                conn,
                task="claim_drafting",
                model_name=getattr(provider, "model_name", provider.__class__.__name__),
                model_version=getattr(provider, "model_version", "1.0"),
                parameters=getattr(provider, "parameters", {"temperature": 0, "seed": 42}),
                prompt=getattr(provider, "last_prompt", ""),
                input_record_ids=input_ids,
                raw_output=getattr(provider, "last_raw_output", json.dumps(drafted, ensure_ascii=True)),
                verifier_result={"status": "PENDING_VERIFICATION", "proposed_count": len(drafted)},
            )
            for c in drafted:
                c["ai_run_id"] = run_rec["id"]
                c["generated_by"] = provider.__class__.__name__
            ver_res = verify_claims(conn, drafted)
            claims_verified = ver_res["verified_count"]
            claims_removed = ver_res["removed_count"]

        return {
            "status": "COMPLETED",
            "parsed_evidence": len(pending),
            "extraction": ext_stats,
            "edges": edge_stats,
            "funnel_patterns": len(funnel_stats),
            "timeline_anomalies": len(tl_anoms) + len(sp_anoms),
            "authenticity_anomalies": len(img_anoms) + len(stmt_anoms),
            "episodes_generated": len(episodes),
            "claims_verified": claims_verified,
            "claims_removed": claims_removed,
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

