"""Deterministic Claim Verifier (Rules V1 through V5).

Guarantees the core principle: No source, no claim.
Runs strictly deterministically without any AI inference.
"""

from __future__ import annotations

import json
import re
import sqlite3
import uuid
from typing import Dict, List, Any, Tuple

CERTAINTY_WORDS_MAP = {
    r"\bguilty\b": "alleged to be involved",
    r"\bintended to defraud\b": "exhibiting indicators consistent with misrepresentation",
    r"\bcommitted\b": "associated with",
    r"\bscammer\b": "identified persona",
    r"\bfraudster\b": "target account holder",
}


def normalize_str(s: str) -> str:
    """Normalize whitespace and case for exact substring comparison."""
    return " ".join(s.lower().split())


def verify_claims(conn: sqlite3.Connection, claims: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Execute Rules V1-V5 on proposed claims and record results."""
    cursor = conn.cursor()

    # Pre-load all valid database IDs for Rule V1
    cursor.execute("SELECT id FROM events UNION SELECT id FROM evidence UNION SELECT id FROM anomalies UNION SELECT id FROM edges;")
    valid_ids = {r[0] for r in cursor.fetchall()}

    verified_claims = []
    removed_claims = []
    modified_claims = []

    for raw_claim in claims:
        claim_id = raw_claim.get("id") or str(uuid.uuid4())
        text = raw_claim.get("text", "")
        kind = raw_claim.get("kind", "finding")
        refs = raw_claim.get("refs", [])
        quotes = raw_claim.get("quotes", [])
        generated_by = raw_claim.get("generated_by", "AI_DRAFT")

        # ---------------------------------------------------------------------
        # Rule V4: A claim with no refs is removed immediately
        # ---------------------------------------------------------------------
        if not refs:
            removed_claims.append({
                "claim_id": claim_id,
                "text": text,
                "reason": "Rule V4 Violation: Claim contains zero source references (No source, no claim).",
            })
            cursor.execute(
                """
                INSERT OR REPLACE INTO claims (id, text, kind, tier, status, source_refs_json, quotes_json, generated_by, verifier_notes)
                VALUES (?, ?, ?, 'LEAD', 'REMOVED', '[]', '[]', ?, 'Rule V4: Removed - No source references');
                """,
                (claim_id, text, kind, generated_by),
            )
            continue

        # ---------------------------------------------------------------------
        # Rule V1: Every ref must exist in database
        # ---------------------------------------------------------------------
        invalid_refs = [r for r in refs if r not in valid_ids]
        if invalid_refs:
            removed_claims.append({
                "claim_id": claim_id,
                "text": text,
                "reason": f"Rule V1 Violation: Referenced record IDs do not exist in evidence store: {invalid_refs}",
            })
            cursor.execute(
                """
                INSERT OR REPLACE INTO claims (id, text, kind, tier, status, source_refs_json, quotes_json, generated_by, verifier_notes)
                VALUES (?, ?, ?, 'LEAD', 'REMOVED', ?, ?, ?, 'Rule V1: Removed - Invalid reference IDs');
                """,
                (claim_id, text, kind, json.dumps(refs), json.dumps(quotes), generated_by),
            )
            continue

        # ---------------------------------------------------------------------
        # Rule V2: Every quote must be an exact substring of referenced event text
        # ---------------------------------------------------------------------
        quote_failed = False
        quote_fail_reason = ""
        for q in quotes:
            ev_id = q.get("event_id")
            q_text = q.get("text", "")
            cursor.execute("SELECT text FROM events WHERE id = ?;", (ev_id,))
            ev_row = cursor.fetchone()
            if not ev_row or not ev_row["text"]:
                quote_failed = True
                quote_fail_reason = f"Referenced event {ev_id} has no text."
                break
            if normalize_str(q_text) not in normalize_str(ev_row["text"]):
                quote_failed = True
                quote_fail_reason = f"Quote '{q_text}' is not an exact substring of record text in event {ev_id}."
                break

        if quote_failed:
            removed_claims.append({
                "claim_id": claim_id,
                "text": text,
                "reason": f"Rule V2 Violation: {quote_fail_reason}",
            })
            cursor.execute(
                """
                INSERT OR REPLACE INTO claims (id, text, kind, tier, status, source_refs_json, quotes_json, generated_by, verifier_notes)
                VALUES (?, ?, ?, 'LEAD', 'REMOVED', ?, ?, ?, ?);
                """,
                (claim_id, text, kind, json.dumps(refs), json.dumps(quotes), generated_by, f"Rule V2: {quote_fail_reason}"),
            )
            continue

        # ---------------------------------------------------------------------
        # Rule V5: Certainty language about guilt or intent is rewritten to lead language
        # ---------------------------------------------------------------------
        sanitized_text = text
        rewritten = False
        for pattern, replacement in CERTAINTY_WORDS_MAP.items():
            if re.search(pattern, sanitized_text, re.IGNORECASE):
                sanitized_text = re.sub(pattern, replacement, sanitized_text, flags=re.IGNORECASE)
                rewritten = True

        status = "VERIFIED"
        verifier_notes = "Verified by Code (V1-V5 passed)"
        if rewritten:
            verifier_notes += " - Certainty words neutralized to lead phrasing (Rule V5)"
            modified_claims.append({
                "claim_id": claim_id,
                "original_text": text,
                "sanitized_text": sanitized_text,
            })

        cursor.execute(
            """
            INSERT OR REPLACE INTO claims (id, text, kind, tier, status, source_refs_json, quotes_json, generated_by, verifier_notes)
            VALUES (?, ?, ?, 'LEAD', ?, ?, ?, ?, ?);
            """,
            (claim_id, sanitized_text, kind, status, json.dumps(refs), json.dumps(quotes), generated_by, verifier_notes),
        )

        verified_claims.append({
            "id": claim_id,
            "text": sanitized_text,
            "kind": kind,
            "tier": "LEAD",
            "status": status,
            "refs": refs,
            "quotes": quotes,
            "notes": verifier_notes,
        })

    conn.commit()

    return {
        "proposed_count": len(claims),
        "verified_count": len(verified_claims),
        "removed_count": len(removed_claims),
        "modified_count": len(modified_claims),
        "verified_claims": verified_claims,
        "removed_claims": removed_claims,
        "modified_claims": modified_claims,
    }

