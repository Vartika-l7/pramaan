"""Bank statement PDF parser using pdfplumber with strict validation and reconciliation."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple
import dateutil.parser
import pdfplumber
import pytz

from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport, SkippedUnit, ParseErrorUnit

REQUIRED_PDF_COLUMNS = {"date"}


def clean_amount(val: Optional[str]) -> Optional[float]:
    if not val or val.strip() in ("-", "", "None"):
        return None
    cleaned = re.sub(r"[^\d.]", "", val)
    try:
        return float(cleaned)
    except ValueError:
        return None


class BankPDFParser(BaseParser):
    @property
    def source_type(self) -> str:
        return "bank_pdf"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

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

        total_pdf_rows = 0

        with pdfplumber.open(file_path) as pdf:
            pdf_metadata = dict(pdf.metadata) if pdf.metadata else {}
            if not pdf.pages:
                raise ValueError(f"Bank PDF '{filename}' contains no pages.")

            # Validate that at least one table with required columns exists across pages
            valid_table_found = False

            for page_idx, page in enumerate(pdf.pages, start=1):
                tables = page.extract_tables()
                if not tables:
                    # Account for whole empty page as skipped unit
                    total_pdf_rows += 1
                    skipped.append(SkippedUnit(
                        unit_index=page_idx,
                        raw_content=f"Page {page_idx}",
                        reason="No tabular transaction structures found on page",
                    ))
                    continue

                for tbl_idx, table in enumerate(tables):
                    if not table or len(table) < 2:
                        total_pdf_rows += len(table) if table else 1
                        skipped.append(SkippedUnit(
                            unit_index=page_idx,
                            raw_content=f"Page {page_idx} table {tbl_idx}",
                            reason="Table has fewer than 2 rows",
                        ))
                        continue

                    headers = [str(c).lower().strip() if c else "" for c in table[0]]
                    has_date = any("date" in h for h in headers)
                    if not has_date:
                        total_pdf_rows += len(table)
                        skipped.append(SkippedUnit(
                            unit_index=page_idx,
                            raw_content=str(headers),
                            reason="Table missing required 'date' header column",
                        ))
                        continue

                    valid_table_found = True
                    # Header row accounted
                    total_pdf_rows += 1
                    skipped.append(SkippedUnit(
                        unit_index=1,
                        raw_content=str(headers),
                        reason=f"Page {page_idx} Table {tbl_idx} Header row",
                    ))

                    date_col = next((i for i, h in enumerate(headers) if "date" in h), 0)
                    desc_col = next((i for i, h in enumerate(headers) if "narration" in h or "desc" in h or "particular" in h), 1)
                    debit_col = next((i for i, h in enumerate(headers) if "debit" in h or "withdrawal" in h or "dr" in h), -1)
                    credit_col = next((i for i, h in enumerate(headers) if "credit" in h or "deposit" in h or "cr" in h), -1)
                    bal_col = next((i for i, h in enumerate(headers) if "balance" in h), -1)

                    for row_idx, row in enumerate(table[1:], start=2):
                        total_pdf_rows += 1
                        if not row or len(row) <= max(date_col, desc_col):
                            skipped.append(SkippedUnit(
                                unit_index=row_idx,
                                raw_content=str(row),
                                reason="Row has fewer columns than date/description index",
                            ))
                            continue

                        date_str = str(row[date_col]).strip() if row[date_col] else ""
                        narration = str(row[desc_col]).strip() if row[desc_col] else ""

                        if not date_str or date_str == "-":
                            skipped.append(SkippedUnit(
                                unit_index=row_idx,
                                raw_content=str(row),
                                reason="Empty or dash date string",
                            ))
                            continue

                        try:
                            dt = dateutil.parser.parse(date_str, dayfirst=True)
                            if dt.tzinfo is None:
                                dt = tz.localize(dt)
                            ts_utc = dt.astimezone(pytz.utc).isoformat()
                        except Exception as e:
                            errors.append(ParseErrorUnit(
                                unit_index=row_idx,
                                raw_content=str(row),
                                error=f"Invalid date format '{date_str}': {str(e)}",
                            ))
                            continue

                        debit_val = clean_amount(row[debit_col]) if debit_col != -1 and debit_col < len(row) else None
                        credit_val = clean_amount(row[credit_col]) if credit_col != -1 and credit_col < len(row) else None
                        balance_val = clean_amount(row[bal_col]) if bal_col != -1 and bal_col < len(row) else None

                        if debit_val and debit_val > 0:
                            kind = "debit"
                            amount = debit_val
                        elif credit_val and credit_val > 0:
                            kind = "credit"
                            amount = credit_val
                        else:
                            kind = "statement_row"
                            amount = 0.0

                        ref = {
                            "file": filename,
                            "page": page_idx,
                            "table_index": tbl_idx,
                            "row_index": row_idx,
                            "balance": balance_val,
                            "pdf_producer": pdf_metadata.get("Producer"),
                            "pdf_creation_date": pdf_metadata.get("CreationDate"),
                        }

                        events.append(
                            ParsedEvent(
                                evidence_id=evidence_id,
                                source_type="bank_pdf",
                                ts_utc=ts_utc,
                                ts_original=date_str,
                                tz_assumed=default_tz,
                                kind=kind,
                                actor=filename.replace(".pdf", ""),
                                text=narration,
                                amount=amount,
                                currency="INR",
                                ref=ref,
                            )
                        )

            if not valid_table_found:
                raise ValueError(
                    f"Bank PDF validation failed for '{filename}': No statement table with 'date' column found."
                )

        report = ParseReport(
            total_units=total_pdf_rows,
            parsed_events=len(events),
            skipped_units=skipped,
            errors=errors,
            unit_name="rows",
        )

        return events, report
