"""CCTV Footage & Camera Registry / Clip-Index Parsers (B1, B2).

Note: CCTV support covers integrity, provenance, time-and-place anchoring, and correlation.
No video analytics are performed in this prototype.
"""

from __future__ import annotations

import csv
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport, SkippedUnit, ParseErrorUnit
from backend.app.parsers.time_utils import normalise_to_utc


class CCTVCameraIndexParser(BaseParser):
    """Parser for CCTV camera registry and clip-index CSV."""

    REQUIRED_COLS = {
        "camera_id",
        "location_name",
        "lat",
        "lon",
        "clip_file",
        "clip_start_local",
        "clip_end_local",
        "clock_offset_seconds",
        "offset_source",
    }

    @property
    def source_type(self) -> str:
        return "cctv_index"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        if not filename.lower().endswith(".csv"):
            return False
        try:
            with open(file_path, "r", encoding="utf-8", errors="replace") as f:
                header = f.readline().lower()
                return "camera_id" in header and "clip_file" in header and "clock_offset_seconds" in header
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
        raw_bytes = file_path.read_bytes()
        lines = raw_bytes.decode("utf-8", errors="replace").splitlines(keepends=True)
        if not lines:
            raise ValueError(f"CCTV index CSV {filename} is empty.")

        header_fields = [c.strip().lower() for c in next(csv.reader([lines[0]]))]
        missing = self.REQUIRED_COLS - set(header_fields)
        if missing:
            raise ValueError(f"CCTV index CSV {filename} missing required columns: {sorted(missing)}")

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
                cam_id = row["camera_id"]
                loc_name = row["location_name"]
                lat = float(row["lat"])
                lon = float(row["lon"])
                clip_file = row["clip_file"]
                start_local = row["clip_start_local"]
                end_local = row["clip_end_local"]
                offset_sec = int(float(row["clock_offset_seconds"] or 0))
                offset_src = row["offset_source"] or "unspecified"
                actor_note = row.get("observed_subject") or cam_id

                start_utc, start_uncorrected_utc = normalise_to_utc(
                    start_local, default_tz=default_tz, clock_offset_seconds=offset_sec
                )
                end_utc, end_uncorrected_utc = normalise_to_utc(
                    end_local, default_tz=default_tz, clock_offset_seconds=offset_sec
                )

                events.append(
                    ParsedEvent(
                        evidence_id=evidence_id,
                        source_type=self.source_type,
                        ts_utc=start_utc,
                        ts_original=start_local,
                        tz_assumed=default_tz,
                        actor=actor_note,
                        kind="CCTV_CLIP",
                        text=(
                            f"CCTV clip {clip_file} from {cam_id} at {loc_name} "
                            f"(original {start_local}..{end_local}, clock offset {offset_sec:+d}s via {offset_src})"
                        ),
                        location_id=loc_name,
                        clock_offset_seconds=offset_sec,
                        offset_source=offset_src,
                        ref={
                            "file": filename,
                            "row": row_idx,
                            "byte_offset": byte_offset,
                            "byte_length": line_bytes,
                            "camera_id": cam_id,
                            "location_name": loc_name,
                            "lat": lat,
                            "lon": lon,
                            "clip_file": clip_file,
                            "clip_start_local": start_local,
                            "clip_end_local": end_local,
                            "clip_start_uncorrected_utc": start_uncorrected_utc,
                            "clip_end_utc": end_utc,
                            "clip_end_uncorrected_utc": end_uncorrected_utc,
                            "clock_offset_seconds": offset_sec,
                            "offset_source": offset_src,
                            "disclaimer": "CCTV support covers integrity, provenance, time-and-place anchoring, and correlation (no video analytics).",
                        },
                    )
                )
            except Exception as exc:
                errors.append(ParseErrorUnit(row_idx, stripped[:200], f"CCTV index row error: {exc}"))
            byte_offset += line_bytes

        return events, ParseReport(total_units=total_rows, parsed_events=len(events), skipped_units=skipped, errors=errors, unit_name="rows")


class CCTVVideoParser(BaseParser):
    """Parser for CCTV video files (.mp4, .avi, .mov, .mkv) — integrity & container metadata only."""

    @property
    def source_type(self) -> str:
        return "cctv_video"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        return filename.lower().endswith((".mp4", ".avi", ".mov", ".mkv"))

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
        size_bytes = file_path.stat().st_size
        ffprobe_bin = shutil.which("ffprobe")
        container_meta: Dict[str, Any] = {"ffprobe_available": bool(ffprobe_bin)}

        if ffprobe_bin:
            try:
                proc = subprocess.run(
                    [ffprobe_bin, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams", str(file_path)],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    container_meta["ffprobe"] = json.loads(proc.stdout)
            except Exception as exc:
                container_meta["ffprobe_error"] = str(exc)

        creation_time = (
            container_meta.get("ffprobe", {}).get("format", {}).get("tags", {}).get("creation_time")
            if isinstance(container_meta.get("ffprobe"), dict)
            else None
        )
        if creation_time:
            ts_utc, ts_original = normalise_to_utc(str(creation_time), default_tz=default_tz)
        else:
            ts_original = "CONTAINER_TIMESTAMP_ABSENT"
            ts_utc = "1970-01-01T00:00:00+00:00"
        ev = ParsedEvent(
            evidence_id=evidence_id,
            source_type=self.source_type,
            ts_utc=ts_utc,
            ts_original=ts_utc,
            tz_assumed=default_tz,
            kind="CCTV_CLIP",
            text=f"CCTV video exhibit {filename} ({size_bytes} bytes). Integrity & provenance anchored; no video analytics performed.",
            ref={
                "file": filename,
                "size_bytes": size_bytes,
                "container_metadata": container_meta,
                "disclaimer": "CCTV support covers integrity, provenance, time-and-place anchoring, and correlation (no video analytics).",
            },
        )
        return [ev], ParseReport(total_units=1, parsed_events=1, unit_name="files")
