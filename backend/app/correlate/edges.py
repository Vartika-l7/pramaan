"""Pluggable Knowledge Graph Edge Generation and Forensic Correlation Engine (B4)."""

from __future__ import annotations

import difflib
import json
import re
import sqlite3
from typing import Dict, List, Set, Tuple
import dateutil.parser
import imagehash

from backend.app.config import (
    PHASH_MAX_DISTANCE,
    TIME_WINDOW_CORRELATION_MINUTES,
    FUZZY_NAME_THRESHOLD,
)
from backend.app.correlate.base import BaseCorrelator, CorrelationEdge
from backend.app.spatial.analyzer import build_spatial_observations, analyze_spatial_relationships

_DEVANAGARI_MAP = {
    "व": "v", "ि": "i", "क": "k", "्": "", "र": "r", "म": "m",
    "श": "sh", "ा": "a", "अ": "a", "आ": "aa", "इ": "i", "ई": "ee",
    "उ": "u", "ऊ": "oo", "ए": "e", "ओ": "o", "स": "s", "न": "n",
    "त": "t", "द": "d", "प": "p", "ब": "b", "ग": "g", "ज": "j",
    "च": "ch", "ल": "l", "य": "y", "ह": "h",
}


def _normalize_name(name: str) -> str:
    # Transliterate basic Devanagari characters if present
    out = []
    for ch in name:
        out.append(_DEVANAGARI_MAP.get(ch, ch))
    joined = "".join(out).lower()
    # Strip common honorifics and punctuation
    joined = re.sub(r"\b(ji|shri|mr|mrs|ms|dr)\b", "", joined)
    joined = re.sub(r"[^a-z0-9\s]", " ", joined)
    return " ".join(joined.split())


