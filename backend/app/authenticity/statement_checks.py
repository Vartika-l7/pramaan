"""Bank statement running-balance arithmetic verification and PDF metadata checks."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Dict, List, Any, Optional
from backend.app.correlate.base import deterministic_id


def verify_statement_arithmetic(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Verify running balance arithmetic row-by-row across all ingested bank statements (GT-08)."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, exhibit_id, filename, source_type
        FROM evidence
        WHERE source_type IN ('bank_pdf', 'bank_csv');
        """
    )
    statement_exhibits = cursor.fetchall()
    anomalies: List[Dict[str, Any]] = []

    for ev in statement_exhibits:
        ev_id = ev["id"]
        exhibit_id = ev["exhibit_id"]
        filename = ev["filename"]

        cursor.execute(
            """
            SELECT id, ts_utc, ts_original, kind, amount, text, ref_json
            FROM events
            WHERE evidence_id = ?
            ORDER BY rowid ASC;
            """,
            (ev_id,),
        )
        rows = cursor.fetchall()
        if not rows:
            continue

        running_balance: Optional[float] = None
        failing_row = None

        for idx, r in enumerate(rows, start=1):
            ref = json.loads(r["ref_json"])
            stated_bal = ref.get("balance")
            kind = r["kind"]
            amount = r["amount"] or 0.0

            if stated_bal is None:
                continue

            if running_balance is None:
                # Initialize opening balance
                running_balance = stated_bal
                continue

            # Compute expected balance
            if kind == "credit":
                expected_bal = running_balance + amount
            elif kind == "debit":
                expected_bal = running_balance - amount
            else:
                expected_bal = running_balance

            # Check for discrepancy (> 0.01 margin for floating point)
            if abs(expected_bal - stated_bal) > 0.05:
                failing_row = {
                    "event_id": r["id"],
                    "row_index": ref.get("row_index", idx),
                    "page": ref.get("page", 1),
                    "date": r["ts_original"],
                    "narration": r["text"],
                    "kind": kind,
                    "amount": amount,
                    "stated_balance": stated_bal,
                    "expected_balance": round(expected_bal, 2),
                    "discrepancy": round(stated_bal - expected_bal, 2),
                }
                break

            running_balance = stated_bal

        if failing_row:
            anom_id = deterministic_id("anom_bal", ev_id, failing_row["event_id"])
            desc = (
                f"Bank statement arithmetic discrepancy indicator: Row {failing_row['row_index']} "
                f"stated balance of INR {failing_row['stated_balance']:,.2f} differs from expected "
                f"running balance of INR {failing_row['expected_balance']:,.2f} (delta: INR {failing_row['discrepancy']:+,.2f})."
            )
            detail = {
                "type": "ANOMALY_BALANCE_MISMATCH",
                "exhibit_id": exhibit_id,
                "filename": filename,
                "failing_row": failing_row,
            }

            cursor.execute(
                """
                INSERT OR IGNORE INTO anomalies (id, kind, severity, evidence_id, event_ids_json, description, detail_json, status)
                VALUES (?, 'ANOMALY_BALANCE_MISMATCH', 'HIGH', ?, ?, ?, ?, 'LEAD');
                """,
                (anom_id, ev_id, json.dumps([failing_row["event_id"]]), desc, json.dumps(detail)),
            )
            anomalies.append(detail)

    conn.commit()
    return anomalies


def get_statement_balance_breakdown(conn: sqlite3.Connection, evidence_id: str) -> Dict[str, Any]:
    """Retrieve row-by-row arithmetic verification for the Authenticity Statement viewer."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM evidence WHERE id = ? OR exhibit_id = ?;", (evidence_id, evidence_id))
    ev = cursor.fetchone()
    if not ev:
        return {"error": "Statement not found"}

    cursor.execute(
        """
        SELECT id, ts_utc, ts_original, kind, amount, text, ref_json
        FROM events
        WHERE evidence_id = ?
        ORDER BY rowid ASC;
        """,
        (ev["id"],),
    )
    events = cursor.fetchall()

    rows = []
    running_balance: Optional[float] = None
    has_mismatch = False

    for idx, r in enumerate(events, start=1):
        ref = json.loads(r["ref_json"])
        stated_bal = ref.get("balance")
        kind = r["kind"]
        amount = r["amount"] or 0.0

        expected_bal = stated_bal
        match_status = "PASS"

        if stated_bal is not None:
            if running_balance is None:
                running_balance = stated_bal
                expected_bal = stated_bal
            else:
                if kind == "credit":
                    expected_bal = running_balance + amount
                elif kind == "debit":
                    expected_bal = running_balance - amount
                else:
                    expected_bal = running_balance

                if abs(expected_bal - stated_bal) > 0.05:
                    match_status = "FAIL"
                    has_mismatch = True

                running_balance = stated_bal

        rows.append({
            "event_id": r["id"],
            "row_index": ref.get("row_index", idx),
            "date": r["ts_original"],
            "narration": r["text"],
            "kind": kind,
            "amount": amount,
            "stated_balance": stated_bal,
            "expected_balance": round(expected_bal, 2) if expected_bal is not None else None,
            "status": match_status,
        })

    return {
        "exhibit_id": ev["exhibit_id"],
        "filename": ev["filename"],
        "has_arithmetic_mismatch": has_mismatch,
        "rows": rows,
    }

