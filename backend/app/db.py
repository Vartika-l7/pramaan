"""SQLite database connection and schema management for PRAMAAN."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Optional
from backend.app.config import CASE_DATA_DIR, DEFAULT_CASE_ID


SCHEMA_SQL = """
-- Evidence store metadata
CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    exhibit_id TEXT UNIQUE NOT NULL,
    filename TEXT NOT NULL,
    sha256 TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    received_at_utc TEXT NOT NULL,
    stored_path TEXT NOT NULL,
    parser TEXT,
    parse_status TEXT DEFAULT 'PENDING',
    parse_notes TEXT,
    parse_report_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_evidence_sha256 ON evidence(sha256);
CREATE INDEX IF NOT EXISTS idx_evidence_exhibit_id ON evidence(exhibit_id);

-- Tamper-evident hash-chained custody log (Append-only)
CREATE TABLE IF NOT EXISTS custody_log (
    seq INTEGER PRIMARY KEY AUTOINCREMENT,
    ts_utc TEXT NOT NULL,
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    evidence_id TEXT,
    details_json TEXT,
    prev_hash TEXT NOT NULL,
    entry_hash TEXT NOT NULL
);

-- Triggers ensuring custody_log is strictly append-only
CREATE TRIGGER IF NOT EXISTS trg_custody_no_update
BEFORE UPDATE ON custody_log
BEGIN
    SELECT RAISE(FAIL, 'CUSTODY_VIOLATION: custody_log is strictly append-only; updates forbidden');
END;

CREATE TRIGGER IF NOT EXISTS trg_custody_no_delete
BEFORE DELETE ON custody_log
BEGIN
    SELECT RAISE(FAIL, 'CUSTODY_VIOLATION: custody_log is strictly append-only; deletions forbidden');
END;

-- Unified chronological event store across all parsed evidence
CREATE TABLE IF NOT EXISTS events (
    id TEXT PRIMARY KEY,
    evidence_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    ts_utc TEXT NOT NULL,
    ts_original TEXT NOT NULL,
    tz_assumed TEXT NOT NULL,
    actor TEXT,
    counterparty TEXT,
    kind TEXT NOT NULL,
    text TEXT,
    amount REAL,
    currency TEXT,
    location_id TEXT,
    clock_offset_seconds INTEGER DEFAULT 0,
    offset_source TEXT,
    ref_json TEXT NOT NULL,
    FOREIGN KEY(evidence_id) REFERENCES evidence(id)
);

CREATE INDEX IF NOT EXISTS idx_events_ts_utc ON events(ts_utc);
CREATE INDEX IF NOT EXISTS idx_events_evidence_id ON events(evidence_id);
CREATE INDEX IF NOT EXISTS idx_events_kind ON events(kind);
CREATE INDEX IF NOT EXISTS idx_events_actor ON events(actor);

-- Normalised entity store
CREATE TABLE IF NOT EXISTS entities (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    value_norm TEXT NOT NULL,
    display TEXT NOT NULL,
    first_event_id TEXT,
    UNIQUE(type, value_norm)
);

CREATE INDEX IF NOT EXISTS idx_entities_type ON entities(type);
CREATE INDEX IF NOT EXISTS idx_entities_val ON entities(value_norm);

-- Entity mentions with exact character spans
CREATE TABLE IF NOT EXISTS mentions (
    id TEXT PRIMARY KEY,
    entity_id TEXT NOT NULL,
    event_id TEXT NOT NULL,
    char_start INTEGER NOT NULL,
    char_end INTEGER NOT NULL,
    extractor TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'VERIFIED BY CODE',
    FOREIGN KEY(entity_id) REFERENCES entities(id),
    FOREIGN KEY(event_id) REFERENCES events(id)
);

CREATE INDEX IF NOT EXISTS idx_mentions_entity ON mentions(entity_id);
CREATE INDEX IF NOT EXISTS idx_mentions_event ON mentions(event_id);