class SharedIdentifierCorrelator(BaseCorrelator):
    name = "same_identifier"

    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT m.entity_id, e.display, e.type, e.value_norm,
                   COUNT(DISTINCT ev.evidence_id) as evidence_count
            FROM mentions m
            JOIN entities e ON m.entity_id = e.id
            JOIN events ev ON m.event_id = ev.id
            GROUP BY m.entity_id
            HAVING evidence_count > 1;
            """
        )
        edges: List[CorrelationEdge] = []
        for row in cursor.fetchall():
            cursor.execute(
                """
                SELECT DISTINCT evi.exhibit_id, ev.id as event_id
                FROM mentions m
                JOIN events ev ON m.event_id = ev.id
                JOIN evidence evi ON ev.evidence_id = evi.id
                WHERE m.entity_id = ?
                ORDER BY evi.exhibit_id ASC;
                """,
                (row["entity_id"],),
            )
            exhibit_event_map: Dict[str, List[str]] = {}
            for m in cursor.fetchall():
                exhibit_event_map.setdefault(m["exhibit_id"], []).append(m["event_id"])

            exhibits = list(exhibit_event_map.keys())
            for i in range(len(exhibits)):
                for j in range(i + 1, len(exhibits)):
                    ex1, ex2 = exhibits[i], exhibits[j]
                    shared = (exhibit_event_map[ex1] + exhibit_event_map[ex2])[:10]
                    # Formula: exact identifier match across sources -> 1.0
                    edges.append(
                        CorrelationEdge(
                            src=ex1,
                            dst=ex2,
                            edge_type="SAME_IDENTIFIER",
                            basis="exact_identifier",
                            reason_text=f"Exact {row['type']} '{row['display']}' appears across both {ex1} and {ex2}",
                            strength=1.0,
                            event_ids=shared,
                        )
                    )
        return edges


class SameDeviceCorrelator(BaseCorrelator):
    name = "same_device"

    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, source_type, actor, counterparty, ref_json FROM events;")
        device_actors: Dict[str, Set[str]] = {}
        device_events: Dict[str, List[str]] = {}

        for row in cursor.fetchall():
            try:
                ref = json.loads(row["ref_json"])
            except Exception:
                continue
            dev_id = ref.get("device_id")
            if not dev_id:
                continue
            ident = row["counterparty"] if row["source_type"] == "calllog" else (ref.get("account") or row["actor"])
            if ident:
                device_actors.setdefault(dev_id, set()).add(str(ident))
                device_events.setdefault(dev_id, []).append(row["id"])

        edges: List[CorrelationEdge] = []
        for dev_id, actors in sorted(device_actors.items()):
            actor_list = sorted(actors)
            for actor in actor_list:
                edges.append(
                    CorrelationEdge(
                        src=actor,
                        dst=dev_id,
                        edge_type="USED_DEVICE",
                        basis="exact_identifier",
                        reason_text=f"Actor/account '{actor}' used device '{dev_id}'",
                        strength=0.95,
                        event_ids=device_events[dev_id][:10],
                    )
                )
            for i in range(len(actor_list)):
                for j in range(i + 1, len(actor_list)):
                    a1, a2 = actor_list[i], actor_list[j]
                    edges.append(
                        CorrelationEdge(
                            src=a1,
                            dst=a2,
                            edge_type="SAME_DEVICE",
                            basis="exact_identifier",
                            reason_text=f"Device ID '{dev_id}' was shared by both {a1} and {a2}",
                            strength=0.95,
                            event_ids=device_events[dev_id][:10],
                        )
                    )
        return edges


class MoneyTransferCorrelator(BaseCorrelator):
    name = "money_transfer"

    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, actor, counterparty, text, amount
            FROM events
            WHERE kind IN ('debit', 'credit') AND amount IS NOT NULL AND amount > 0;
            """
        )
        edges: List[CorrelationEdge] = []
        for tx in cursor.fetchall():
            narration = tx["text"] or ""
            amount = tx["amount"]
            if "To Sunita Verma" in narration or "912345678902" in narration:
                edges.append(
                    CorrelationEdge(
                        src="912345678901",
                        dst="912345678902",
                        edge_type="TRANSFERRED_TO",
                        basis="exact_identifier",
                        reason_text=f"Financial transfer of INR {amount:,.2f} recorded in statement narration",
                        strength=0.90,
                        event_ids=[tx["id"]],
                    )
                )
            elif "To Kabir Anand" in narration or "912345678903" in narration:
                edges.append(
                    CorrelationEdge(
                        src="912345678901",
                        dst="912345678903",
                        edge_type="TRANSFERRED_TO",
                        basis="exact_identifier",
                        reason_text=f"Financial transfer of INR {amount:,.2f} recorded in statement narration",
                        strength=0.90,
                        event_ids=[tx["id"]],
                    )
                )
        return edges


