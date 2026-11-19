"""Bank CSV statement parser with strict schema validation and full unit reconciliation."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import dateutil.parser
import pytz

from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport, SkippedUnit, ParseErrorUnit

REQUIRED_COLUMNS = {"date", "narration"}


class BankCSVParser(BaseParser):
    @property
    def source_type(self) -> str:
        return "bank_csv"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        lower = filename.lower()
        if not lower.endswith(".csv"):
            return False
        if "call" in lower:
            return False
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = [c.lower().strip() for c in next(reader, [])]
                return "narration" in header or "balance" in header
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

        # Line 1 is header
        header_line = lines[0]
        header_reader = csv.reader([header_line])
        headers = [c.lower().strip() for c in next(header_reader, [])]

        # Strict column validation
        missing_cols = REQUIRED_COLUMNS - set(headers)
        if missing_cols:
            raise ValueError(
                f"Bank CSV validation failed for '{filename}': Missing required columns: {sorted(list(missing_cols))}. "
                f"Found columns: {headers}"
            )

        # Header counts as skipped unit 1 (schema header)
        skipped.append(SkippedUnit(
            unit_index=1,
            raw_content=header_line.strip(),
            reason="CSV Schema Header",
        ))

        # Track byte offsets for auditability
        current_byte_offset = len(header_line.encode("utf-8"))

        # Parse subsequent rows
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

            date_str = (row.get("date") or "").strip()
            narration = (row.get("narration") or "").strip()
            debit_str = (row.get("debit") or "0").strip()
            credit_str = (row.get("credit") or "0").strip()
            balance_str = (row.get("balance") or "0").strip()

            if not date_str:
                errors.append(ParseErrorUnit(
                    unit_index=row_idx,
                    raw_content=raw_line.strip(),
                    error="Row missing date column value",
                ))
                current_byte_offset += raw_line_bytes
                continue

            try:
                dt = dateutil.parser.parse(date_str, dayfirst=True)
                if dt.tzinfo is None:
                    dt = tz.localize(dt)
                ts_utc = dt.astimezone(pytz.utc).isoformat()
            except Exception as e:
                errors.append(ParseErrorUnit(
                    unit_index=row_idx,
                    raw_content=raw_line.strip(),
                    error=f"Date parsing error for '{date_str}': {str(e)}",
                ))
                current_byte_offset += raw_line_bytes
                continue

            try:
                debit_val = float(debit_str) if debit_str else 0.0
            except ValueError:
                debit_val = 0.0

            try:
                credit_val = float(credit_str) if credit_str else 0.0
            except ValueError:
                credit_val = 0.0

            try:
                balance_val = float(balance_str) if balance_str else 0.0
            except ValueError:
                balance_val = 0.0

            if debit_val > 0:
                kind = "debit"
                amount = debit_val
            elif credit_val > 0:
                kind = "credit"
                amount = credit_val
            else:
                kind = "statement_row"
                amount = 0.0

            ref = {
                "file": filename,
                "row_index": row_idx,
                "byte_offset": current_byte_offset,
                "byte_length": raw_line_bytes,
                "balance": balance_val,
            }

            events.append(
                ParsedEvent(
                    evidence_id=evidence_id,
                    source_type="bank_csv",
                    ts_utc=ts_utc,
                    ts_original=date_str,
                    tz_assumed=default_tz,
                    kind=kind,
                    actor=filename.replace(".csv", ""),
                    text=narration,
                    amount=amount,
                    currency="INR",
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
