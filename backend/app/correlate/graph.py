"""Knowledge Graph assembly and Cytoscape format conversion."""

from __future__ import annotations

import json
import sqlite3
from typing import Dict, List, Any, Optional


def get_cytoscape_graph(
    conn: sqlite3.Connection,
    type_filter: Optional[str] = None,
    tier_filter: Optional[str] = None,
    min_strength: float = 0.0,
) -> Dict[str, Any]:
    """Assemble the unified forensic knowledge graph formatted for Cytoscape.js."""
    cursor = conn.cursor()

    # 1. Fetch entities as primary graph nodes
    cursor.execute(
        """
        SELECT e.id, e.type, e.value_norm, e.display, COUNT(m.id) as mention_count
        FROM entities e
        LEFT JOIN mentions m ON e.id = m.entity_id
        GROUP BY e.id;
        """
    )
    entity_rows = cursor.fetchall()

    # 2. Fetch exhibits as source nodes
    cursor.execute("SELECT id, exhibit_id, filename, source_type FROM evidence;")
    evidence_rows = cursor.fetchall()

    nodes = []
    node_ids = set()

    # Add entity nodes
    for r in entity_rows:
        if type_filter and r["type"].lower() != type_filter.lower():
            continue
        nid = str(r["id"])
        node_ids.add(nid)
        nodes.append({
            "data": {
                "id": nid,
                "label": r["display"],
                "type": r["type"],
                "tier": "VERIFIED BY CODE",
                "mention_count": r["mention_count"],
            }
        })

    # Add evidence exhibit nodes
    for ev in evidence_rows:
        ex_id = ev["exhibit_id"]
        node_ids.add(ex_id)
        nodes.append({
            "data": {
                "id": ex_id,
                "label": f"{ex_id} ({ev['filename']})",
                "type": "EXHIBIT",
                "tier": "VERIFIED BY CODE",
                "source_type": ev["source_type"],
            }
        })

    # 3. Fetch correlation edges
    cursor.execute("SELECT * FROM edges WHERE strength >= ?;", (min_strength,))
    edge_rows = cursor.fetchall()

    edges = []
    for edge in edge_rows:
        if tier_filter and edge["tier"].upper() != tier_filter.upper():
            continue

        src, dst = edge["src"], edge["dst"]

        # Ensure synthetic nodes exist if src or dst are raw values
        if src not in node_ids:
            nodes.append({
                "data": {
                    "id": src,
                    "label": src,
                    "type": "EXTERNAL",
                    "tier": "LEAD",
                }
            })
            node_ids.add(src)

        if dst not in node_ids:
            nodes.append({
                "data": {
                    "id": dst,
                    "label": dst,
                    "type": "EXTERNAL",
                    "tier": "LEAD",
                }
            })
            node_ids.add(dst)

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

    return {
        "nodes": nodes,
        "edges": edges,
        "total_nodes": len(nodes),
        "total_edges": len(edges),
    }