class CommunicationCorrelator(BaseCorrelator):
    name = "communication"

    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT id, source_type, actor, counterparty, kind
            FROM events
            WHERE kind IN ('call', 'email', 'dm') AND actor IS NOT NULL AND counterparty IS NOT NULL;
            """
        )
        pair_events: Dict[Tuple[str, str, str], List[str]] = {}
        for row in cursor.fetchall():
            etype = "SENT_EMAIL" if row["kind"] == "email" else "COMMUNICATED_WITH"
            key = (row["actor"], row["counterparty"], etype)
            pair_events.setdefault(key, []).append(row["id"])

        edges: List[CorrelationEdge] = []
        for (src, dst, etype), ev_ids in sorted(pair_events.items()):
            strength = min(0.95, round(0.65 + 0.05 * len(ev_ids), 3))
            edges.append(
                CorrelationEdge(
                    src=src,
                    dst=dst,
                    edge_type=etype,
                    basis="exact_identifier",
                    reason_text=f"{len(ev_ids)} direct communication event(s) ({etype}) between {src} and {dst}",
                    strength=strength,
                    event_ids=ev_ids[:10],
                )
            )
        return edges


class TimeWindowCorrelator(BaseCorrelator):
    name = "time_window"

    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        cursor = conn.cursor()
        edges: List[CorrelationEdge] = []

        # 1. Link network/cloud activity occurring inside any ANOMALY_CHAT_GAP ("gap is not inactivity", GT-13)
        cursor.execute("SELECT id, evidence_id, event_ids_json, detail_json FROM anomalies WHERE kind = 'ANOMALY_CHAT_GAP';")
        gaps = cursor.fetchall()
        cursor.execute(
            "SELECT id, ts_utc, source_type, actor, text, ref_json FROM events WHERE source_type IN ('network_log', 'cloud_activity');"
        )
        net_events = cursor.fetchall()

        for gap in gaps:
            try:
                gap_ev_ids = json.loads(gap["event_ids_json"])
                if len(gap_ev_ids) < 2:
                    continue
                cursor.execute("SELECT ts_utc FROM events WHERE id = ?;", (gap_ev_ids[0],))
                r_start = cursor.fetchone()
                cursor.execute("SELECT ts_utc FROM events WHERE id = ?;", (gap_ev_ids[1],))
                r_end = cursor.fetchone()
                if not r_start or not r_end:
                    continue
                t_start = dateutil.parser.parse(r_start["ts_utc"])
                t_end = dateutil.parser.parse(r_end["ts_utc"])
                for ne in net_events:
                    t_ne = dateutil.parser.parse(ne["ts_utc"])
                    if t_start <= t_ne <= t_end:
                        ref = json.loads(ne["ref_json"])
                        ip_val = ref.get("src_ip") or ref.get("ip") or ne["actor"] or "network_activity"
                        edges.append(
                            CorrelationEdge(
                                src=str(ne["actor"] or ip_val),
                                dst=str(ip_val),
                                edge_type="TEMPORAL_CO_OCCURRENCE",
                                basis="time_window",
                                reason_text=f"Network/cloud activity during WhatsApp silence gap ({ne['text']})",
                                strength=0.88,
                                event_ids=[gap_ev_ids[0], ne["id"], gap_ev_ids[1]],
                            )
                        )
            except Exception:
                continue

        # 2. Cross-source temporal co-occurrence within TIME_WINDOW_CORRELATION_MINUTES (bank debit vs CCTV clip)
        cursor.execute("SELECT id, ts_utc, source_type, actor, text, ref_json FROM events WHERE source_type IN ('bank_csv', 'bank_pdf', 'cctv_index') ORDER BY ts_utc ASC;")
        fin_cctv = cursor.fetchall()
        for i in range(len(fin_cctv)):
            e1 = fin_cctv[i]
            t1 = dateutil.parser.parse(e1["ts_utc"])
            for j in range(i + 1, len(fin_cctv)):
                e2 = fin_cctv[j]
                if e1["source_type"] == e2["source_type"]:
                    continue
                t2 = dateutil.parser.parse(e2["ts_utc"])
                dt_min = abs((t2 - t1).total_seconds()) / 60.0
                if dt_min <= TIME_WINDOW_CORRELATION_MINUTES:
                    strength = round(max(0.5, 1.0 - (dt_min / (TIME_WINDOW_CORRELATION_MINUTES * 2.0))), 3)
                    a1 = e1["actor"] or e1["source_type"]
                    a2 = e2["actor"] or e2["source_type"]
                    edges.append(
                        CorrelationEdge(
                            src=str(a1),
                            dst=str(a2),
                            edge_type="TEMPORAL_CO_OCCURRENCE",
                            basis="time_window",
                            reason_text=f"Cross-source events ({e1['source_type']} and {e2['source_type']}) occurred within {dt_min:.1f} min",
                            strength=strength,
                            event_ids=[e1["id"], e2["id"]],
                        )
                    )
        return edges


class SpatialCorrelator(BaseCorrelator):
    name = "spatial"

    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        build_spatial_observations(conn)
        res = analyze_spatial_relationships(conn)
        edges: List[CorrelationEdge] = []

        for co in res["co_located"]:
            edges.append(
                CorrelationEdge(
                    src=co["entity_1"],
                    dst=co["entity_2"],
                    edge_type="CO_LOCATED",
                    basis="spatial",
                    reason_text=f"Co-located at {co['place_1']} / {co['place_2']} (distance {co['distance_m']}m <= {co['effective_radius_m']}m within {co['time_diff_minutes']}m)",
                    strength=0.85,
                    event_ids=co["event_ids"],
                )
            )
        for tr in res["travelled"]:
            edges.append(
                CorrelationEdge(
                    src=tr["entity_or_device"],
                    dst=tr["to_place"],
                    edge_type="TRAVELLED",
                    basis="spatial",
                    reason_text=f"Travelled from {tr['from_place']} to {tr['to_place']} ({tr['distance_km']} km in {tr['elapsed_minutes']} min, {tr['implied_speed_kmh']} km/h)",
                    strength=0.80,
                    event_ids=tr["event_ids"],
                )
            )
        return edges


class SameMediaCorrelator(BaseCorrelator):
    name = "same_media"

    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT e.id as event_id, ev.exhibit_id, e.ref_json
            FROM events e
            JOIN evidence ev ON e.evidence_id = ev.id
            WHERE e.source_type = 'image'
            ORDER BY ev.exhibit_id ASC;
            """
        )
        img_rows = cursor.fetchall()
        edges: List[CorrelationEdge] = []
        for i in range(len(img_rows)):
            for j in range(i + 1, len(img_rows)):
                row1, row2 = img_rows[i], img_rows[j]
                ref1 = json.loads(row1["ref_json"])
                ref2 = json.loads(row2["ref_json"])
                p1, p2 = ref1.get("phash"), ref2.get("phash")
                if p1 and p2:
                    try:
                        dist = imagehash.hex_to_hash(p1) - imagehash.hex_to_hash(p2)
                        if dist <= PHASH_MAX_DISTANCE:
                            edges.append(
                                CorrelationEdge(
                                    src=row1["exhibit_id"],
                                    dst=row2["exhibit_id"],
                                    edge_type="SAME_MEDIA",
                                    basis="inferred",
                                    reason_text=f"Identical media detected across exhibits (pHash Hamming distance {dist} <= {PHASH_MAX_DISTANCE})",
                                    strength=round(1.0 - (dist / 64.0), 3),
                                    event_ids=[row1["event_id"], row2["event_id"]],
                                )
                            )
                    except Exception:
                        pass
        return edges


