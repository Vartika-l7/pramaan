"""Call Detail Record (CDR) and Call Log CSV Parser."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import dateutil.parser
import pytz

from backend.app.parsers.base import BaseParser, ParsedEvent


class CallLogParser(BaseParser):
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
        events: List[ParsedEvent] = []
        tz = pytz.timezone(default_tz)

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=1):
                ts_str = row.get("timestamp", "").strip()
                direction = row.get("direction", "UNKNOWN").strip().upper()
                number = row.get("number", "").strip()
                dur_str = row.get("duration_sec", "0").strip()
                tower_id = row.get("cell_tower_id", "").strip()
                loc_name = row.get("location_name", "").strip()
                device_id = row.get("device_id", "").strip()

                try:
                    dt = dateutil.parser.parse(ts_str)
                    if dt.tzinfo is None:
                        dt = tz.localize(dt)
                    ts_utc = dt.astimezone(pytz.utc).isoformat()
                except Exception:
                    continue

                try:
                    duration_sec = int(dur_str)
                except ValueError:
                    duration_sec = 0

                ref = {
                    "file": filename,
                    "row_index": row_idx,
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

        return events

