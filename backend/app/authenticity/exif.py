"""EXIF metadata tampering inspection and image authenticity indicators."""

from __future__ import annotations

import json
import sqlite3
import uuid
from pathlib import Path
from typing import Dict, List, Any
import exifread
import dateutil.parser

from backend.app.config import CASE_DATA_DIR, ELA_HOTSPOT_THRESHOLD
from backend.app.authenticity.ela import compute_ela_heatmap, ELA_DIR
from backend.app.correlate.base import deterministic_id

KNOWN_EDITORS = ["pixelmod", "photoshop", "gimp", "canva", "snapseed", "lightroom", "picsart"]


def inspect_image_authenticity(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    """Scan all ingested image exhibits for EXIF metadata modifications and ELA hotspots (GT-06)."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT e.id as event_id, ev.id as evidence_id, ev.exhibit_id, ev.filename, ev.stored_path, ev.sha256, e.ref_json
        FROM events e
        JOIN evidence ev ON e.evidence_id = ev.id
        WHERE e.source_type = 'image';
        """
    )
    img_rows = cursor.fetchall()
    anomalies: List[Dict[str, Any]] = []

    for row in img_rows:
        evidence_id = row["evidence_id"]
        exhibit_id = row["exhibit_id"]
        event_id = row["event_id"]
        stored_path = Path(row["stored_path"])
        sha256 = row["sha256"]

        if not stored_path.exists():
            continue

        ref = json.loads(row["ref_json"])
        exif = ref.get("exif", {})

        # 1. EXIF Software Check
        software = exif.get("Image Software", "")
        editor_detected = None
        for ed in KNOWN_EDITORS:
            if ed in software.lower():
                editor_detected = software
                break

        # 2. DateTime Comparison
        dt_original = exif.get("EXIF DateTimeOriginal")
        dt_modified = exif.get("Image DateTime")
        mod_later = False

        if dt_original and dt_modified:
            try:
                # Format: "YYYY:MM:DD HH:MM:SS"
                fmt_orig = dt_original.replace(":", "-", 2)
                fmt_mod = dt_modified.replace(":", "-", 2)
                parsed_orig = dateutil.parser.parse(fmt_orig)
                parsed_mod = dateutil.parser.parse(fmt_mod)
                if parsed_mod > parsed_orig:
                    mod_later = True
            except Exception:
                pass

        # 3. ELA Heatmap
        heatmap_path = ELA_DIR / f"{sha256}_ela.png"
        try:
            hotspot_ratio, _ = compute_ela_heatmap(stored_path, heatmap_path)
        except Exception:
            hotspot_ratio = 0.0

        is_suspicious = (editor_detected is not None) or mod_later or (hotspot_ratio > ELA_HOTSPOT_THRESHOLD)

        if is_suspicious:
            anom_id = deterministic_id("anom_img", evidence_id, event_id)
            reasons = []
            if editor_detected:
                reasons.append(f"Image editor signature '{editor_detected}' detected in EXIF Software tag")
            if mod_later:
                reasons.append(f"Modification timestamp ({dt_modified}) is later than creation timestamp ({dt_original})")
            if hotspot_ratio > ELA_HOTSPOT_THRESHOLD:
                reasons.append(f"Elevated ELA compression artifact hotspot ratio ({hotspot_ratio * 100:.1f}%)")

            desc = f"Image modification indicator: {'; '.join(reasons)}. (Forensic indicator only, not conclusive proof)."
            detail = {
                "type": "ANOMALY_IMAGE_EDITED",
                "exhibit_id": exhibit_id,
                "software": editor_detected,
                "datetime_original": dt_original,
                "datetime_modified": dt_modified,
                "hotspot_ratio": round(hotspot_ratio, 3),
                "ela_heatmap_path": str(heatmap_path),
            }

            cursor.execute(
                """
                INSERT OR IGNORE INTO anomalies (id, kind, severity, evidence_id, event_ids_json, description, detail_json, status)
                VALUES (?, 'ANOMALY_IMAGE_EDITED', 'HIGH', ?, ?, ?, ?, 'LEAD');
                """,
                (anom_id, evidence_id, json.dumps([event_id]), desc, json.dumps(detail)),
            )
            anomalies.append(detail)

    conn.commit()
    return anomalies