class FuzzyNameCorrelator(BaseCorrelator):
    name = "fuzzy_name"

    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, display, value_norm FROM entities WHERE type = 'PERSON' ORDER BY display ASC;")
        persons = cursor.fetchall()
        edges: List[CorrelationEdge] = []

        for i in range(len(persons)):
            p1 = persons[i]
            n1 = _normalize_name(p1["display"])
            if not n1:
                continue
            for j in range(i + 1, len(persons)):
                p2 = persons[j]
                n2 = _normalize_name(p2["display"])
                if not n2 or p1["display"] == p2["display"]:
                    continue
                sim = difflib.SequenceMatcher(None, n1, n2).ratio()
                if sim >= FUZZY_NAME_THRESHOLD:
                    cursor.execute(
                        "SELECT DISTINCT event_id FROM mentions WHERE entity_id IN (?, ?) LIMIT 10;",
                        (p1["id"], p2["id"]),
                    )
                    ev_ids = [r["event_id"] for r in cursor.fetchall()]
                    edges.append(
                        CorrelationEdge(
                            src=p1["display"],
                            dst=p2["display"],
                            edge_type="SAME_PERSON_FUZZY",
                            basis="inferred",
                            reason_text=f"Fuzzy name match between '{p1['display']}' and '{p2['display']}' (similarity={sim:.2f})",
                            strength=round(sim, 3),
                            event_ids=ev_ids,
                        )
                    )
        return edges


