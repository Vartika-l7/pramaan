"""Call Detail Record (CDR) and Call Log CSV Parser with strict validation and full reconciliation."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import dateutil.parser
import pytz

from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport, SkippedUnit, ParseErrorUnit

REQUIRED_CALL_COLUMNS = {"timestamp", "direction", "number"}


class CallLogParser(BaseParser):
    @property
    def source_type(self) -> str:
        return "calllog"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        lower = filename.lower()
        if not lower.endswith(".csv"):
            return False
        if "call" not in lower:
            return False
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = [c.lower().strip() for c in next(reader, [])]
                return "direction" in header and "number" in header
        except Exception:
            return False

    def parse(
        self,
        file_path: Path,
        evidence_id: str,
        filename: str,
        default_tz: str = "Asia/Kolkata",
    ) -> List[ParsedEvent]:
        events, _ = self.parse_with_report(file_path, evidence_id, filename, default_tz)
        return events

    def parse_with_report(
        self,
        file_path: Path,
        evidence_id: str,
        filename: str,
        default_tz: str = "Asia/Kolkata",
    ) -> Tuple[List[ParsedEvent], ParseReport]:
        events: List[ParsedEvent] = []
        tz = pytz.timezone(default_tz)

        skipped: List[SkippedUnit] = []
        errors: List[ParseErrorUnit] = []

        with open(file_path, "r", encoding="utf-8") as f:
            lines = f.readlines()

        total_lines = len(lines)
        if not lines:
            return [], ParseReport(total_units=0, parsed_events=0, unit_name="rows")

        header_line = lines[0]
        header_reader = csv.reader([header_line])
        headers = [c.lower().strip() for c in next(header_reader, [])]

        missing_cols = REQUIRED_CALL_COLUMNS - set(headers)
        if missing_cols:
            raise ValueError(
                f"Call log validation failed for '{filename}': Missing required columns: {sorted(list(missing_cols))}. "
                f"Found columns: {headers}"
            )

        skipped.append(SkippedUnit(
            unit_index=1,
            raw_content=header_line.strip(),
            reason="CDR Schema Header",
        ))

        current_byte_offset = len(header_line.encode("utf-8"))

        reader = csv.DictReader(lines[1:], fieldnames=headers)
        for row_idx, row in enumerate(reader, start=2):
            raw_line = lines[row_idx - 1]
            raw_line_bytes = len(raw_line.encode("utf-8"))

            if not any(row.values()):
                skipped.append(SkippedUnit(
                    unit_index=row_idx,
                    raw_content=raw_line.strip(),
                    reason="Empty row",
                ))
                current_byte_offset += raw_line_bytes
                continue

            ts_str = (row.get("timestamp") or "").strip()
            direction = (row.get("direction") or "UNKNOWN").strip().upper()
            number = (row.get("number") or "").strip()
            dur_str = (row.get("duration_sec") or "0").strip()
            tower_id = (row.get("cell_tower_id") or "").strip()
            loc_name = (row.get("location_name") or "").strip()
            device_id = (row.get("device_id") or "").strip()

            if not ts_str:
                errors.append(ParseErrorUnit(
                    unit_index=row_idx,
                    raw_content=raw_line.strip(),
                    error="Row missing timestamp",
                ))
                current_byte_offset += raw_line_bytes
                continue

            try:
                dt = dateutil.parser.parse(ts_str)
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
                ts_utc = dt.astimezone(pytz.utc).isoformat()
            except Exception as e:
                errors.append(ParseErrorUnit(
                    unit_index=row_idx,
                    raw_content=raw_line.strip(),
                    error=f"Timestamp parse error: {str(e)}",
                ))
                current_byte_offset += raw_line_bytes
                continue

            try:
                duration_sec = int(dur_str)
            except ValueError:
                duration_sec = 0

            ref = {
                "file": filename,
                "row_index": row_idx,
                "byte_offset": current_byte_offset,
                "byte_length": raw_line_bytes,
                "direction": direction,
                "duration_sec": duration_sec,
                "cell_tower_id": tower_id,
                "location_name": loc_name,
                "device_id": device_id,
            }

            actor = f"Device_{device_id}" if device_id else filename.replace(".csv", "")
            text = f"{direction} call with {number} ({duration_sec}s) via tower {tower_id} ({loc_name})"

            events.append(
                ParsedEvent(
                    evidence_id=evidence_id,
                    source_type="calllog",
                    ts_utc=ts_utc,
                    ts_original=ts_str,
                    tz_assumed=default_tz,
                    kind="call",
                    actor=actor,
                    counterparty=number,
                    text=text,
                    location_id=tower_id or loc_name,
                    ref=ref,
                )
            )
            current_byte_offset += raw_line_bytes

        report = ParseReport(
            total_units=total_lines,
            parsed_events=len(events),
            skipped_units=skipped,
            errors=errors,
            unit_name="rows",
        )

        return events, report
