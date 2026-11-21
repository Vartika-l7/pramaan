"""Deterministic Digital Crime Scene Reconstruction Engine (B7)."""

from __future__ import annotations

import json
import sqlite3
from typing import Any, Dict, List, Optional


def _resolve_window(
    conn: sqlite3.Connection,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    episode_id: Optional[str] = None,
) -> Dict[str, Optional[str]]:
    if episode_id:
        cursor = conn.cursor()
        cursor.execute("SELECT start_ts_utc, end_ts_utc, title FROM episodes WHERE id = ?;", (episode_id,))
        row = cursor.fetchone()
        if row:
            return {
                "start_ts_utc": row["start_ts_utc"],
                "end_ts_utc": row["end_ts_utc"],
                "episode_id": episode_id,
                "episode_title": row["title"],
            }
    return {
        "start_ts_utc": start_ts,
        "end_ts_utc": end_ts,
        "episode_id": episode_id,
        "episode_title": None,
    }


def reconstruct_scene(
    conn: sqlite3.Connection,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    episode_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Reconstruct a digital crime scene for a time window or episode with full source references."""
    window = _resolve_window(conn, start_ts, end_ts, episode_id)
    w_start = window["start_ts_utc"]
    w_end = window["end_ts_utc"]

    cursor = conn.cursor()
    where_clauses = []
    params: List[Any] = []
    if w_start:
        where_clauses.append("ev.ts_utc >= ?")
        params.append(w_start)
    if w_end:
        where_clauses.append("ev.ts_utc <= ?")
        params.append(w_end)

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""

    cursor.execute(
        f"""
        SELECT ev.*, evi.exhibit_id, evi.filename
        FROM events ev
        JOIN evidence evi ON ev.evidence_id = evi.id
        {where_sql}
        ORDER BY ev.ts_utc ASC, ev.id ASC;
        """,
        params,
    )
    event_rows = cursor.fetchall()
    event_ids = [r["id"] for r in event_rows]

    events_out = []
    exhibits_map: Dict[str, Dict[str, Any]] = {}
    all_actors = set()

    for r in event_rows:
        try:
            ref = json.loads(r["ref_json"])
        except Exception:
            ref = {}
        if r["actor"]:
            all_actors.add(r["actor"])
        exhibits_map[r["exhibit_id"]] = {
            "exhibit_id": r["exhibit_id"],
            "filename": r["filename"],
            "source_type": r["source_type"],
        }
        events_out.append({
            "id": r["id"],
            "exhibit_id": r["exhibit_id"],
            "source_type": r["source_type"],
            "ts_utc": r["ts_utc"],
            "ts_original": r["ts_original"],
            "tz_assumed": r["tz_assumed"],
            "clock_offset_seconds": int(r["clock_offset_seconds"] or 0),
            "offset_source": r["offset_source"],
            "actor": r["actor"],
            "counterparty": r["counterparty"],
            "kind": r["kind"],
            "text": r["text"],
            "ref": ref,
        })

    # Fetch spatial observations in window
    obs_where = []
    obs_params: List[Any] = []
    if w_start:
        obs_where.append("o.end_ts_utc >= ?")
        obs_params.append(w_start)
    if w_end:
        obs_where.append("o.start_ts_utc <= ?")
        obs_params.append(w_end)
    obs_sql = ("WHERE " + " AND ".join(obs_where)) if obs_where else ""

    cursor.execute(
        f"""
        SELECT o.*, ev.exhibit_id
        FROM observations o
        JOIN events e ON o.source_event_id = e.id
        JOIN evidence ev ON e.evidence_id = ev.id
        {obs_sql}
        ORDER BY o.start_ts_utc ASC;
        """,
        obs_params,
    )
    obs_rows = cursor.fetchall()

    locations_map: Dict[str, Dict[str, Any]] = {}
    presence: List[Dict[str, Any]] = []
    established_actors = set()

    for o in obs_rows:
        established_actors.add(o["entity_or_device"])
        loc_key = o["location_id"] or o["place_name"]
        if loc_key not in locations_map:
            locations_map[loc_key] = {
                "location_id": o["location_id"],
                "place_name": o["place_name"],
                "lat": o["lat"],
                "lon": o["lon"],
                "first_seen_utc": o["start_ts_utc"],
                "last_seen_utc": o["end_ts_utc"],
                "source_types": [o["source_type"]],
            }
        else:
            if o["end_ts_utc"] > locations_map[loc_key]["last_seen_utc"]:
                locations_map[loc_key]["last_seen_utc"] = o["end_ts_utc"]
            if o["source_type"] not in locations_map[loc_key]["source_types"]:
                locations_map[loc_key]["source_types"].append(o["source_type"])

        presence.append({
            "entity_or_device": o["entity_or_device"],
            "entity_type": o["entity_type"],
            "place_name": o["place_name"],
            "lat": o["lat"],
            "lon": o["lon"],
            "start_ts_utc": o["start_ts_utc"],
            "end_ts_utc": o["end_ts_utc"],
            "accuracy_m": o["accuracy_m"],
            "source_event_id": o["source_event_id"],
            "exhibit_id": o["exhibit_id"],
            "source_type": o["source_type"],
            "status": "established",
        })

    # Explicitly mark actors in the window whose physical location is NOT established
    for act in sorted(all_actors - established_actors):
        presence.append({
            "entity_or_device": act,
            "entity_type": "ACTOR",
            "place_name": "not established",
            "lat": None,
            "lon": None,
            "start_ts_utc": w_start,
            "end_ts_utc": w_end,
            "accuracy_m": None,
            "source_event_id": None,
            "exhibit_id": None,
            "source_type": None,
            "status": "not established",
        })

    # Anomalies overlapping the window
    cursor.execute("SELECT * FROM anomalies;")
    anomalies_in_window = []
    ev_id_set = set(event_ids)
    for a in cursor.fetchall():
        try:
            a_eids = json.loads(a["event_ids_json"])
        except Exception:
            a_eids = []
        if not event_ids or any(eid in ev_id_set for eid in a_eids):
            anomalies_in_window.append({
                "id": a["id"],
                "kind": a["kind"],
                "severity": a["severity"],
                "description": a["description"],
                "status": a["status"],
                "event_ids": a_eids,
            })

    return {
        "window": window,
        "locations": list(locations_map.values()),
        "presence": presence,
        "events": events_out,
        "exhibits": list(exhibits_map.values()),
        "anomalies": anomalies_in_window,
    }


def replay_scene(
    conn: sqlite3.Connection,
    start_ts: Optional[str] = None,
    end_ts: Optional[str] = None,
    episode_id: Optional[str] = None,
) -> Dict[str, Any]:
    """Return an ordered step-by-step replay of the crime scene."""
    scene = reconstruct_scene(conn, start_ts=start_ts, end_ts=end_ts, episode_id=episode_id)
    obs_by_event = {p["source_event_id"]: p for p in scene["presence"] if p.get("source_event_id")}
    anom_by_event: Dict[str, List[Dict[str, Any]]] = {}
    for a in scene["anomalies"]:
        for eid in a.get("event_ids", []):
            anom_by_event.setdefault(eid, []).append(a)

    steps = []
    for idx, ev in enumerate(scene["events"], start=1):
        obs = obs_by_event.get(ev["id"])
        steps.append({
            "step": idx,
            "event_id": ev["id"],
            "ts_utc": ev["ts_utc"],
            "ts_original": ev["ts_original"],
            "clock_offset_seconds": ev["clock_offset_seconds"],
            "offset_source": ev["offset_source"],
            "actor": ev["actor"],
            "place_name": obs["place_name"] if obs else "not established",
            "exhibit_id": ev["exhibit_id"],
            "source_type": ev["source_type"],
            "kind": ev["kind"],
            "text": ev["text"],
            "anomalies": anom_by_event.get(ev["id"], []),
        })

    return {
        "window": scene["window"],
        "total_steps": len(steps),
        "steps": steps,
    }