-- Correlated knowledge graph edges
CREATE TABLE IF NOT EXISTS edges (
    id TEXT PRIMARY KEY,
    src TEXT NOT NULL,
    dst TEXT NOT NULL,
    edge_type TEXT NOT NULL,
    basis TEXT NOT NULL,
    reason_text TEXT NOT NULL,
    strength REAL NOT NULL,
    tier TEXT NOT NULL DEFAULT 'LEAD',
    status TEXT NOT NULL DEFAULT 'LEAD',
    event_ids_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_edges_src ON edges(src);
CREATE INDEX IF NOT EXISTS idx_edges_dst ON edges(dst);
CREATE INDEX IF NOT EXISTS idx_edges_type ON edges(edge_type);

-- Forensic anomalies and timeline irregularities
CREATE TABLE IF NOT EXISTS anomalies (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    severity TEXT NOT NULL,
    evidence_id TEXT NOT NULL,
    event_ids_json TEXT NOT NULL,
    description TEXT NOT NULL,
    detail_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'LEAD',
    FOREIGN KEY(evidence_id) REFERENCES evidence(id)
);

CREATE INDEX IF NOT EXISTS idx_anomalies_evidence ON anomalies(evidence_id);
CREATE INDEX IF NOT EXISTS idx_anomalies_severity ON anomalies(severity);

-- Geographic locations for offline spatial correlation
CREATE TABLE IF NOT EXISTS locations (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    lat REAL,
    lon REAL,
    kind TEXT
);

-- Spatio-temporal observations (entity/device at location over time interval)
CREATE TABLE IF NOT EXISTS observations (
    id TEXT PRIMARY KEY,
    entity_or_device TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    location_id TEXT,
    place_name TEXT NOT NULL,
    lat REAL,
    lon REAL,
    start_ts_utc TEXT NOT NULL,
    end_ts_utc TEXT NOT NULL,
    accuracy_m REAL NOT NULL,
    source_event_id TEXT NOT NULL,
    source_type TEXT NOT NULL,
    FOREIGN KEY(source_event_id) REFERENCES events(id)
);

CREATE INDEX IF NOT EXISTS idx_observations_entity ON observations(entity_or_device);
CREATE INDEX IF NOT EXISTS idx_observations_time ON observations(start_ts_utc, end_ts_utc);

-- Automated event-sequence episodes
CREATE TABLE IF NOT EXISTS episodes (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    start_ts_utc TEXT NOT NULL,
    end_ts_utc TEXT NOT NULL,
    actors_json TEXT NOT NULL,
    devices_json TEXT NOT NULL,
    locations_json TEXT NOT NULL,
    exhibits_json TEXT NOT NULL,
    anomalies_json TEXT NOT NULL,
    steps_json TEXT NOT NULL,
    title_source TEXT NOT NULL DEFAULT 'template'
);

-- AI-drafted claims and verification statuses
CREATE TABLE IF NOT EXISTS claims (
    id TEXT PRIMARY KEY,
    text TEXT NOT NULL,
    kind TEXT NOT NULL,
    tier TEXT NOT NULL DEFAULT 'LEAD',
    status TEXT NOT NULL DEFAULT 'PROPOSED',
    source_refs_json TEXT NOT NULL,
    quotes_json TEXT NOT NULL,
    generated_by TEXT NOT NULL,
    verifier_notes TEXT,
    ai_run_id TEXT
);

-- Tamper-evident AI run records (Phase 4 Part C)
CREATE TABLE IF NOT EXISTS ai_runs (
    id TEXT PRIMARY KEY,
    ts_utc TEXT NOT NULL,
    task TEXT NOT NULL,
    model_name TEXT NOT NULL,
    model_version TEXT NOT NULL,
    parameters_json TEXT NOT NULL,
    prompt TEXT NOT NULL,
    input_record_ids_json TEXT NOT NULL,
    raw_output TEXT NOT NULL,
    verifier_result_json TEXT NOT NULL,
    record_sha256 TEXT NOT NULL
);

-- Human review audit trail
CREATE TABLE IF NOT EXISTS reviews (
    id TEXT PRIMARY KEY,
    item_type TEXT NOT NULL,
    item_id TEXT NOT NULL,
    decision TEXT NOT NULL,
    reviewer TEXT NOT NULL,
    ts TEXT NOT NULL,
    note TEXT
);

-- Case manifest & Merkle root signatures
CREATE TABLE IF NOT EXISTS manifests (
    id TEXT PRIMARY KEY,
    created_at_utc TEXT NOT NULL,
    merkle_root TEXT NOT NULL,
    manifest_json TEXT NOT NULL,
    signature_b64 TEXT NOT NULL,
    public_key_b64 TEXT NOT NULL
);
"""


def get_db_path(case_id: Optional[str] = None) -> Path:
    cid = case_id or DEFAULT_CASE_ID
    return CASE_DATA_DIR / f"{cid}.db"


def get_db_connection(case_id: Optional[str] = None) -> sqlite3.Connection:
    """Return an active SQLite connection configured with WAL mode and foreign keys."""
    db_path = get_db_path(case_id)
    conn = sqlite3.connect(str(db_path), timeout=15.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_db(case_id: Optional[str] = None) -> sqlite3.Connection:
    """Initialize database tables, indexes, and triggers."""
    conn = get_db_connection(case_id)
    with conn:
        conn.executescript(SCHEMA_SQL)
        # Migrate existing schema if parse_report_json or clock_offset columns are missing
        cursor = conn.cursor()
        cursor.execute("PRAGMA table_info(evidence);")
        columns = [row[1] for row in cursor.fetchall()]
        if "parse_report_json" not in columns:
            cursor.execute("ALTER TABLE evidence ADD COLUMN parse_report_json TEXT;")
        cursor.execute("PRAGMA table_info(events);")
        ev_cols = [row[1] for row in cursor.fetchall()]
        if "clock_offset_seconds" not in ev_cols:
            cursor.execute("ALTER TABLE events ADD COLUMN clock_offset_seconds INTEGER DEFAULT 0;")
        if "offset_source" not in ev_cols:
            cursor.execute("ALTER TABLE events ADD COLUMN offset_source TEXT;")
        cursor.execute("PRAGMA table_info(claims);")
        claim_cols = [row[1] for row in cursor.fetchall()]
        if "ai_run_id" not in claim_cols:
            cursor.execute("ALTER TABLE claims ADD COLUMN ai_run_id TEXT;")
    return conn

