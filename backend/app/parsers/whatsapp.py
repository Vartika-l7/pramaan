"""WhatsApp chat export parser (Android & iOS format support with full reconciliation)."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import dateutil.parser
import pytz

from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport, SkippedUnit, ParseErrorUnit

# Android regex: 12/03/2026, 08:30 - Sender: message
# or 12/03/2026, 8:30 am - Sender: message
RE_ANDROID = re.compile(
    r"^(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)\s*-\s*(.*)$"
)

# iOS regex: [12/03/26, 08:30:15] Sender: message
RE_IOS = re.compile(
    r"^\[(\d{1,2}/\d{1,2}/\d{2,4}),?\s+(\d{1,2}:\d{2}(?::\d{2})?(?:\s*[AaPp][Mm])?)\]\s*(.*)$"
)

DELETED_MARKERS = [
    "this message was deleted",
    "you deleted this message",
    "message was deleted",
    "this message was revoked",
]


class WhatsAppParser(BaseParser):
    @property
    def source_type(self) -> str:
        return "whatsapp"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        lower = filename.lower()
        if not lower.endswith(".txt"):
            return False
        # Read first few lines to detect WhatsApp header
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                for _ in range(15):
                    line = f.readline()
                    if not line:
                        break
                    line_s = line.strip()
                    if RE_ANDROID.match(line_s) or RE_IOS.match(line_s):
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

        with open(file_path, "rb") as bf:
            raw_bytes = bf.read()

        raw_text = raw_bytes.decode("utf-8", errors="replace")
        lines = raw_text.splitlines(keepends=True)
        total_lines = len(lines)

        skipped: List[SkippedUnit] = []
        errors: List[ParseErrorUnit] = []

        current_event: Optional[dict] = None
        current_byte_offset = 0

        for line_idx, line in enumerate(lines, start=1):
            line_len_bytes = len(line.encode("utf-8"))
            stripped_line = line.strip("\r\n")

            if not stripped_line:
                # Account for empty lines
                if current_event:
                    # Empty line within a multi-line message counts as continuation line
                    current_event["continuation_lines"] += 1
                    current_event["text"] += "\n"
                    current_event["line_end"] = line_idx
                    current_event["byte_length"] += line_len_bytes
                else:
                    skipped.append(SkippedUnit(
                        unit_index=line_idx,
                        raw_content=line,
                        reason="Empty whitespace line before any message",
                    ))
                current_byte_offset += line_len_bytes
                continue

            match = RE_ANDROID.match(stripped_line) or RE_IOS.match(stripped_line)

            if match:
                # Commit previous event
                if current_event:
                    events.append(self._build_event(current_event, evidence_id, filename, tz, default_tz))

                date_part, time_part, rest = match.groups()
                ts_orig = f"{date_part} {time_part}"

                if ": " in rest:
                    sender, msg_text = rest.split(": ", 1)
                    lower_msg = msg_text.lower().strip()
                    if any(marker in lower_msg for marker in DELETED_MARKERS):
                        kind = "deleted_message"
                    elif "<Media omitted>" in msg_text or "image omitted" in lower_msg:
                        kind = "media"
                    else:
                        kind = "message"
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
                    "continuation_lines": 0,
                }
            else:
                # Continuation of multi-line message or header
                if current_event:
                    current_event["text"] += "\n" + stripped_line
                    current_event["line_end"] = line_idx
                    current_event["byte_length"] += line_len_bytes
                    current_event["continuation_lines"] += 1
                else:
                    # Unrecognized line prior to first message header
                    skipped.append(SkippedUnit(
                        unit_index=line_idx,
                        raw_content=stripped_line,
                        reason="Header/preamble line without timestamp match",
                    ))

            current_byte_offset += line_len_bytes

        if current_event:
            events.append(self._build_event(current_event, evidence_id, filename, tz, default_tz))

        # Reconcile lines:
        # Every input line must be accounted for:
        # Each event accounts for: (line_end - line_start + 1) lines = 1 base line + continuation_lines
        # To make input_units = parsed_events + skipped + errors, we treat each input line as an input unit.
        # Lines accounted by multi-line continuations are registered as "multi-line continuation lines"
        # so total_units = events + continuation_lines_skipped + preamble_skipped + errors.
        total_continuation_lines = sum(
            (ev.ref.get("line_end", ev.ref.get("line_start", 1)) - ev.ref.get("line_start", 1))
            for ev in events
        )
        
        # Add continuation lines into skipped (as reconciled multi-line payload) so line math holds exactly:
        # total_lines == len(events) + len(skipped) + len(errors)
        for ev in events:
            l_start = ev.ref.get("line_start", 1)
            l_end = ev.ref.get("line_end", l_start)
            for c_idx in range(l_start + 1, l_end + 1):
                skipped.append(SkippedUnit(
                    unit_index=c_idx,
                    raw_content="<continuation>",
                    reason=f"Continuation of multi-line message starting at line {l_start}",
                ))

        report = ParseReport(
            total_units=total_lines,
            parsed_events=len(events),
            skipped_units=skipped,
            errors=errors,
            unit_name="lines",
        )

        return events, report

    def _build_event(
        self,
        ev_dict: dict,
        evidence_id: str,
        filename: str,
        tz: pytz.BaseTzInfo,
        tz_name: str,
    ) -> ParsedEvent:
        try:
            dt = dateutil.parser.parse(ev_dict["ts_original"], dayfirst=True)
            if dt.tzinfo is None:
                localized = tz.localize(dt)
            else:
                localized = dt
            ts_utc = localized.astimezone(pytz.utc).isoformat()
        except Exception:
            ts_utc = datetime.now(pytz.utc).isoformat()

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
