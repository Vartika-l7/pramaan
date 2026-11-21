"""Knowledge Graph assembly, querying, Cytoscape formatting, and GraphML export (B5)."""

from __future__ import annotations

import json
import sqlite3
import xml.etree.ElementTree as ET
from typing import Dict, List, Any, Optional

from backend.app.correlate.base import deterministic_id


def _infer_node_type(node_id: str) -> str:
    if node_id.startswith("EX-"):
        return "EXHIBIT"
    if node_id.startswith("EP-"):
        return "EPISODE"
    if "@" in node_id and "." in node_id.split("@")[-1]:
        return "EMAIL_ADDRESS"
    if "@" in node_id:
        return "UPI"
    if node_id.startswith(("http://", "https://")):
        return "URL"
    if node_id.startswith("D") and node_id[1:].isdigit():
        return "DEVICE"
    if node_id.replace(".", "").isdigit() and node_id.count(".") == 3:
        return "IP"
    if node_id.replace("+", "").replace(" ", "").isdigit() and len(node_id) >= 10:
        return "ACCOUNT" if len(node_id) >= 12 and not node_id.startswith("+") else "PHONE"
    return "PERSON"


def get_cytoscape_graph(
    conn: sqlite3.Connection,
    type_filter: Optional[str] = None,
    tier_filter: Optional[str] = None,
    min_strength: float = 0.0,
    edge_type_filter: Optional[str] = None,
    query: Optional[str] = None,
) -> Dict[str, Any]:
    """Assemble the unified forensic knowledge graph formatted for Cytoscape.js."""
    cursor = conn.cursor()

    cursor.execute(
        """
        SELECT e.id, e.type, e.value_norm, e.display, COUNT(m.id) as mention_count
        FROM entities e
        LEFT JOIN mentions m ON e.id = m.entity_id
        GROUP BY e.id
        ORDER BY e.id ASC;
        """
    )
    entity_rows = cursor.fetchall()

    cursor.execute("SELECT id, exhibit_id, filename, source_type FROM evidence ORDER BY exhibit_id ASC;")
    evidence_rows = cursor.fetchall()

    cursor.execute("SELECT id, name, lat, lon, kind FROM locations ORDER BY id ASC;")
    location_rows = cursor.fetchall()

    cursor.execute("SELECT id, title, start_ts_utc, end_ts_utc FROM episodes ORDER BY id ASC;")
    episode_rows = cursor.fetchall()

    nodes: List[Dict[str, Any]] = []
    node_ids = set()

    def add_node(nid: str, label: str, ntype: str, tier: str = "VERIFIED BY CODE", extra: Optional[Dict[str, Any]] = None):
        if nid in node_ids:
            return
        data = {"id": nid, "label": label, "type": ntype, "tier": tier}
        if extra:
            data.update(extra)
        nodes.append({"data": data})
        node_ids.add(nid)

    for r in entity_rows:
        if type_filter and r["type"].lower() != type_filter.lower():
            continue
        add_node(str(r["id"]), r["display"], r["type"], "VERIFIED BY CODE", {"mention_count": r["mention_count"]})

    for ev in evidence_rows:
        if type_filter and type_filter.upper() != "EXHIBIT":
            pass
        add_node(ev["exhibit_id"], f"{ev['exhibit_id']} ({ev['filename']})", "EXHIBIT", "VERIFIED BY CODE", {"source_type": ev["source_type"]})

    for loc in location_rows:
        if type_filter and type_filter.upper() != "LOCATION":
            continue
        add_node(loc["id"], loc["name"], "LOCATION", "VERIFIED BY CODE", {"lat": loc["lat"], "lon": loc["lon"], "kind": loc["kind"]})

    for ep in episode_rows:
        if type_filter and type_filter.upper() != "EPISODE":
            continue
        add_node(ep["id"], ep["title"], "EPISODE", "VERIFIED BY CODE", {"start_ts_utc": ep["start_ts_utc"], "end_ts_utc": ep["end_ts_utc"]})

    # Fetch correlation edges
    cursor.execute("SELECT * FROM edges WHERE strength >= ? ORDER BY id ASC;", (min_strength,))
    edge_rows = cursor.fetchall()

    edges: List[Dict[str, Any]] = []
    for edge in edge_rows:
        if tier_filter and edge["tier"].upper() != tier_filter.upper():
            continue
        if edge_type_filter and edge["edge_type"].upper() != edge_type_filter.upper():
            continue

        src, dst = edge["src"], edge["dst"]
        if src not in node_ids:
            add_node(src, src, _infer_node_type(src), "LEAD")
        if dst not in node_ids:
            add_node(dst, dst, _infer_node_type(dst), "LEAD")

        try:
            event_ids = json.loads(edge["event_ids_json"])
        except Exception:
            event_ids = []

        edges.append({
            "data": {
                "id": edge["id"],
                "source": src,
                "target": dst,
                "edge_type": edge["edge_type"],
                "basis": edge["basis"],
                "reason_text": edge["reason_text"],
                "strength": edge["strength"],
                "tier": edge["tier"],
                "status": edge["status"],
                "event_ids": event_ids,
            }
        })

    # Add OBSERVED_AT edges from observations table (if not filtered out)
    if not edge_type_filter or edge_type_filter.upper() == "OBSERVED_AT":
        if not tier_filter or tier_filter.upper() == "VERIFIED BY CODE":
            cursor.execute("SELECT id, entity_or_device, location_id, place_name, start_ts_utc, source_event_id FROM observations ORDER BY start_ts_utc ASC, entity_or_device ASC, place_name ASC;")
            for obs in cursor.fetchall():
                ent = obs["entity_or_device"]
                loc_id = obs["location_id"] or deterministic_id("loc", obs["place_name"].lower(), "OBS")
                add_node(ent, ent, _infer_node_type(ent), "VERIFIED BY CODE")
                add_node(loc_id, obs["place_name"], "LOCATION", "VERIFIED BY CODE")
                eid = deterministic_id("edge_obs", ent, loc_id, obs["start_ts_utc"])
                edges.append({
                    "data": {
                        "id": eid,
                        "source": ent,
                        "target": loc_id,
                        "edge_type": "OBSERVED_AT",
                        "basis": "spatial",
                        "reason_text": f"{ent} observed at {obs['place_name']} at {obs['start_ts_utc']}",
                        "strength": 0.90,
                        "tier": "LEAD",
                        "status": "LEAD",
                        "event_ids": [obs["source_event_id"]],
                    }
                })

    # Add PART_OF_EPISODE edges for actors/locations in episodes
    if not edge_type_filter or edge_type_filter.upper() == "PART_OF_EPISODE":
        for ep in episode_rows:
            cursor.execute("SELECT actors_json FROM episodes WHERE id = ?;", (ep["id"],))
            row = cursor.fetchone()
            if not row:
                continue
            try:
                actors = json.loads(row["actors_json"])
            except Exception:
                actors = []
            for act in actors:
                add_node(act, act, _infer_node_type(act), "VERIFIED BY CODE")
                add_node(ep["id"], ep["title"], "EPISODE", "VERIFIED BY CODE")
                eid = deterministic_id("edge_ep", act, ep["id"])
                edges.append({
                    "data": {
                        "id": eid,
                        "source": act,
                        "target": ep["id"],
                        "edge_type": "PART_OF_EPISODE",
                        "basis": "time_window",
                        "reason_text": f"{act} participated in {ep['id']}",
                        "strength": 0.85,
                        "tier": "LEAD",
                        "status": "LEAD",
                        "event_ids": [],
                    }
                })

    # Optional query filter: keep matching nodes and their 1-hop neighbors/edges
    if query:
        q = query.strip().lower()
        matched_ids = {n["data"]["id"] for n in nodes if q in n["data"]["label"].lower() or q in n["data"]["id"].lower()}
        edges = [e for e in edges if e["data"]["source"] in matched_ids or e["data"]["target"] in matched_ids]
        connected_ids = set(matched_ids)
        for e in edges:
            connected_ids.add(e["data"]["source"])
            connected_ids.add(e["data"]["target"])
        nodes = [n for n in nodes if n["data"]["id"] in connected_ids]

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }


