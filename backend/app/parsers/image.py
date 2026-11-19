"""Image forensic parser (EXIF, perceptual hash, and optional OCR) with reconciliation."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Tuple
import exifread
import imagehash
from PIL import Image

from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport, SkippedUnit, ParseErrorUnit


class ImageParser(BaseParser):
    @property
    def source_type(self) -> str:
        return "image"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        return filename.lower().endswith((".png", ".jpg", ".jpeg"))

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
        exif_data = {}
        phash_str = None
        ocr_text = ""

        try:
            with Image.open(file_path) as img:
                phash_str = str(imagehash.phash(img))
                width, height = img.size
                format_type = img.format
        except Exception:
            width, height, format_type = 0, 0, "UNKNOWN"

        try:
            with open(file_path, "rb") as f:
                tags = exifread.process_file(f, details=False)
                for k, v in tags.items():
                    if k in ("Image Software", "EXIF DateTimeOriginal", "EXIF DateTimeDigitized", "Image DateTime", "Image Make", "Image Model"):
                        exif_data[k] = str(v)
        except Exception:
            pass

        try:
            import pytesseract
            with Image.open(file_path) as img:
                ocr_text = pytesseract.image_to_string(img, lang="eng+hin").strip()
        except Exception:
            ocr_text = "[OCR unavailable: tesseract not found or language pack missing]"

        ts_original = exif_data.get("EXIF DateTimeOriginal") or exif_data.get("Image DateTime") or datetime.now(timezone.utc).isoformat()
        ts_utc = datetime.now(timezone.utc).isoformat()

        ref = {
            "file": filename,
            "format": format_type,
            "dimensions": f"{width}x{height}",
            "phash": phash_str,
            "exif": exif_data,
            "ocr_status": "AVAILABLE" if not ocr_text.startswith("[OCR unavailable") else "UNAVAILABLE",
        }

        events.append(
            ParsedEvent(
                evidence_id=evidence_id,
                source_type="image",
                ts_utc=ts_utc,
                ts_original=str(ts_original),
                tz_assumed=default_tz,
                kind="media",
                actor=filename,
                text=ocr_text if ocr_text else f"Image media exhibit ({format_type}, {width}x{height})",
                ref=ref,
            )
        )

        report = ParseReport(
            total_units=1,
            parsed_events=1,
            unit_name="images",
        )

        return events, report
