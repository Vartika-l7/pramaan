"""Read-only retrieval tools for the Investigator Assistant (Phase 2C)."""

from __future__ import annotations

import json
import sqlite3
from collections import deque
from typing import Any, Dict, List, Optional

from backend.app.extract.language import transliterate_devanagari_to_latin
from backend.app.sequence.generator import generate_event_sequence, get_stored_episodes
from backend.app.scene.reconstructor import reconstruct_scene


def _ensure_fts(conn: sqlite3.Connection) -> None:
    """Create and populate SQLite FTS5 index over events if not already populated."""
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE VIRTUAL TABLE IF NOT EXISTS events_fts USING fts5(
            event_id UNINDEXED,
            text_norm,
            actor_norm,
            source_type UNINDEXED
        );
        """
    )
    cursor.execute("SELECT COUNT(*) FROM events_fts;")
    fts_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM events;")
    ev_count = cursor.fetchone()[0]
    if fts_count != ev_count:
        cursor.execute("DELETE FROM events_fts;")
        cursor.execute("SELECT id, text, actor, counterparty, source_type FROM events;")
        for r in cursor.fetchall():
            raw_text = f"{r['text'] or ''} {r['actor'] or ''} {r['counterparty'] or ''}"
            norm_text = transliterate_devanagari_to_latin(raw_text).lower()
            norm_actor = transliterate_devanagari_to_latin(r["actor"] or "").lower()
            cursor.execute(
                "INSERT INTO events_fts (event_id, text_norm, actor_norm, source_type) VALUES (?, ?, ?, ?);",
                (r["id"], norm_text, norm_actor, r["source_type"]),
            )
        conn.commit()


def search_text(
    conn: sqlite3.Connection,
    query: str,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 20,
) -> List[Dict[str, Any]]:
    """SQLite FTS5 full-text search over events with transliteration-normalised matching."""
    _ensure_fts(conn)
    norm_q = transliterate_devanagari_to_latin(query).lower().strip()
    stopwords = {
        "what", "where", "when", "who", "which", "how", "was", "were", "is", "are",
        "the", "and", "for", "with", "from", "that", "this", "did", "does", "about",
        "into", "near", "today", "there", "any", "have", "has",
    }
    tokens = [
        t for t in "".join(c if c.isalnum() else " " for c in norm_q).split()
        if len(t) >= 2 and t not in stopwords
    ]
    if not tokens:
        return []

    fts_expr = " AND ".join(f'"{t}"' for t in tokens[:6])
    cursor = conn.cursor()
    where_extra = ""
    params: List[Any] = [fts_expr]
    if filters and filters.get("source_type"):
        where_extra += " AND ev.source_type = ?"
        params.append(filters["source_type"])
    params.append(limit)

    try:
        cursor.execute(
            f"""
            SELECT ev.id, ev.ts_utc, ev.ts_original, ev.source_type, ev.actor, ev.counterparty,
                   ev.kind, ev.text, ev.amount, ev.currency, evi.exhibit_id, evi.filename
            FROM events_fts f
            JOIN events ev ON f.event_id = ev.id
            JOIN evidence evi ON ev.evidence_id = evi.id
            WHERE events_fts MATCH ? {where_extra}
            ORDER BY ev.ts_utc ASC
            LIMIT ?;
            """,
            params,
        )
        return [dict(r) for r in cursor.fetchall()]
    except Exception:
        return []


def find_entity(conn: sqlite3.Connection, text: str) -> List[Dict[str, Any]]:
    """Find entities matching text (with Devanagari/Hinglish transliteration support)."""
    norm_q = transliterate_devanagari_to_latin(text).lower().strip()
    cursor = conn.cursor()
    cursor.execute("SELECT id, type, value_norm, display FROM entities;")
    matches = []
    for r in cursor.fetchall():
        disp_norm = transliterate_devanagari_to_latin(r["display"]).lower()
        val_norm = transliterate_devanagari_to_latin(r["value_norm"]).lower()
        if norm_q in disp_norm or norm_q in val_norm or disp_norm in norm_q:
            matches.append(dict(r))
    return matches[:15]


def get_entity_profile(conn: sqlite3.Connection, entity_id: str) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM entities WHERE id = ? OR value_norm = ? OR display = ?;", (entity_id, entity_id, entity_id))
    ent = cursor.fetchone()
    if not ent:
        return {"found": False, "entity_id": entity_id}
    cursor.execute(
        """
        SELECT ev.id, ev.ts_utc, ev.source_type, ev.text, evi.exhibit_id
        FROM mentions m
        JOIN events ev ON m.event_id = ev.id
        JOIN evidence evi ON ev.evidence_id = evi.id
        WHERE m.entity_id = ?
        ORDER BY ev.ts_utc ASC LIMIT 20;
        """,
        (ent["id"],),
    )
    return {"found": True, "entity": dict(ent), "mentions": [dict(r) for r in cursor.fetchall()]}


def connections(conn: sqlite3.Connection, entity_id: str, depth: int = 1) -> List[Dict[str, Any]]:
    """Return graph edges connected to entity_id up to depth 2."""
    depth = min(max(1, depth), 2)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM edges;")
    all_edges = [dict(r) for r in cursor.fetchall()]

    frontier = {entity_id}
    visited_edges: Dict[str, Dict[str, Any]] = {}
    for _ in range(depth):
        next_frontier = set()
        for e in all_edges:
            if e["src"] in frontier or e["dst"] in frontier or entity_id.lower() in e["reason_text"].lower():
                visited_edges[e["id"]] = e
                next_frontier.add(e["src"])
                next_frontier.add(e["dst"])
        frontier = next_frontier
    return list(visited_edges.values())[:25]


def path_between(conn: sqlite3.Connection, entity_a: str, entity_b: str) -> Dict[str, Any]:
    """Shortest path between two entities in the knowledge graph."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, src, dst, edge_type, reason_text FROM edges;")
    adj: Dict[str, List[Dict[str, Any]]] = {}
    for r in cursor.fetchall():
        d = dict(r)
        adj.setdefault(d["src"], []).append(d)
        adj.setdefault(d["dst"], []).append(d)

    q = deque([(entity_a, [])])
    seen = {entity_a}
    while q:
        curr, path = q.popleft()
        if curr == entity_b and path:
            return {"found": True, "path": path}
        if len(path) >= 4:
            continue
        for edge in adj.get(curr, []):
            nxt = edge["dst"] if edge["src"] == curr else edge["src"]
            if nxt not in seen:
                seen.add(nxt)
                q.append((nxt, path + [edge]))
    return {"found": False, "path": []}