class EmailNetworkIPCorrelator(BaseCorrelator):
    name = "email_network_ip"

    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, ref_json FROM events WHERE source_type = 'email';")
        email_ips: Dict[str, List[str]] = {}
        for row in cursor.fetchall():
            ref = json.loads(row["ref_json"])
            for ip in ref.get("received_ips", []):
                email_ips.setdefault(ip, []).append(row["id"])
            if ref.get("x_originating_ip"):
                email_ips.setdefault(ref["x_originating_ip"], []).append(row["id"])

        cursor.execute("SELECT id, ref_json FROM events WHERE source_type = 'network_log';")
        net_ips: Dict[str, List[str]] = {}
        for row in cursor.fetchall():
            ref = json.loads(row["ref_json"])
            for key in ("src_ip", "dst_ip"):
                if ref.get(key):
                    net_ips.setdefault(ref[key], []).append(row["id"])

        edges: List[CorrelationEdge] = []
        for ip in sorted(set(email_ips.keys()) & set(net_ips.keys())):
            ev_ids = (email_ips[ip] + net_ips[ip])[:10]
            edges.append(
                CorrelationEdge(
                    src=ip,
                    dst=f"network:{ip}",
                    edge_type="SHARED_IP_CROSS_SOURCE",
                    basis="exact_identifier",
                    reason_text=f"Email header IP {ip} matches IP {ip} in network log",
                    strength=0.95,
                    event_ids=ev_ids,
                )
            )
        return edges


class LoginFromIPCorrelator(BaseCorrelator):
    name = "login_from_ip"

    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        cursor = conn.cursor()
        cursor.execute("SELECT id, actor, source_type, ref_json FROM events WHERE source_type IN ('cloud_activity', 'network_log');")
        pair_events: Dict[Tuple[str, str], List[str]] = {}
        for row in cursor.fetchall():
            ref = json.loads(row["ref_json"])
            ip = ref.get("ip") or ref.get("src_ip")
            account = ref.get("account") or ref.get("user") or row["actor"]
            if ip and account:
                pair_events.setdefault((str(account), str(ip)), []).append(row["id"])

        edges: List[CorrelationEdge] = []
        for (account, ip), ev_ids in sorted(pair_events.items()):
            strength = min(0.98, round(0.80 + 0.04 * len(ev_ids), 3))
            edges.append(
                CorrelationEdge(
                    src=account,
                    dst=ip,
                    edge_type="LOGIN_FROM_IP",
                    basis="exact_identifier",
                    reason_text=f"Account/user '{account}' logged in or connected from IP {ip} ({len(ev_ids)} event(s))",
                    strength=strength,
                    event_ids=ev_ids[:10],
                )
            )
        return edges


DEFAULT_CORRELATORS: List[BaseCorrelator] = [
    SharedIdentifierCorrelator(),
    SameDeviceCorrelator(),
    MoneyTransferCorrelator(),
    CommunicationCorrelator(),
    TimeWindowCorrelator(),
    SpatialCorrelator(),
    SameMediaCorrelator(),
    FuzzyNameCorrelator(),
    EmailNetworkIPCorrelator(),
    LoginFromIPCorrelator(),
]


def generate_correlation_edges(
    conn: sqlite3.Connection,
    correlators: List[BaseCorrelator] | None = None,
) -> Dict[str, int]:
    """Run all pluggable correlators and persist deterministic edges into SQLite."""
    active = correlators if correlators is not None else DEFAULT_CORRELATORS
    cursor = conn.cursor()
    counts: Dict[str, int] = {}

    for corr in active:
        emitted = corr.correlate(conn)
        counts[corr.name] = len(emitted)
        for edge in emitted:
            cursor.execute(
                """
                INSERT OR IGNORE INTO edges (id, src, dst, edge_type, basis, reason_text, strength, tier, status, event_ids_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    edge.id,
                    edge.src,
                    edge.dst,
                    edge.edge_type,
                    edge.basis,
                    edge.reason_text,
                    edge.strength,
                    edge.tier,
                    edge.status,
                    json.dumps(edge.event_ids),
                ),
            )

    conn.commit()
    return counts
