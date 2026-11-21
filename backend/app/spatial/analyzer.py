"""Spatio-temporal observation builder and travel/co-location analyzer (B3)."""

from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
import dateutil.parser

from backend.app.config import (
    COLOCATION_RADIUS_METERS,
    COLOCATION_WINDOW_MINUTES,
    IMPOSSIBLE_TRAVEL_SPEED_KMH,
)
from backend.app.spatial.geo import haversine_km, load_tower_registry, load_gazetteer


def _det_id(prefix: str, *parts: str) -> str:
    raw = "|".join(str(p) for p in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


def _upsert_location(
    cursor: sqlite3.Cursor,
    name: str,
    lat: Optional[float],
    lon: Optional[float],
    kind: str,
) -> str:
    loc_id = _det_id("loc", name.lower(), kind)
    cursor.execute(
        """
        INSERT OR IGNORE INTO locations (id, name, lat, lon, kind)
        VALUES (?, ?, ?, ?, ?);
        """,
        (loc_id, name, lat, lon, kind),
    )
    return loc_id


def build_spatial_observations(conn: sqlite3.Connection) -> Dict[str, int]:
    """Populate `locations` and `observations` from call logs, cloud location history, CCTV, and chat gazetteer."""
    cursor = conn.cursor()
    # Clear and rebuild observations deterministically
    cursor.execute("DELETE FROM observations;")

    towers = load_tower_registry()
    gazetteer = load_gazetteer()
    gaz_patterns = [
        (re.compile(rf"\b{re.escape(c['city'])}\b", re.IGNORECASE), c)
        for c in gazetteer
    ]

    cursor.execute("SELECT * FROM events ORDER BY ts_utc ASC;")
    events = cursor.fetchall()
    obs_count = 0

    def add_obs(
        entity_or_device: str,
        entity_type: str,
        place_name: str,
        lat: Optional[float],
        lon: Optional[float],
        start_ts: str,
        end_ts: str,
        accuracy_m: float,
        source_event_id: str,
        source_type: str,
        loc_kind: str,
    ):
        nonlocal obs_count
        loc_id = _upsert_location(cursor, place_name, lat, lon, loc_kind)
        obs_id = _det_id("obs", entity_or_device, place_name, start_ts, source_type)
        cursor.execute(
            """
            INSERT OR IGNORE INTO observations
            (id, entity_or_device, entity_type, location_id, place_name, lat, lon, start_ts_utc, end_ts_utc, accuracy_m, source_event_id, source_type)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                obs_id,
                entity_or_device,
                entity_type,
                loc_id,
                place_name,
                lat,
                lon,
                start_ts,
                end_ts,
                accuracy_m,
                source_event_id,
                source_type,
            ),
        )
        obs_count += 1

    for ev in events:
        try:
            ref = json.loads(ev["ref_json"])
        except Exception:
            ref = {}

        st = ev["source_type"]
        if st == "calllog":
            tower_id = ref.get("cell_tower_id") or ev["location_id"]
            if tower_id and tower_id in towers:
                t = towers[tower_id]
                dev = ref.get("device_id") or ev["actor"] or "UnknownDevice"
                add_obs(
                    dev,
                    "DEVICE",
                    t["location_name"],
                    t["lat"],
                    t["lon"],
                    ev["ts_utc"],
                    ev["ts_utc"],
                    t["accuracy_m"],
                    ev["id"],
                    st,
                    "CELL_TOWER",
                )
        elif st == "cloud_location":
            lat = ref.get("lat")
            lon = ref.get("lon")
            acc = float(ref.get("accuracy_m") or 50.0)
            dev = ref.get("device_id") or ref.get("account") or ev["actor"] or "CloudDevice"
            place = ref.get("place_name") or f"{lat},{lon}"
            if lat is not None and lon is not None:
                add_obs(
                    dev,
                    "DEVICE",
                    place,
                    float(lat),
                    float(lon),
                    ev["ts_utc"],
                    ev["ts_utc"],
                    acc,
                    ev["id"],
                    st,
                    "CLOUD_GPS",
                )
        elif st == "cctv_index":
            lat = ref.get("lat")
            lon = ref.get("lon")
            place = ref.get("location_name") or ev["location_id"] or "CCTV"
            end_ts = ref.get("clip_end_utc") or ev["ts_utc"]
            subject = ev["actor"] or ref.get("camera_id") or "CCTV_SUBJECT"
            if lat is not None and lon is not None:
                add_obs(
                    subject,
                    "PERSON" if ev["actor"] and ev["actor"] != ref.get("camera_id") else "CAMERA",
                    place,
                    float(lat),
                    float(lon),
                    ev["ts_utc"],
                    end_ts,
                    25.0,
                    ev["id"],
                    st,
                    "CCTV_CAMERA",
                )
        elif st in ("whatsapp", "social_telegram", "social_generic") and ev["text"]:
            for pat, city_info in gaz_patterns:
                if pat.search(ev["text"]):
                    actor = ev["actor"] or "Unknown"
                    add_obs(
                        actor,
                        "PERSON",
                        city_info["city"],
                        city_info["lat"],
                        city_info["lon"],
                        ev["ts_utc"],
                        ev["ts_utc"],
                        city_info["accuracy_m"],
                        ev["id"],
                        st,
                        "GAZETTEER_CITY",
                    )

    conn.commit()
    return {"observations": obs_count}


def analyze_spatial_relationships(conn: sqlite3.Connection) -> Dict[str, Any]:
    """Derive CO_LOCATED, TRAVELLED, and IMPOSSIBLE_TRAVEL from `observations`."""
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM observations WHERE lat IS NOT NULL AND lon IS NOT NULL ORDER BY start_ts_utc ASC;")
    obs_rows = cursor.fetchall()

    co_located: List[Dict[str, Any]] = []
    travelled: List[Dict[str, Any]] = []
    impossible_travel: List[Dict[str, Any]] = []

    # 1. Consecutive observations per entity_or_device -> TRAVELLED & IMPOSSIBLE_TRAVEL
    by_entity: Dict[str, List[sqlite3.Row]] = {}
    for row in obs_rows:
        by_entity.setdefault(row["entity_or_device"], []).append(row)

    for entity, items in by_entity.items():
        for i in range(1, len(items)):
            o1, o2 = items[i - 1], items[i]
            dist_km = haversine_km(o1["lat"], o1["lon"], o2["lat"], o2["lon"])
            t1 = dateutil.parser.parse(o1["start_ts_utc"])
            t2 = dateutil.parser.parse(o2["start_ts_utc"])
            elapsed_hours = max((t2 - t1).total_seconds() / 3600.0, 1e-6)
            elapsed_minutes = (t2 - t1).total_seconds() / 60.0
            speed_kmh = dist_km / elapsed_hours

            # Ignore tiny jitter within combined accuracy
            min_move_km = (COLOCATION_RADIUS_METERS + o1["accuracy_m"] + o2["accuracy_m"]) / 1000.0
            if dist_km > min_move_km:
                rec = {
                    "entity_or_device": entity,
                    "from_place": o1["place_name"],
                    "to_place": o2["place_name"],
                    "from_ts_utc": o1["start_ts_utc"],
                    "to_ts_utc": o2["start_ts_utc"],
                    "distance_km": round(dist_km, 2),
                    "elapsed_minutes": round(elapsed_minutes, 1),
                    "implied_speed_kmh": round(speed_kmh, 1),
                    "event_ids": [o1["source_event_id"], o2["source_event_id"]],
                }
                travelled.append(rec)

                if speed_kmh > IMPOSSIBLE_TRAVEL_SPEED_KMH:
                    impossible_travel.append(rec)
                    anom_id = _det_id("anom_imp", entity, o1["source_event_id"], o2["source_event_id"])
                    desc = (
                        f"IMPOSSIBLE_TRAVEL: {entity} observed at {o1['place_name']} and {o2['place_name']} "
                        f"({dist_km:.1f} km apart in {elapsed_minutes:.1f} min -> {speed_kmh:.1f} km/h > {IMPOSSIBLE_TRAVEL_SPEED_KMH} km/h)."
                    )
                    cursor.execute(
                        """
                        INSERT OR IGNORE INTO anomalies (id, kind, severity, evidence_id, event_ids_json, description, detail_json, status)
                        SELECT ?, 'IMPOSSIBLE_TRAVEL', 'HIGH', e.evidence_id, ?, ?, ?, 'LEAD'
                        FROM events e WHERE e.id = ?;
                        """,
                        (
                            anom_id,
                            json.dumps(rec["event_ids"]),
                            desc,
                            json.dumps(rec),
                            o2["source_event_id"],
                        ),
                    )

    # 2. Cross-entity CO_LOCATED within radius (widened by stated accuracy) and time window
    for i in range(len(obs_rows)):
        o1 = obs_rows[i]
        t1 = dateutil.parser.parse(o1["start_ts_utc"])
        for j in range(i + 1, len(obs_rows)):
            o2 = obs_rows[j]
            if o1["entity_or_device"] == o2["entity_or_device"]:
                continue
            t2 = dateutil.parser.parse(o2["start_ts_utc"])
            dt_min = abs((t2 - t1).total_seconds()) / 60.0
            if dt_min > COLOCATION_WINDOW_MINUTES:
                if t2 > t1:
                    break
                continue
            dist_m = haversine_km(o1["lat"], o1["lon"], o2["lat"], o2["lon"]) * 1000.0
            max_radius_m = COLOCATION_RADIUS_METERS + float(o1["accuracy_m"]) + float(o2["accuracy_m"])
            if dist_m <= max_radius_m:
                co_located.append({
                    "entity_1": o1["entity_or_device"],
                    "entity_2": o2["entity_or_device"],
                    "place_1": o1["place_name"],
                    "place_2": o2["place_name"],
                    "distance_m": round(dist_m, 1),
                    "effective_radius_m": round(max_radius_m, 1),
                    "time_diff_minutes": round(dt_min, 1),
                    "event_ids": [o1["source_event_id"], o2["source_event_id"]],
                })

    conn.commit()
    return {
        "co_located": co_located,
        "travelled": travelled,
        "impossible_travel": impossible_travel,
    }
