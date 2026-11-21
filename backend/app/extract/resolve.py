"""Entity extraction orchestration and fuzzy resolution for PRAMAAN."""

from __future__ import annotations

import json
import sqlite3
import uuid
from typing import Dict, List, Set, Tuple
from rapidfuzz import fuzz

from backend.app.extract.patterns import extract_all_identifiers, ExtractedEntityMatch
from backend.app.extract.names import extract_persons, clean_person_name
from backend.app.extract.locations import extract_locations
from backend.app.extract.language import transliterate_devanagari_to_latin
from backend.app.correlate.base import deterministic_id


def run_entity_extraction(conn: sqlite3.Connection) -> Dict[str, int]:
    """Extract entities and mentions across all recorded events."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, text, actor, counterparty, source_type FROM events ORDER BY ts_utc ASC, id ASC;")
    events = cursor.fetchall()

    entity_cache: Dict[Tuple[str, str], str] = {}  # (type, value_norm) -> entity_id
    # Pre-populate cache
    cursor.execute("SELECT id, type, value_norm FROM entities;")
    for r in cursor.fetchall():
        entity_cache[(r["type"], r["value_norm"])] = r["id"]

    total_mentions = 0
    total_entities_new = 0

    for ev in events:
        event_id = ev["id"]
        text = ev["text"] or ""
        actor = ev["actor"] or ""
        counterparty = ev["counterparty"] or ""

        matches: List[ExtractedEntityMatch] = []
        matches.extend(extract_all_identifiers(text))
        matches.extend(extract_persons(text))
        matches.extend(extract_locations(text))

        # Check actor/counterparty if they are phone numbers or known personas
        if actor and actor not in ("SYSTEM", "unknown"):
            if actor.startswith("+91") or (actor.isdigit() and len(actor) >= 10):
                matches.extend(extract_all_identifiers(actor))
            else:
                norm_act = clean_person_name(actor)
                if len(norm_act) >= 3 and not norm_act.startswith("Device_"):
                    matches.append(
                        ExtractedEntityMatch(
                            type="PERSON",
                            value_raw=actor,
                            value_norm=norm_act,
                            char_start=0,
                            char_end=len(actor),
                            extractor="actor_header",
                        )
                    )

        if counterparty:
            matches.extend(extract_all_identifiers(counterparty))

        for m in matches:
            key = (m.type, m.value_norm)
            if key not in entity_cache:
                ent_id = deterministic_id("ent", m.type, m.value_norm)
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO entities (id, type, value_norm, display, first_event_id)
                    VALUES (?, ?, ?, ?, ?);
                    """,
                    (ent_id, m.type, m.value_norm, m.value_norm, event_id),
                )
                entity_cache[key] = ent_id
                total_entities_new += 1
            else:
                ent_id = entity_cache[key]

            # Insert mention
            mention_id = deterministic_id("men", ent_id, event_id, m.char_start, m.char_end, m.extractor)
            cursor.execute(
                """
                INSERT OR IGNORE INTO mentions (id, entity_id, event_id, char_start, char_end, extractor, tier)
                VALUES (?, ?, ?, ?, ?, ?, 'VERIFIED BY CODE');
                """,
                (mention_id, ent_id, event_id, m.char_start, m.char_end, m.extractor),
            )
            total_mentions += 1

    conn.commit()

    # Run fuzzy entity resolution on PERSON entities
    fuzzy_edges = run_fuzzy_resolution(conn)

    return {
        "new_entities": total_entities_new,
        "total_mentions": total_mentions,
        "fuzzy_edges": fuzzy_edges,
    }


def run_fuzzy_resolution(conn: sqlite3.Connection, threshold: float = 75.0) -> int:
    """Identify fuzzy name variants and emit LEAD edges without auto-merging."""
    cursor = conn.cursor()
    cursor.execute("SELECT id, display, value_norm FROM entities WHERE type = 'PERSON' ORDER BY id ASC;")
    persons = cursor.fetchall()

    created_edges = 0
    checked_pairs: Set[Tuple[str, str]] = set()

    for i in range(len(persons)):
        for j in range(i + 1, len(persons)):
            p1 = persons[i]
            p2 = persons[j]
            id1, id2 = p1["id"], p2["id"]
            if (id1, id2) in checked_pairs:
                continue
            checked_pairs.add((id1, id2))

            name1 = transliterate_devanagari_to_latin(p1["value_norm"]).lower()
            name2 = transliterate_devanagari_to_latin(p2["value_norm"]).lower()

            # RapidFuzz similarity
            ratio = fuzz.token_sort_ratio(name1, name2)
            if ratio >= threshold:
                edge_id = deterministic_id("edge_fuzzy", id1, id2, "SAME_PERSON_FUZZY")
                reason = f"Fuzzy name match ({ratio:.1f}% similarity) between '{p1['display']}' and '{p2['display']}'"
                cursor.execute(
                    """
                    INSERT OR IGNORE INTO edges (id, src, dst, edge_type, basis, reason_text, strength, tier, status, event_ids_json)
                    VALUES (?, ?, ?, 'SAME_PERSON_FUZZY', 'inferred', ?, ?, 'LEAD', 'LEAD', '[]');
                    """,
                    (edge_id, id1, id2, reason, ratio / 100.0),
                )
                created_edges += 1

    conn.commit()
    return created_edges

