"""Parser registry and evidence parsing orchestrator for PRAMAAN."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List, Optional, Type

from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport
from backend.app.parsers.whatsapp import WhatsAppParser
from backend.app.parsers.bank_pdf import BankPDFParser
from backend.app.parsers.bank_csv import BankCSVParser
from backend.app.parsers.calllog import CallLogParser
from backend.app.parsers.image import ImageParser
from backend.app.parsers.social_media import TelegramJSONParser, GenericSocialJSONParser
from backend.app.parsers.cloud import CloudLocationHistoryParser, CloudActivityCSVParser
from backend.app.parsers.email_parser import EmailParser
from backend.app.parsers.network_log import NetworkLogParser
from backend.app.parsers.cctv import CCTVCameraIndexParser, CCTVVideoParser
from backend.app.integrity.custody import append_custody_log
from backend.app.correlate.base import deterministic_id


class ParserRegistry:
    """Registry managing available evidence parsers using a plugin pattern."""

    def __init__(self):
        self._parsers: List[BaseParser] = [
            WhatsAppParser(),
            BankPDFParser(),
            BankCSVParser(),
            CCTVCameraIndexParser(),
            CloudActivityCSVParser(),
            NetworkLogParser(),
            CallLogParser(),
            ImageParser(),
            TelegramJSONParser(),
            CloudLocationHistoryParser(),
            GenericSocialJSONParser(),
            EmailParser(),
            CCTVVideoParser(),
        ]

    def register(self, parser: BaseParser):
        """Register a new parser plugin. Insert at beginning to allow custom overrides."""
        self._parsers.insert(0, parser)

    def get_parser(self, file_path: Path, filename: str) -> Optional[BaseParser]:
        """Find the first matching parser capable of parsing the evidence file."""
        for parser in self._parsers:
            if parser.can_parse(file_path, filename):
                return parser
        return None

    def detect_source_type(self, file_path: Path, filename: str) -> str:
        """Detect source type via registered plugins without hardcoded extensions."""
        p = self.get_parser(file_path, filename)
        if p:
            return p.source_type
        # Fallback check based on file extension
        lower = filename.lower()
        if lower.endswith(".txt"):
            return "whatsapp"
        elif lower.endswith(".pdf"):
            return "bank_pdf"
        elif lower.endswith(".csv"):
            return "calllog" if "call" in lower else "bank_csv"
        elif lower.endswith((".png", ".jpg", ".jpeg")):
            return "image"
        elif lower.endswith((".eml", ".mbox")):
            return "email"
        elif lower.endswith(".log"):
            return "network_log"
        elif lower.endswith((".mp4", ".avi", ".mov", ".mkv")):
            return "cctv_video"
        elif lower.endswith(".json"):
            return "social_generic"
        return "unknown"


# Global registry singleton
registry = ParserRegistry()


def parse_and_store_evidence(
    conn: sqlite3.Connection,
    evidence_id: str,
    actor: str = "SYSTEM",
) -> int:
    """Parse an ingested evidence file and store normalised forensic events + parse report into SQLite."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evidence WHERE id = ?;", (evidence_id,))
    row = cursor.fetchone()
    if not row:
        raise ValueError(f"Evidence {evidence_id} not found")

    filename = row["filename"]
    stored_path = Path(row["stored_path"])
    if not stored_path.exists():
        raise FileNotFoundError(f"Underlying evidence file missing at {stored_path}")

    parser = registry.get_parser(stored_path, filename)
    if not parser:
        cursor.execute("UPDATE evidence SET parse_status = 'UNSUPPORTED' WHERE id = ?;", (evidence_id,))
        conn.commit()
        return 0

    parsed_events, report = parser.parse_with_report(stored_path, evidence_id=evidence_id, filename=filename)

    # Insert events into unified events table
    clock_offsets_seen: List[Dict[str, object]] = []
    for idx, ev in enumerate(parsed_events):
        event_id = deterministic_id("evt", ev.evidence_id, idx, ev.ts_utc, ev.kind)
        cursor.execute(
            """
            INSERT INTO events (id, evidence_id, source_type, ts_utc, ts_original, tz_assumed, actor, counterparty, kind, text, amount, currency, location_id, clock_offset_seconds, offset_source, ref_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                event_id,
                ev.evidence_id,
                ev.source_type,
                ev.ts_utc,
                ev.ts_original,
                ev.tz_assumed,
                ev.actor,
                ev.counterparty,
                ev.kind,
                ev.text,
                ev.amount,
                ev.currency,
                ev.location_id,
                int(getattr(ev, "clock_offset_seconds", 0) or 0),
                getattr(ev, "offset_source", None),
                json.dumps(ev.ref, ensure_ascii=True),
            ),
        )
        if getattr(ev, "clock_offset_seconds", 0):
            clock_offsets_seen.append({
                "event_id": event_id,
                "offset_seconds": ev.clock_offset_seconds,
                "offset_source": ev.offset_source or "unspecified",
                "camera_id": ev.ref.get("camera_id") if isinstance(ev.ref, dict) else None,
            })
        if isinstance(ev.ref, dict) and ev.ref.get("date_received_inconsistency"):
            inc = ev.ref["date_received_inconsistency"]
            cursor.execute(
                """
                INSERT OR IGNORE INTO anomalies (id, kind, severity, evidence_id, event_ids_json, description, detail_json, status)
                VALUES (?, 'ANOMALY_EMAIL_DATE_INCONSISTENCY', 'HIGH', ?, ?, ?, ?, 'LEAD');
                """,
                (
                    deterministic_id("anom_email_date", evidence_id, event_id),
                    evidence_id,
                    json.dumps([event_id]),
                    f"Email Date header differs from Received chain by {inc['drift_minutes']} minutes.",
                    json.dumps(inc),
                ),
            )

    if clock_offsets_seen:
        append_custody_log(
            conn,
            action="CLOCK_OFFSET_RECORDED",
            actor=actor,
            evidence_id=evidence_id,
            details={"filename": filename, "offsets": clock_offsets_seen},
        )

    parser_name = parser.__class__.__name__
    report_dict = report.to_dict()
    report_json = json.dumps(report_dict, ensure_ascii=True)

    cursor.execute(
        """
        UPDATE evidence
        SET parse_status = 'PARSED', parser = ?, parse_notes = ?, parse_report_json = ?
        WHERE id = ?;
        """,
        (parser_name, f"Parsed {len(parsed_events)} events successfully", report_json, evidence_id),
    )

    append_custody_log(
        conn,
        action="PARSED",
        actor=actor,
        evidence_id=evidence_id,
        details={
            "parser": parser_name,
            "events_count": len(parsed_events),
            "filename": filename,
            "total_units": report.total_units,
            "skipped_count": len(report.skipped_units),
            "error_count": len(report.errors),
            "reconciled": report_dict["reconciled"],
        },
    )

    conn.commit()
    return len(parsed_events)
