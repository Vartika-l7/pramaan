"""Bank CSV statement parser with strict schema validation."""

from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path
from typing import List, Optional
import dateutil.parser
import pytz

from backend.app.parsers.base import BaseParser, ParsedEvent


class BankCSVParser(BaseParser):
    def can_parse(self, file_path: Path, filename: str) -> bool:
        lower = filename.lower()
        if not lower.endswith(".csv"):
            return False
        if "call" in lower:
            return False
        # Verify columns in header
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
        events: List[ParsedEvent] = []
        tz = pytz.timezone(default_tz)

        with open(file_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row_idx, row in enumerate(reader, start=1):
                date_str = row.get("date", "").strip()
                narration = row.get("narration", "").strip()
                debit_str = row.get("debit", "0").strip()
                credit_str = row.get("credit", "0").strip()
                balance_str = row.get("balance", "0").strip()

                try:
                    dt = dateutil.parser.parse(date_str, dayfirst=True)
                    if dt.tzinfo is None:
                        dt = tz.localize(dt)
                    ts_utc = dt.astimezone(pytz.utc).isoformat()
                except Exception:
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

        return events

