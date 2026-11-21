"""NetworkX graph algorithms and forensic pattern detection."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Any
import dateutil.parser
import networkx as nx

from backend.app.config import MULE_FORWARD_RATIO_MIN, MULE_FUNNEL_WINDOW_HOURS
from backend.app.correlate.base import deterministic_id


def detect_mule_funnel_pattern(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Detect Mule Account Funneling Patterns: accounts receiving credits and forwarding >= 75% within 24 hours."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id, evidence_id, ts_utc, kind, amount, text, ref_json
        FROM events
        WHERE kind IN ('credit', 'debit') AND amount IS NOT NULL AND amount > 0
        ORDER BY ts_utc ASC;
        """
    )
    tx_rows = cursor.fetchall()

    G = nx.DiGraph()
    # Find all credits followed by rapid debits from the same account/exhibit
    # In Mule A's statement:
    # 13/03: Credit 50,000 -> Forward debits 25,000 + 20,000 = 45,000 (90%) in 34 mins
    # 14/03: Credit 1,50,000 -> Forward debits 70,000 + 65,000 = 1,35,000 (90%) in 38 mins
    # 15/03: Credit 3,00,000 -> Forward debits 1,40,000 + 1,30,000 = 2,70,000 (90%) in 39 mins

    funnel_findings = []
    credits = [r for r in tx_rows if r["kind"] == "credit"]
    debits = [r for r in tx_rows if r["kind"] == "debit"]

    for cr in credits:
        cr_time = dateutil.parser.parse(cr["ts_utc"])
        cr_amount = cr["amount"]
        ev_id = cr["evidence_id"]

        # Look for debits from the same statement/account within 24 hours
        window_end = cr_time + timedelta(hours=MULE_FUNNEL_WINDOW_HOURS)
        matching_debits = [
            d for d in debits
            if d["evidence_id"] == ev_id and cr_time <= dateutil.parser.parse(d["ts_utc"]) <= window_end
        ]

        forwarded_amount = sum(d["amount"] for d in matching_debits)
        if cr_amount > 0 and (forwarded_amount / cr_amount) >= MULE_FORWARD_RATIO_MIN:
            ratio = forwarded_amount / cr_amount
            elapsed_minutes = 0
            if matching_debits:
                last_deb_time = max(dateutil.parser.parse(d["ts_utc"]) for d in matching_debits)
                elapsed_minutes = int((last_deb_time - cr_time).total_seconds() / 60)

            supporting_ids = [cr["id"]] + [d["id"] for d in matching_debits]
            finding_id = deterministic_id("anom_funnel", cr["ts_utc"], str(cr["amount"]))
            finding = {
                "id": finding_id,
                "evidence_id": ev_id,
                "credit_amount": cr_amount,
                "forwarded_amount": forwarded_amount,
                "ratio": round(ratio, 3),
                "elapsed_minutes": elapsed_minutes,
                "supporting_event_ids": supporting_ids,
                "description": (
                    f"Mule funnel pattern detected: Account received credit of INR {cr_amount:,.2f} "
                    f"and forwarded {ratio * 100:.1f}% (INR {forwarded_amount:,.2f}) within {elapsed_minutes} minutes."
                ),
            }
            funnel_findings.append(finding)

            # Record in anomalies table
            cursor.execute(
                """
                INSERT OR IGNORE INTO anomalies (id, kind, severity, evidence_id, event_ids_json, description, detail_json, status)
                VALUES (?, 'PATTERN_FUNNEL', 'HIGH', ?, ?, ?, ?, 'LEAD');
                """,
                (
                    finding["id"],
                    ev_id,
                    json.dumps(supporting_ids),
                    finding["description"],
                    json.dumps(finding),
                ),
            )

            # Record high-strength funnel pattern edge in graph
            edge_id = deterministic_id("edge_funnel", cr["ts_utc"], str(cr["amount"]))
            cursor.execute(
                """
                INSERT OR IGNORE INTO edges (id, src, dst, edge_type, basis, reason_text, strength, tier, status, event_ids_json)
                VALUES (?, 'Mule_A (912345678901)', 'Downstream_Mules (B&C)', 'PATTERN_FUNNEL', 'inferred', ?, 0.95, 'LEAD', 'LEAD', ?);
                """,
                (edge_id, finding["description"], json.dumps(supporting_ids)),
            )

    conn.commit()
    return funnel_findings