def export_graph_graphml(graph_data: Dict[str, Any]) -> str:
    """Serialize Cytoscape graph JSON into valid GraphML XML."""
    graphml = ET.Element("graphml", {
        "xmlns": "http://graphml.graphdrawing.org/xmlns",
        "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance",
    })
    for key_id, attr_for, attr_name, attr_type in [
        ("d0", "node", "label", "string"),
        ("d1", "node", "type", "string"),
        ("d2", "node", "tier", "string"),
        ("d3", "edge", "edge_type", "string"),
        ("d4", "edge", "basis", "string"),
        ("d5", "edge", "strength", "double"),
        ("d6", "edge", "tier", "string"),
        ("d7", "edge", "reason_text", "string"),
    ]:
        ET.SubElement(graphml, "key", {
            "id": key_id,
            "for": attr_for,
            "attr.name": attr_name,
            "attr.type": attr_type,
        })

    graph_el = ET.SubElement(graphml, "graph", {"id": "PRAMAAN_KG", "edgedefault": "directed"})

    for n in graph_data["nodes"]:
        nd = n["data"]
        n_el = ET.SubElement(graph_el, "node", {"id": str(nd["id"])})
        for kid, field in [("d0", "label"), ("d1", "type"), ("d2", "tier")]:
            d = ET.SubElement(n_el, "data", {"key": kid})
            d.text = str(nd.get(field, ""))

    for e in graph_data["edges"]:
        ed = e["data"]
        e_el = ET.SubElement(graph_el, "edge", {
            "id": str(ed["id"]),
            "source": str(ed["source"]),
            "target": str(ed["target"]),
        })
        for kid, field in [("d3", "edge_type"), ("d4", "basis"), ("d5", "strength"), ("d6", "tier"), ("d7", "reason_text")]:
            d = ET.SubElement(e_el, "data", {"key": kid})
            d.text = str(ed.get(field, ""))

    return ET.tostring(graphml, encoding="unicode", xml_declaration=True)
