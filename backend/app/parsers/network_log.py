"""Network Log Parser for CSV and syslog-style network/portal logs (B1)."""

from __future__ import annotations

import csv
import ipaddress
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport, SkippedUnit, ParseErrorUnit
from backend.app.parsers.time_utils import normalise_to_utc

DEFAULT_COLUMN_MAP = {
    "timestamp": ["timestamp", "ts", "time", "datetime"],
    "src_ip": ["src_ip", "source_ip", "client_ip", "ip"],
    "dst_ip": ["dst_ip", "destination_ip", "dest_ip", "server_ip"],
    "port": ["port", "dst_port", "dest_port"],
    "user": ["user", "username", "account", "actor"],
    "action": ["action", "event", "status", "method"],
}

SYSLOG_RE = re.compile(
    r"^(?P<ts>\S+)\s+\S+\s+\S+:\s+user=(?P<user>\S+)\s+src_ip=(?P<src_ip>\S+)\s+dst_ip=(?P<dst_ip>\S+)\s+port=(?P<port>\d+)\s+action=(?P<action>\S+)(?P<rest>.*)$"
)


def _validate_ip(ip_str: str) -> str:
    return str(ipaddress.ip_address(ip_str.strip()))


class NetworkLogParser(BaseParser):
    """Parser for network logs (CSV with column-mapping config or syslog-style lines)."""

    def __init__(self, column_map: Optional[Dict[str, List[str]]] = None):
        self.column_map = column_map or DEFAULT_COLUMN_MAP

    @property
    def source_type(self) -> str:
        return "network_log"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        lower = filename.lower()
        if lower.endswith(".log"):
            return True
        if lower.endswith(".csv"):
            try:
                with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                    header = f.readline().lower()
                    return ("src_ip" in header or "source_ip" in header) and ("dst_ip" in header or "destination_ip" in header)
            except Exception:
                return False
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

    def _resolve_columns(self, header_fields: List[str]) -> Dict[str, str]:
        resolved: Dict[str, str] = {}
        lower_set = {h.strip().lower(): h.strip().lower() for h in header_fields}
        for canonical, aliases in self.column_map.items():
            for alias in aliases:
                if alias in lower_set:
                    resolved[canonical] = alias
                    break
        return resolved

    def parse_with_report(
        self,
        file_path: Path,
        evidence_id: str,
        filename: str,
        default_tz: str = "Asia/Kolkata",
    ) -> Tuple[List[ParsedEvent], ParseReport]:
        raw_bytes = file_path.read_bytes()
        lines = raw_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
        if not lines:
            raise ValueError(f"Network log {filename} is empty.")

        if filename.lower().endswith(".csv"):
            return self._parse_csv(lines, evidence_id, filename, default_tz)
        return self._parse_syslog(lines, evidence_id, filename, default_tz)

    def _parse_csv(
        self,
        lines: List[str],
        evidence_id: str,
        filename: str,
        default_tz: str,
    ) -> Tuple[List[ParsedEvent], ParseReport]:
        header_fields = [c.strip().lower() for c in next(csv.reader([lines[0]]))]
        col_map = self._resolve_columns(header_fields)
        required = {"timestamp", "src_ip", "dst_ip", "port", "user", "action"}
        missing = required - set(col_map.keys())
        if missing:
            raise ValueError(f"Network log CSV {filename} missing required columns: {sorted(missing)}")

        events: List[ParsedEvent] = []
        skipped: List[SkippedUnit] = []
        errors: List[ParseErrorUnit] = []
        total_rows = 0
        byte_offset = len(lines[0].encode("utf-8"))

        for row_idx, line in enumerate(lines[1:], start=1):
            total_rows += 1
            line_bytes = len(line.encode("utf-8"))
            stripped = line.strip()
            if not stripped:
                skipped.append(SkippedUnit(row_idx, "", "empty_row"))
                byte_offset += line_bytes
                continue

            try:
                vals = next(csv.reader([stripped]))
                row = {header_fields[i]: (vals[i].strip() if i < len(vals) else "") for i in range(len(header_fields))}
                ts_raw = row[col_map["timestamp"]]
                src_ip = _validate_ip(row[col_map["src_ip"]])
                dst_ip = _validate_ip(row[col_map["dst_ip"]])
                port = int(row[col_map["port"]])
                user = row[col_map["user"]]
                action = row[col_map["action"]]
                ts_utc, _ = normalise_to_utc(ts_raw, default_tz=default_tz)

                events.append(
                    ParsedEvent(
                        evidence_id=evidence_id,
                        source_type=self.source_type,
                        ts_utc=ts_utc,
                        ts_original=ts_raw,
                        tz_assumed=default_tz,
                        actor=user or src_ip,
                        counterparty=dst_ip,
                        kind="network_event",
                        text=f"Network {action}: user={user} src={src_ip} -> dst={dst_ip}:{port}",
                        ref={
                            "file": filename,
                            "row": row_idx,
                            "byte_offset": byte_offset,
                            "byte_length": line_bytes,
                            "src_ip": src_ip,
                            "dst_ip": dst_ip,
                            "port": port,
                            "user": user,
                            "action": action,
                        },
                    )
                )
            except Exception as exc:
                errors.append(ParseErrorUnit(row_idx, stripped[:200], f"Network CSV row error: {exc}"))
            byte_offset += line_bytes

        return events, ParseReport(total_units=total_rows, parsed_events=len(events), skipped_units=skipped, errors=errors, unit_name="rows")

    def _parse_syslog(
        self,
        lines: List[str],
        evidence_id: str,
        filename: str,
        default_tz: str,
    ) -> Tuple[List[ParsedEvent], ParseReport]:
        events: List[ParsedEvent] = []
        skipped: List[SkippedUnit] = []
        errors: List[ParseErrorUnit] = []
        byte_offset = 0

        for line_idx, line in enumerate(lines, start=1):
            line_bytes = len(line.encode("utf-8"))
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                skipped.append(SkippedUnit(line_idx, stripped[:200], "empty_or_comment"))
                byte_offset += line_bytes
                continue

            m = SYSLOG_RE.match(stripped)
            if not m:
                errors.append(ParseErrorUnit(line_idx, stripped[:200], "Unrecognized syslog line format"))
                byte_offset += line_bytes
                continue

            try:
                ts_raw = m.group("ts")
                src_ip = _validate_ip(m.group("src_ip"))
                dst_ip = _validate_ip(m.group("dst_ip"))
                port = int(m.group("port"))
                user = m.group("user")
                action = m.group("action")
                ts_utc, _ = normalise_to_utc(ts_raw, default_tz=default_tz)

                events.append(
                    ParsedEvent(
                        evidence_id=evidence_id,
                        source_type=self.source_type,
                        ts_utc=ts_utc,
                        ts_original=ts_raw,
                        tz_assumed=default_tz,
                        actor=user,
                        counterparty=dst_ip,
                        kind="network_event",
                        text=f"Network {action}: user={user} src={src_ip} -> dst={dst_ip}:{port}",
                        ref={
                            "file": filename,
                            "line": line_idx,
                            "byte_offset": byte_offset,
                            "byte_length": line_bytes,
                            "src_ip": src_ip,
                            "dst_ip": dst_ip,
                            "port": port,
                            "user": user,
                            "action": action,
                        },
                    )
                )
            except Exception as exc:
                errors.append(ParseErrorUnit(line_idx, stripped[:200], f"Syslog validation error: {exc}"))
            byte_offset += line_bytes

        return events, ParseReport(total_units=len(lines), parsed_events=len(events), skipped_units=skipped, errors=errors, unit_name="lines")
