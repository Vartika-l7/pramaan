"""Timeline anomalies: chat gaps, out-of-order events, and spatial thread tracking."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime
from typing import Dict, List, Any
import dateutil.parser
import numpy as np

from backend.app.config import CHAT_GAP_MINUTES_MIN
from backend.app.correlate.base import deterministic_id


def detect_timeline_anomalies(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Detect forensic timeline anomalies: chat silence gaps and out-of-order timestamps."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, exhibit_id, source_type FROM evidence WHERE source_type = 'whatsapp';")
    whatsapp_exhibits = cursor.fetchall()

    anomalies: List[Dict[str, Any]] = []

    for ev in whatsapp_exhibits:
        ev_id = ev["id"]
        exhibit_id = ev["exhibit_id"]

        # Fetch messages in sequential line order
        cursor.execute(
            """
            SELECT id, ts_utc, ts_original, kind, text, ref_json
            FROM events
            WHERE evidence_id = ?
            ORDER BY rowid ASC;
            """,
            (ev_id,),
        )
        msg_rows = cursor.fetchall()
        if len(msg_rows) < 5:
            continue

        timestamps: List[datetime] = []
        valid_indices: List[int] = []

        for idx, r in enumerate(msg_rows):
            try:
                dt = dateutil.parser.parse(r["ts_utc"])
                timestamps.append(dt)
                valid_indices.append(idx)
            except Exception:
                pass

        if len(timestamps) < 5:
            continue

        # 1. Out-of-order timestamp detection (GT-05)
        for i in range(1, len(timestamps)):
            if timestamps[i] < timestamps[i - 1]:
                delta_sec = (timestamps[i - 1] - timestamps[i]).total_seconds()
                prev_row = msg_rows[valid_indices[i - 1]]
                curr_row = msg_rows[valid_indices[i]]

                anom_id = deterministic_id("anom_ooo", ev_id, prev_row["id"], curr_row["id"])
                desc = (
                    f"Out-of-order timestamp indicator: Message at {curr_row['ts_original']} "
                    f"appears after message at {prev_row['ts_original']} (inversion of {int(delta_sec)}s)."
                )
                detail = {
                    "type": "ANOMALY_OUT_OF_ORDER",
                    "preceding_time": prev_row["ts_original"],
                    "inverted_time": curr_row["ts_original"],
                    "delta_seconds": delta_sec,
                    "exhibit_id": exhibit_id,
                }

                cursor.execute(
                    """
                    INSERT OR IGNORE INTO anomalies (id, kind, severity, evidence_id, event_ids_json, description, detail_json, status)
                    VALUES (?, 'ANOMALY_OUT_OF_ORDER', 'MEDIUM', ?, ?, ?, ?, 'LEAD');
                    """,
                    (anom_id, ev_id, json.dumps([prev_row["id"], curr_row["id"]]), desc, json.dumps(detail)),
                )
                anomalies.append(detail)

        # 2. Chat silence gap detection (GT-04)
        # Threshold: max(3 * median_gap, 2h)
        deltas = [
            (timestamps[i] - timestamps[i - 1]).total_seconds() / 60.0
            for i in range(1, len(timestamps))
            if (timestamps[i] - timestamps[i - 1]).total_seconds() > 0
        ]
        if deltas:
            median_gap = float(np.median(deltas))
            threshold_min = max(3.0 * median_gap, float(CHAT_GAP_MINUTES_MIN))

            for i in range(1, len(timestamps)):
                gap_min = (timestamps[i] - timestamps[i - 1]).total_seconds() / 60.0
                if gap_min >= threshold_min:
                    row_before = msg_rows[valid_indices[i - 1]]
                    row_after = msg_rows[valid_indices[i]]

                    hours = int(gap_min // 60)
                    mins = int(gap_min % 60)
                    anom_id = deterministic_id("anom_gap", ev_id, row_before["id"], row_after["id"])
                    desc = (
                        f"Chat silence gap indicator: {hours}h {mins}m unexplained gap "
                        f"between {row_before['ts_original']} and {row_after['ts_original']} (threshold: {int(threshold_min)}m)."
                    )
                    detail = {
                        "type": "ANOMALY_CHAT_GAP",
                        "gap_duration_minutes": round(gap_min, 1),
                        "gap_start": row_before["ts_original"],
                        "gap_end": row_after["ts_original"],
                        "exhibit_id": exhibit_id,
                    }

                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO anomalies (id, kind, severity, evidence_id, event_ids_json, description, detail_json, status)
                        VALUES (?, 'ANOMALY_CHAT_GAP', 'HIGH', ?, ?, ?, ?, 'LEAD');
                        """,
                        (anom_id, ev_id, json.dumps([row_before["id"], row_after["id"]]), desc, json.dumps(detail)),
                    )
                    anomalies.append(detail)

    conn.commit()
    return anomalies


def detect_spatial_movement(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Track cell tower transitions across locations between events (GT-10)."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.id, e.evidence_id, e.ts_utc, e.ts_original, e.location_id, e.ref_json, ev.exhibit_id
        FROM events e
        JOIN evidence ev ON e.evidence_id = ev.id
        WHERE e.source_type = 'calllog' AND e.location_id IS NOT NULL
        ORDER BY e.ts_utc ASC;
        """
    )
    rows = cursor.fetchall()
    transitions = []

    for i in range(1, len(rows)):
        r1, r2 = rows[i - 1], rows[i]
        ref1 = json.loads(r1["ref_json"])
        ref2 = json.loads(r2["ref_json"])
        loc1 = ref1.get("location_name", "")
        loc2 = ref2.get("location_name", "")

        city1 = loc1.split()[0] if loc1 else ""
        city2 = loc2.split()[0] if loc2 else ""

        if city1 and city2 and city1.lower() != city2.lower():
            anom_id = deterministic_id("anom_spatial", r1["id"], r2["id"])
            desc = f"Spatial location transition indicator: Handset moved from {loc1} to {loc2} between calls."
            detail = {
                "type": "SPATIAL_THREAD",
                "origin_location": loc1,
                "origin_tower": ref1.get("cell_tower_id"),
                "origin_time": r1["ts_original"],
                "destination_location": loc2,
                "destination_tower": ref2.get("cell_tower_id"),
                "destination_time": r2["ts_original"],
            }
            cursor.execute(
                """
                INSERT OR IGNORE INTO anomalies (id, kind, severity, evidence_id, event_ids_json, description, detail_json, status)
                VALUES (?, 'SPATIAL_THREAD', 'MEDIUM', ?, ?, ?, ?, 'LEAD');
                """,
                (anom_id, r2["evidence_id"], json.dumps([r1["id"], r2["id"]]), desc, json.dumps(detail)),
            )
            transitions.append(detail)

    conn.commit()
    return transitions

