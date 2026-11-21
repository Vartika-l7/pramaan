"""Deterministic Automated Event-Sequence Generator (B6)."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
import dateutil.parser

from backend.app.config import EPISODE_GAP_MINUTES


def _kind_group(kind: str) -> str:
    k = (kind or "").lower()
    if k in ("credit", "debit"):
        return "payment"
    if k in ("message", "deleted_message", "dm", "post", "email", "call"):
        return "communication"
    if k in ("network_event", "login", "cloud_activity"):
        return "network_cloud"
    if k in ("cctv_clip", "location_ping", "media"):
        return "physical_media"
    return "other"


def _build_template_title(ep_events: List[Dict[str, Any]], start_utc: str, end_utc: str) -> str:
    t_start = start_utc[11:16] if len(start_utc) >= 16 else start_utc
    t_end = end_utc[11:16] if len(end_utc) >= 16 else end_utc
    groups = {_kind_group(e["kind"]) for e in ep_events}

    if "payment" in groups:
        txs = [e for e in ep_events if e["kind"] in ("credit", "debit") and e.get("amount")]
        total_amt = sum(float(e["amount"]) for e in txs)
        return f"Payment: {len(txs)} transfer(s) totalling INR {total_amt:,.2f}, {t_start} to {t_end} UTC"
    if "network_cloud" in groups and len(groups) == 1:
        actors = sorted({e["actor"] for e in ep_events if e.get("actor")})[:3]
        actor_str = ", ".join(actors) if actors else "unknown actor"
        return f"Network & Cloud Activity: {len(ep_events)} event(s) by {actor_str}, {t_start} to {t_end} UTC"
    if "physical_media" in groups and len(groups) == 1:
        places = sorted({e["place"] for e in ep_events if e.get("place")})[:2]
        place_str = ", ".join(places) if places else "unspecified location"
        return f"Physical & Media Anchor: {len(ep_events)} event(s) at {place_str}, {t_start} to {t_end} UTC"

    actors = sorted({e["actor"] for e in ep_events if e.get("actor")})[:3]
    actor_str = ", ".join(actors) if actors else "participants"
    return f"Communication & Activity: {len(ep_events)} event(s) involving {actor_str}, {t_start} to {t_end} UTC"


def generate_event_sequence(
    conn: sqlite3.Connection,
    gap_minutes: int = EPISODE_GAP_MINUTES,
) -> List[Dict[str, Any]]:
    """Segment the unified timeline into titled episodes with full citations."""
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT ev.*, evi.exhibit_id, evi.filename
        FROM events ev
        JOIN evidence evi ON ev.evidence_id = evi.id
        ORDER BY ev.ts_utc ASC, ev.id ASC;
        """
    )
    rows = cursor.fetchall()

    # Load anomaly flags indexed by event_id
    cursor.execute("SELECT id, kind, severity, event_ids_json FROM anomalies;")
    event_anomalies: Dict[str, List[Dict[str, str]]] = {}
    for a in cursor.fetchall():
        try:
            eids = json.loads(a["event_ids_json"])
        except Exception:
            eids = []
        for eid in eids:
            event_anomalies.setdefault(eid, []).append({
                "anomaly_id": a["id"],
                "kind": a["kind"],
                "severity": a["severity"],
            })

    # Load spatial observations indexed by source_event_id
    cursor.execute("SELECT source_event_id, place_name, entity_or_device FROM observations;")
    event_places: Dict[str, str] = {}
    for obs in cursor.fetchall():
        event_places[obs["source_event_id"]] = obs["place_name"]

    if not rows:
        cursor.execute("DELETE FROM episodes;")
        conn.commit()
        return []

    # Segment into episodes
    buckets: List[List[Dict[str, Any]]] = []
    current_bucket: List[Dict[str, Any]] = []
    prev_dt: Optional[datetime] = None
    prev_actors: Set[str] = set()
    prev_group: Optional[str] = None

    for r in rows:
        try:
            ref = json.loads(r["ref_json"])
        except Exception:
            ref = {}
        dt = dateutil.parser.parse(r["ts_utc"])
        actors_here = {x for x in (r["actor"], r["counterparty"]) if x}
        grp = _kind_group(r["kind"])
        device_id = ref.get("device_id")
        place = event_places.get(r["id"]) or ref.get("location_name") or r["location_id"]

        step = {
            "event_id": r["id"],
            "ts_utc": r["ts_utc"],
            "ts_original": r["ts_original"],
            "tz_assumed": r["tz_assumed"],
            "clock_offset_seconds": int(r["clock_offset_seconds"] or 0),
            "offset_source": r["offset_source"],
            "place": place,
            "actor": r["actor"],
            "counterparty": r["counterparty"],
            "actors": sorted(actors_here),
            "devices": [device_id] if device_id else [],
            "kind": r["kind"],
            "amount": r["amount"],
            "currency": r["currency"],
            "text": r["text"],
            "source_chip": {
                "exhibit_id": r["exhibit_id"],
                "filename": r["filename"],
                "source_type": r["source_type"],
                "ref": ref,
            },
            "anomaly_flags": event_anomalies.get(r["id"], []),
        }

        split_episode = False
        if prev_dt is not None:
            dt_min = (dt - prev_dt).total_seconds() / 60.0
            if dt_min > gap_minutes:
                split_episode = True
            elif dt_min > (gap_minutes / 3.0) and grp != prev_group and not (actors_here & prev_actors):
                split_episode = True

        if split_episode and current_bucket:
            buckets.append(current_bucket)
            current_bucket = []

        current_bucket.append(step)
        prev_dt = dt
        prev_actors = actors_here
        prev_group = grp

    if current_bucket:
        buckets.append(current_bucket)

    episodes: List[Dict[str, Any]] = []
    cursor.execute("DELETE FROM episodes;")

    for idx, steps in enumerate(buckets, start=1):
        ep_id = f"EP-{idx:03d}"
        start_ts = steps[0]["ts_utc"]
        end_ts = steps[-1]["ts_utc"]
        title = _build_template_title(steps, start_ts, end_ts)
        actors = sorted({a for s in steps for a in s["actors"]})
        devices = sorted({d for s in steps for d in s["devices"]})
        locations = sorted({s["place"] for s in steps if s["place"]})
        exhibits = sorted({s["source_chip"]["exhibit_id"] for s in steps})
        anomalies = []
        seen_anom = set()
        for s in steps:
            for af in s["anomaly_flags"]:
                if af["anomaly_id"] not in seen_anom:
                    seen_anom.add(af["anomaly_id"])
                    anomalies.append(af)

        ep_obj = {
            "id": ep_id,
            "title": title,
            "start_ts_utc": start_ts,
            "end_ts_utc": end_ts,
            "actors": actors,
            "devices": devices,
            "locations": locations,
            "exhibits": exhibits,
            "anomalies": anomalies,
            "steps": steps,
            "title_source": "template",
        }
        episodes.append(ep_obj)

        cursor.execute(
            """
            INSERT INTO episodes (id, title, start_ts_utc, end_ts_utc, actors_json, devices_json, locations_json, exhibits_json, anomalies_json, steps_json, title_source)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                ep_id,
                title,
                start_ts,
                end_ts,
                json.dumps(actors),
                json.dumps(devices),
                json.dumps(locations),
                json.dumps(exhibits),
                json.dumps(anomalies),
                json.dumps(steps),
                "template",
            ),
        )

    conn.commit()
    return episodes


def get_stored_episodes(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM episodes ORDER BY id ASC;")
    episodes = []
    for r in cursor.fetchall():
        episodes.append({
            "id": r["id"],
            "title": r["title"],
            "start_ts_utc": r["start_ts_utc"],
            "end_ts_utc": r["end_ts_utc"],
            "actors": json.loads(r["actors_json"]),
            "devices": json.loads(r["devices_json"]),
            "locations": json.loads(r["locations_json"]),
            "exhibits": json.loads(r["exhibits_json"]),
            "anomalies": json.loads(r["anomalies_json"]),
            "steps": json.loads(r["steps_json"]),
            "title_source": r["title_source"],
        })
    return episodes


def export_sequence_markdown(episodes: List[Dict[str, Any]]) -> str:
    lines = ["# PRAMAAN Automated Event Sequence", ""]
    for ep in episodes:
        lines.append(f"## {ep['id']}: {ep['title']}")
        lines.append(f"- **Window (UTC):** `{ep['start_ts_utc']}` to `{ep['end_ts_utc']}`")
        lines.append(f"- **Actors:** {', '.join(ep['actors']) or 'None'}")
        lines.append(f"- **Locations:** {', '.join(ep['locations']) or 'Not established'}")
        lines.append(f"- **Exhibits:** {', '.join(ep['exhibits'])}")
        lines.append("")
        for i, step in enumerate(ep["steps"], start=1):
            offset_note = (
                f" *(original: `{step['ts_original']}`, offset: `{step['clock_offset_seconds']:+d}s` via {step['offset_source']})*"
                if step.get("clock_offset_seconds")
                else f" *(original: `{step['ts_original']}`)*"
            )
            place_note = f" @ **{step['place']}**" if step.get("place") else ""
            anom_note = (
                f" [ANOMALY: {', '.join(a['kind'] for a in step['anomaly_flags'])}]"
                if step.get("anomaly_flags")
                else ""
            )
            lines.append(
                f"{i}. `{step['ts_utc']}`{offset_note} — **[{step['source_chip']['exhibit_id']}]** "
                f"{step.get('actor') or ''}{place_note}: {step.get('text') or ''}{anom_note}"
            )
        lines.append("")
    return "\n".join(lines)