def events_in_range(
    conn: sqlite3.Connection,
    from_ts: Optional[str] = None,
    to_ts: Optional[str] = None,
    filters: Optional[Dict[str, Any]] = None,
    limit: int = 30,
) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    clauses = []
    params: List[Any] = []
    if from_ts:
        clauses.append("ev.ts_utc >= ?")
        params.append(from_ts)
    if to_ts:
        clauses.append("ev.ts_utc <= ?")
        params.append(to_ts)
    if filters and filters.get("source_type"):
        clauses.append("ev.source_type = ?")
        params.append(filters["source_type"])
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)
    cursor.execute(
        f"""
        SELECT ev.id, ev.ts_utc, ev.ts_original, ev.clock_offset_seconds, ev.offset_source,
               ev.source_type, ev.actor, ev.counterparty, ev.kind, ev.text, ev.amount, ev.currency,
               evi.exhibit_id, evi.filename
        FROM events ev
        JOIN evidence evi ON ev.evidence_id = evi.id
        {where_sql}
        ORDER BY ev.ts_utc ASC
        LIMIT ?;
        """,
        params,
    )
    return [dict(r) for r in cursor.fetchall()]


def list_anomalies(conn: sqlite3.Connection, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    clauses = []
    params: List[Any] = []
    if filters and filters.get("kind"):
        clauses.append("kind = ?")
        params.append(filters["kind"])
    if filters and filters.get("severity"):
        clauses.append("severity = ?")
        params.append(filters["severity"])
    where_sql = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    cursor.execute(f"SELECT id, kind, severity, evidence_id, event_ids_json, description, status FROM anomalies {where_sql};", params)
    return [dict(r) for r in cursor.fetchall()]


def explain_edge(conn: sqlite3.Connection, edge_id: str) -> Optional[Dict[str, Any]]:
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM edges WHERE id = ?;", (edge_id,))
    row = cursor.fetchone()
    return dict(row) if row else None


def transfers_summary(
    conn: sqlite3.Connection,
    account: Optional[str] = None,
    time_range: Optional[Dict[str, str]] = None,
) -> List[Dict[str, Any]]:
    cursor = conn.cursor()
    clauses = ["ev.kind IN ('credit', 'debit')", "ev.amount IS NOT NULL"]
    params: List[Any] = []
    if account:
        clauses.append("(ev.actor LIKE ? OR ev.text LIKE ? OR evi.filename LIKE ?)")
        like = f"%{account}%"
        params.extend([like, like, like])
    if time_range and time_range.get("from"):
        clauses.append("ev.ts_utc >= ?")
        params.append(time_range["from"])
    if time_range and time_range.get("to"):
        clauses.append("ev.ts_utc <= ?")
        params.append(time_range["to"])
    cursor.execute(
        f"""
        SELECT ev.id, ev.ts_utc, ev.ts_original, ev.kind, ev.amount, ev.currency, ev.text, evi.exhibit_id
        FROM events ev
        JOIN evidence evi ON ev.evidence_id = evi.id
        WHERE {' AND '.join(clauses)}
        ORDER BY ev.ts_utc ASC LIMIT 30;
        """,
        params,
    )
    return [dict(r) for r in cursor.fetchall()]


def locations_for(conn: sqlite3.Connection, entity_or_device: str) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT o.*, evi.exhibit_id
        FROM observations o
        JOIN events ev ON o.source_event_id = ev.id
        JOIN evidence evi ON ev.evidence_id = evi.id
        WHERE LOWER(o.entity_or_device) LIKE ?
        ORDER BY o.start_ts_utc ASC;
        """,
        (f"%{entity_or_device.lower()}%",),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    if not rows:
        return {"entity_or_device": entity_or_device, "status": "not established", "observations": []}
    return {"entity_or_device": entity_or_device, "status": "established", "observations": rows}


def who_was_near(conn: sqlite3.Connection, location: str) -> Dict[str, Any]:
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT o.*, evi.exhibit_id
        FROM observations o
        JOIN events ev ON o.source_event_id = ev.id
        JOIN evidence evi ON ev.evidence_id = evi.id
        WHERE LOWER(o.place_name) LIKE ?
        ORDER BY o.start_ts_utc ASC;
        """,
        (f"%{location.lower()}%",),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    if not rows:
        return {"location": location, "status": "not established", "observations": []}
    return {"location": location, "status": "established", "observations": rows}


def sequence_summary(conn: sqlite3.Connection, episode_id: Optional[str] = None) -> List[Dict[str, Any]]:
    eps = get_stored_episodes(conn) or generate_event_sequence(conn)
    if episode_id:
        return [e for e in eps if e["id"] == episode_id]
    return eps[:10]


def scene_summary(conn: sqlite3.Connection, episode_id: Optional[str] = None, start_ts: Optional[str] = None, end_ts: Optional[str] = None) -> Dict[str, Any]:
    return reconstruct_scene(conn, start_ts=start_ts, end_ts=end_ts, episode_id=episode_id)


def summarise_records(conn: sqlite3.Connection, record_ids: List[str]) -> List[Dict[str, Any]]:
    if not record_ids:
        return []
    cursor = conn.cursor()
    ph = ",".join(["?"] * len(record_ids))
    cursor.execute(
        f"""
        SELECT ev.id, ev.ts_utc, ev.source_type, ev.actor, ev.kind, ev.text, evi.exhibit_id
        FROM events ev
        JOIN evidence evi ON ev.evidence_id = evi.id
        WHERE ev.id IN ({ph});
        """,
        record_ids,
    )
    return [dict(r) for r in cursor.fetchall()]


def draft_case_diary(conn: sqlite3.Connection, from_ts: Optional[str] = None, to_ts: Optional[str] = None) -> List[Dict[str, Any]]:
    evs = events_in_range(conn, from_ts=from_ts, to_ts=to_ts, limit=200)
    by_date: Dict[str, List[Dict[str, Any]]] = {}
    for ev in evs:
        day = ev["ts_utc"][:10]
        by_date.setdefault(day, []).append(ev)

    diary = []
    for day in sorted(by_date.keys()):
        day_evs = by_date[day]
        refs = [e["id"] for e in day_evs[:5]]
        summary = f"{day}: {len(day_evs)} recorded event(s) across {', '.join(sorted({e['exhibit_id'] for e in day_evs}))}."
        diary.append({"date": day, "event_count": len(day_evs), "summary": summary, "refs": refs})
    return diary


def suggest_next_leads(conn: sqlite3.Connection) -> List[Dict[str, Any]]:
    leads: List[Dict[str, Any]] = []
    for anom in list_anomalies(conn)[:5]:
        try:
            eids = json.loads(anom["event_ids_json"])
        except Exception:
            eids = []
        leads.append({
            "title": f"Investigate {anom['kind']} ({anom['severity']})",
            "reason": anom["description"],
            "evidence_refs": eids or [anom["id"]],
            "what_to_check_next": "Inspect referenced source records and corroborate with independent telecom or banking records.",
            "tier": "LEAD",
        })
    return leads


def get_starter_chips(conn: sqlite3.Connection) -> List[str]:
    chips: List[str] = []
    cursor = conn.cursor()
    cursor.execute("SELECT display FROM entities WHERE type IN ('UPI', 'PERSON', 'DEVICE') LIMIT 2;")
    for r in cursor.fetchall():
        chips.append(f"Who is connected to {r['display']}?")
    cursor.execute("SELECT kind FROM anomalies WHERE severity = 'HIGH' LIMIT 2;")
    for r in cursor.fetchall():
        if r["kind"] == "IMPOSSIBLE_TRAVEL":
            chips.append("Where was device D1 when impossible travel occurred?")
        elif r["kind"] == "ANOMALY_CHAT_GAP":
            chips.append("What happened during the 6h 14m chat silence gap?")
    if len(chips) < 4:
        chips.append("How did the money move from Meera's account?")
        chips.append("Summarise the case so far.")
    return chips[:5]
