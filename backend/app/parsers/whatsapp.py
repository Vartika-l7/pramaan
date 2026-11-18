"""WhatsApp chat export parser (Android & iOS format support)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import dateutil.parser
import pytz

from backend.app.parsers.base import BaseParser, ParsedEvent

# Android regex: 12/03/2026, 08:30 - Sender: message
# or 12/03/2026, 8:30 am - Sender: message
RE_ANDROID = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)\s*-\s*(.*)$"
)

# iOS regex: [12/03/26, 08:30:15] Sender: message
RE_IOS = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)\]\s*(.*)$"
)


class WhatsAppParser(BaseParser):
    def can_parse(self, file_path: Path, filename: str) -> bool:
        lower = filename.lower()
        if not lower.endswith(".txt"):
            return False
        # Read first few lines to detect WhatsApp header
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for _ in range(10):
                    line = f.readline()
                    if not line:
                        break
                    if RE_ANDROID.match(line) or RE_IOS.match(line):
                        return True
        except Exception:
            pass
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

        with open(file_path, "rb") as bf:
            raw_bytes = bf.read()

        raw_text = raw_bytes.decode("utf-8", errors="replace")
        lines = raw_text.splitlines(keepends=True)

        current_event: Optional[dict] = None
        current_byte_offset = 0

        for line_idx, line in enumerate(lines, start=1):
            line_len_bytes = len(line.encode("utf-8"))
            stripped_line = line.strip("\r\n")

            match = RE_ANDROID.match(stripped_line) or RE_IOS.match(stripped_line)

            if match:
                # Commit previous event if accumulating
                if current_event:
                    events.append(self._build_event(current_event, evidence_id, filename, tz, default_tz))

                date_part, time_part, rest = match.groups()
                ts_orig = f"{date_part} {time_part}"

                # Check if sender: message or system message
                if ": " in rest:
                    sender, msg_text = rest.split(": ", 1)
                    kind = "media" if "<Media omitted>" in msg_text else "message"
                else:
                    sender = "SYSTEM"
                    msg_text = rest
                    kind = "system"

                current_event = {
                    "ts_original": ts_orig,
                    "actor": sender,
                    "kind": kind,
                    "text": msg_text,
                    "line_start": line_idx,
                    "line_end": line_idx,
                    "byte_offset": current_byte_offset,
                    "byte_length": line_len_bytes,
                }
            else:
                # Continuation of multi-line message
                if current_event:
                    current_event["text"] += "\n" + stripped_line
                    current_event["line_end"] = line_idx
                    current_event["byte_length"] += line_len_bytes

            current_byte_offset += line_len_bytes

        if current_event:
            events.append(self._build_event(current_event, evidence_id, filename, tz, default_tz))

        return events

    def _build_event(
        self,
        ev_dict: dict,
        evidence_id: str,
        filename: str,
        tz: pytz.BaseTzInfo,
        tz_name: str,
    ) -> ParsedEvent:
        # Parse timestamp to UTC
        try:
            dt = dateutil.parser.parse(ev_dict["ts_original"], dayfirst=True)
            if dt.tzinfo is None:
                localized = tz.localize(dt)
            else:
                localized = dt
            ts_utc = localized.astimezone(pytz.utc).isoformat()
        except Exception:
            ts_utc = datetime.utcnow().isoformat()

        ref = {
            "file": filename,
            "line_start": ev_dict["line_start"],
            "line_end": ev_dict["line_end"],
            "byte_offset": ev_dict["byte_offset"],
            "byte_length": ev_dict["byte_length"],
        }

        return ParsedEvent(
            evidence_id=evidence_id,
            source_type="whatsapp",
            ts_utc=ts_utc,
            ts_original=ev_dict["ts_original"],
            tz_assumed=tz_name,
            kind=ev_dict["kind"],
            actor=ev_dict["actor"],
            text=ev_dict["text"],
            ref=ref,
        )

