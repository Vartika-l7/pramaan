"""Merkle Tree implementation for evidence verification in PRAMAAN."""

from __future__ import annotations

import hashlib
import sqlite3
from typing import List, Tuple


def merkle_root_from_hashes(hashes: List[str]) -> str:
    """Compute the Merkle root from a sorted list of SHA-256 leaf hashes."""
    if not hashes:
        return hashlib.sha256(b"").hexdigest()

    current_level = list(hashes)
    while len(current_level) > 1:
        if len(current_level) % 2 != 0:
            # Duplicate the last leaf for balanced tree
            current_level.append(current_level[-1])

        next_level = []
        for i in range(0, len(current_level), 2):
            combined = current_level[i] + current_level[i + 1]
            parent_hash = hashlib.sha256(combined.encode("utf-8")).hexdigest()
            next_level.append(parent_hash)
        current_level = next_level

    return current_level[0]


def compute_case_merkle_root(conn: sqlite3.Connection) -> Tuple[str, List[Tuple[str, str]]]:
    """Compute the Merkle root over all evidence SHA-256 hashes ordered by exhibit_id ASC."""
    cursor = conn.cursor()
    cursor.execute("SELECT exhibit_id, sha256 FROM evidence ORDER BY exhibit_id ASC;")
    rows = cursor.fetchall()

    exhibits = [(r["exhibit_id"], r["sha256"]) for r in rows]
    hashes = [sha for _, sha in exhibits]
    root = merkle_root_from_hashes(hashes)
    return root, exhibits

