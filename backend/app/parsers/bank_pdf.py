"""Bank statement PDF parser using pdfplumber."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import dateutil.parser
import pdfplumber
import pytz

from backend.app.parsers.base import BaseParser, ParsedEvent


def clean_amount(val: Optional[str]) -> Optional[float]:
    if not val or val.strip() in ("-", "", "None"):
        return None
    # Remove commas, currency symbols, and whitespace
    cleaned = re.sub(r"[^\d.]", "", val)
    try:
        return float(cleaned)
    except ValueError:
        return None


class BankPDFParser(BaseParser):
    def can_parse(self, file_path: Path, filename: str) -> bool:
        return filename.lower().endswith(".pdf")

    def parse(
        self,
        file_path: Path,
        evidence_id: str,
        filename: str,
        default_tz: str = "Asia/Kolkata",
    ) -> List[ParsedEvent]:
        events: List[ParsedEvent] = []
        tz = pytz.timezone(default_tz)

        try:
            with pdfplumber.open(file_path) as pdf:
                pdf_metadata = dict(pdf.metadata) if pdf.metadata else {}

                for page_idx, page in enumerate(pdf.pages, start=1):
                    tables = page.extract_tables()
                    for tbl_idx, table in enumerate(tables):
                        if not table or len(table) < 2:
                            continue

                        headers = [str(c).lower().strip() if c else "" for c in table[0]]
                        
                        # Find indices for Date, Narration, Debit, Credit, Balance
                        date_col = next((i for i, h in enumerate(headers) if "date" in h), 0)
                        desc_col = next((i for i, h in enumerate(headers) if "narration" in h or "desc" in h or "particular" in h), 1)
                        debit_col = next((i for i, h in enumerate(headers) if "debit" in h or "withdrawal" in h or "dr" in h), -1)
                        credit_col = next((i for i, h in enumerate(headers) if "credit" in h or "deposit" in h or "cr" in h), -1)
                        bal_col = next((i for i, h in enumerate(headers) if "balance" in h), -1)

                        for row_idx, row in enumerate(table[1:], start=1):
                            if not row or len(row) <= max(date_col, desc_col):
                                continue

                            date_str = str(row[date_col]).strip() if row[date_col] else ""
                            narration = str(row[desc_col]).strip() if row[desc_col] else ""

                            if not date_str or date_str == "-":
                                continue

                            # Attempt to parse date
                            try:
                                dt = dateutil.parser.parse(date_str, dayfirst=True)
                                if dt.tzinfo is None:
                                    dt = tz.localize(dt)
                                ts_utc = dt.astimezone(pytz.utc).isoformat()
                            except Exception:
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
                                "pdf_mod_date": pdf_metadata.get("ModDate"),
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
        except Exception as e:
            # Degrade gracefully
            pass

        return events

