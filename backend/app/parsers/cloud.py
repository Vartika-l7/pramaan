"""Cloud Services Parsers: Location History JSON and Account Activity Log CSV (B1)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport, SkippedUnit, ParseErrorUnit
from backend.app.parsers.time_utils import normalise_to_utc


class CloudLocationHistoryParser(BaseParser):
    """Parser for cloud location-history JSON (timestamp, lat, lon, accuracy in metres)."""

    @property
    def source_type(self) -> str:
        return "cloud_location"

    def _extract_records(self, data: Any) -> Optional[List[Dict[str, Any]]]:
        if isinstance(data, dict) and isinstance(data.get("locations"), list):
            return data["locations"]
        if isinstance(data, list) and data and isinstance(data[0], dict) and "lat" in data[0] and "lon" in data[0]:
            return data
        return None

    def can_parse(self, file_path: Path, filename: str) -> bool:
        if not filename.lower().endswith(".json"):
            return False
        try:
            data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
            return self._extract_records(data) is not None
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
        data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
        records = self._extract_records(data)
        if records is None:
            raise ValueError("Invalid cloud location-history JSON: expected 'locations' list or array of {timestamp, lat, lon}.")

        default_device = data.get("device_id") if isinstance(data, dict) else None
        default_account = data.get("account") if isinstance(data, dict) else None

        events: List[ParsedEvent] = []
        skipped: List[SkippedUnit] = []
        errors: List[ParseErrorUnit] = []

        for idx, rec in enumerate(records):
            if not isinstance(rec, dict):
                errors.append(ParseErrorUnit(idx, str(rec)[:200], "Location record is not a JSON object"))
                continue

            ts_raw = rec.get("timestamp")
            lat = rec.get("lat")
            lon = rec.get("lon")
            if ts_raw is None or lat is None or lon is None:
                errors.append(ParseErrorUnit(idx, json.dumps(rec)[:200], "Missing required timestamp, lat, or lon"))
                continue

            try:
                ts_utc, _ = normalise_to_utc(str(ts_raw), default_tz=default_tz)
                lat_f = float(lat)
                lon_f = float(lon)
                acc_m = float(rec.get("accuracy_m", rec.get("accuracy", 50.0)))
            except Exception as exc:
                errors.append(ParseErrorUnit(idx, json.dumps(rec)[:200], f"Invalid coordinate or timestamp: {exc}"))
                continue

            device_id = rec.get("device_id") or rec.get("device") or default_device
            account = rec.get("account") or default_account
            place_name = rec.get("place_name") or f"{lat_f:.4f}, {lon_f:.4f}"

            events.append(
                ParsedEvent(
                    evidence_id=evidence_id,
                    source_type=self.source_type,
                    ts_utc=ts_utc,
                    ts_original=str(ts_raw),
                    tz_assumed=default_tz,
                    actor=str(device_id or account or "CloudDevice"),
                    kind="location_ping",
                    text=f"Cloud location ping at {place_name} (accuracy +/-{acc_m:.0f}m) [device={device_id or 'unknown'}]",
                    location_id=place_name,
                    ref={
                        "file": filename,
                        "record_index": idx,
                        "lat": lat_f,
                        "lon": lon_f,
                        "accuracy_m": acc_m,
                        "device_id": device_id,
                        "account": account,
                        "place_name": place_name,
                    },
                )
            )

        report = ParseReport(
            total_units=len(records),
            parsed_events=len(events),
            skipped_units=skipped,
            errors=errors,
            unit_name="records",
        )
        return events, report


class CloudActivityCSVParser(BaseParser):
    """Parser for cloud account activity log CSV (timestamp, account, action, ip, device)."""

    REQUIRED_COLS = {"timestamp", "account", "action", "ip", "device"}

    @property
    def source_type(self) -> str:
        return "cloud_activity"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        if not filename.lower().endswith(".csv"):
            return False
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                header = f.readline().lower()
                return all(col in header for col in ("timestamp", "account", "action", "ip", "device"))
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
        skipped: List[SkippedUnit] = []
        errors: List[ParseErrorUnit] = []

        raw_bytes = file_path.read_bytes()
        lines = raw_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
        if not lines:
            raise ValueError(f"Cloud activity CSV {filename} is empty.")

        header_fields = [c.strip().lower() for c in next(csv.reader([lines[0]]))]
        missing = self.REQUIRED_COLS - set(header_fields)
        if missing:
            raise ValueError(f"Cloud activity CSV {filename} missing required columns: {sorted(missing)}")

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
                ts_raw = row.get("timestamp", "")
                account = row.get("account", "")
                action = row.get("action", "")
                ip_addr = row.get("ip", "")
                device = row.get("device", "")

                if not ts_raw or not account or not action:
                    errors.append(ParseErrorUnit(row_idx, stripped[:200], "Missing timestamp, account, or action"))
                    byte_offset += line_bytes
                    continue

                ts_utc, _ = normalise_to_utc(ts_raw, default_tz=default_tz)
                kind = "login" if "login" in action.lower() else "cloud_activity"

                events.append(
                    ParsedEvent(
                        evidence_id=evidence_id,
                        source_type=self.source_type,
                        ts_utc=ts_utc,
                        ts_original=ts_raw,
                        tz_assumed=default_tz,
                        actor=account,
                        kind=kind,
                        text=f"Cloud {action} by {account} from IP {ip_addr} on device {device}",
                        ref={
                            "file": filename,
                            "row": row_idx,
                            "byte_offset": byte_offset,
                            "byte_length": line_bytes,
                            "account": account,
                            "action": action,
                            "ip": ip_addr,
                            "device_id": device,
                        },
                    )
                )
            except Exception as exc:
                errors.append(ParseErrorUnit(row_idx, stripped[:200], f"Row parse error: {exc}"))
            byte_offset += line_bytes

        report = ParseReport(
            total_units=total_rows,
            parsed_events=len(events),
            skipped_units=skipped,
            errors=errors,
            unit_name="rows",
        )
        return events, report
