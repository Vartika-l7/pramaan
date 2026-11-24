"""Phase 4 Part B: Comprehensive Test Pyramid (Parsers, Extractors, Detectors, Verifier, Spatial/Temporal, Determinism, Cross-Check, GT-01..GT-15)."""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.db import SCHEMA_SQL
from backend.app.main import app
from backend.app.ingest.service import ingest_file, verify_case_integrity
from backend.app.ingest.registry import parse_and_store_evidence, registry
from backend.app.extract.patterns import extract_all_identifiers
from backend.app.extract.language import detect_script, detect_language, transliterate_devanagari_to_latin
from backend.app.extract.names import extract_persons, clean_person_name
from backend.app.extract.locations import extract_locations
from backend.app.extract.resolve import run_entity_extraction
from backend.app.correlate.edges import generate_correlation_edges
from backend.app.correlate.patterns import detect_mule_funnel_pattern
from backend.app.correlate.graph import get_cytoscape_graph
from backend.app.timeline.anomalies import detect_timeline_anomalies, detect_spatial_movement
from backend.app.authenticity.exif import inspect_image_authenticity
from backend.app.authenticity.statement_checks import verify_statement_arithmetic
from backend.app.sequence.generator import generate_event_sequence
from backend.app.scene.reconstructor import reconstruct_scene
from backend.app.spatial.geo import haversine_km
from backend.app.spatial.analyzer import build_spatial_observations, analyze_spatial_relationships
from backend.app.parsers.time_utils import normalise_to_utc, reverse_clock_offset
from backend.app.verify.claim_verifier import verify_claims
from backend.app.ai.provider import DeterministicProvider
from backend.app.report.package import assemble_case_package

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data" / "case_alpha"
SKIP_DATA_FILES = {"ground_truth.json", "benchmark_results.json", "assistant_eval_results.json", "tower_registry.csv"}


def _fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


def _run_full_pipeline(conn: sqlite3.Connection, store_root: Path | None = None, data_dir: Path = DATA_DIR):
    import backend.app.ingest.service as ingest_svc
    import backend.app.authenticity.exif as exif_mod
    import backend.app.authenticity.ela as ela_mod

    orig_store = ingest_svc.EVIDENCE_STORE_DIR
    orig_ela = ela_mod.ELA_DIR
    tmp_ctx = None if store_root is not None else tempfile.TemporaryDirectory(prefix="pramaan_test_store_")
    base_dir = store_root if store_root is not None else Path(tmp_ctx.name)
    ingest_svc.EVIDENCE_STORE_DIR = base_dir / "evidence_store"
    ela_mod.ELA_DIR = base_dir / "ela"
    ela_mod.ELA_DIR.mkdir(parents=True, exist_ok=True)
    exif_mod.ELA_DIR = ela_mod.ELA_DIR
    try:
        files = sorted(f for f in data_dir.iterdir() if f.is_file() and f.name not in SKIP_DATA_FILES)
        for f in files:
            with open(f, "rb") as fh:
                res = ingest_file(conn, fh, f.name, actor="TEST_DETERMINISM")
            parse_and_store_evidence(conn, res["id"], actor="TEST_DETERMINISM")

        run_entity_extraction(conn)
        detect_timeline_anomalies(conn)
        detect_spatial_movement(conn)
        generate_correlation_edges(conn)
        detect_mule_funnel_pattern(conn)
        inspect_image_authenticity(conn)
        verify_statement_arithmetic(conn)
        episodes = generate_event_sequence(conn)
        scene = reconstruct_scene(conn, episode_id=episodes[0]["id"] if episodes else None)

        prov = DeterministicProvider()
        events = [dict(r) for r in conn.execute("SELECT id, ts_utc, kind, text, amount, actor, counterparty FROM events ORDER BY ts_utc ASC, id ASC LIMIT 200;").fetchall()]
        anomalies = [dict(r) for r in conn.execute("SELECT id, kind, severity, description FROM anomalies ORDER BY id ASC;").fetchall()]
        edges = [dict(r) for r in conn.execute("SELECT id, src, dst, edge_type, reason_text FROM edges ORDER BY id ASC;").fetchall()]
        drafted = prov.draft_claims({"events": events, "anomalies": anomalies, "edges": edges})
        ver_report = verify_claims(conn, drafted)
        return episodes, scene, ver_report
    finally:
        ingest_svc.EVIDENCE_STORE_DIR = orig_store
        ela_mod.ELA_DIR = orig_ela
        exif_mod.ELA_DIR = orig_ela
        if tmp_ctx is not None:
            tmp_ctx.cleanup()


def test_unit_all_parsers_reconcile(tmp_path: Path):
    """Unit test every registered parser produces reconciled parse reports."""
    sample_cases = [
        (DATA_DIR / "whatsapp_group_alpha_wealth.txt", "whatsapp"),
        (DATA_DIR / "bank_statement_meera.pdf", "bank_pdf"),
        (DATA_DIR / "bank_statement_mule_B.csv", "bank_csv"),
        (DATA_DIR / "call_log_device1.csv", "calllog"),
        (DATA_DIR / "screenshot_payment_genuine.png", "image"),
        (DATA_DIR / "telegram_alpha_export.json", "social_telegram"),
        (DATA_DIR / "cloud_location_history.json", "cloud_location"),
        (DATA_DIR / "cloud_activity_log.csv", "cloud_activity"),
        (DATA_DIR / "email_support.eml", "email"),
        (DATA_DIR / "network_portal_logs.csv", "network_log"),
        (DATA_DIR / "cctv_camera_registry.csv", "cctv_index"),
        (DATA_DIR / "cam_noi_atm_01_clip.mp4", "cctv_video"),
    ]
    gen_social = tmp_path / "generic_social.json"
    gen_social.write_text(json.dumps({"posts": [{"timestamp": "2026-03-14T10:00:00+05:30", "author": "A", "text": "Hi"}]}), encoding="utf-8")
    sample_cases.append((gen_social, "social_generic"))

    for fpath, expected_type in sample_cases:
        parser = registry.get_parser(fpath, fpath.name)
        assert parser is not None, f"No parser matched {fpath.name}"
        assert parser.source_type == expected_type
        events, report = parser.parse_with_report(fpath, "ev_unit", fpath.name)
        assert len(events) >= 1
        assert report.to_dict()["reconciled"] is True


def test_unit_all_extractors():
    """Unit test pattern, language, person-name, and location extractors."""
    text = (
        "Contact Vikram Sharma Ji on device D1 at +91 90000 10001, "
        "UPI vikram.alpha@okaxis, IFSC HDFC0001234, A/C 912345678901, "
        "URL https://alpha-wealth.example.com near Noida Sector 62."
    )
    ids = extract_all_identifiers(text)
    id_types = {m.type for m in ids}
    assert {"PHONE", "UPI", "DEVICE", "IFSC", "ACCOUNT", "URL"}.issubset(id_types)

    persons = extract_persons(text)
    assert any("Vikram Sharma" in p.value_norm for p in persons)
    assert clean_person_name("Vikram Sharma Ji") == "Vikram Sharma"

    locs = extract_locations(text)
    assert any("Noida Sector 62" in l.value_norm for l in locs)

    assert detect_script("विक्रम शर्मा ने पैसे भेजे") == "DEVANAGARI"
    assert detect_language("विक्रम शर्मा ने पैसे भेजे") == "hi"
    latin = transliterate_devanagari_to_latin("विक्रम शर्मा").lower()
    assert "vikram" in latin and "sharma" in latin


def test_unit_verifier_rules_v1_v2_v4_v5():
    """Unit test every claim verifier rule: V1 (invalid ref), V2 (bad quote), V4 (no refs), V5 (certainty neutralization)."""
    conn = _fresh_conn()
    # Insert one evidence + one event
    conn.execute(
        "INSERT INTO evidence (id, exhibit_id, filename, sha256, size_bytes, source_type, received_at_utc, stored_path) VALUES ('evi_1', 'EX-001', 'chat.txt', 'abc', 10, 'whatsapp', '2026-03-14T00:00:00Z', '/tmp/x');"
    )
    conn.execute(
        "INSERT INTO events (id, evidence_id, source_type, ts_utc, ts_original, tz_assumed, kind, text, ref_json) VALUES ('evt_1', 'evi_1', 'whatsapp', '2026-03-14T10:00:00Z', '2026-03-14 15:30', 'Asia/Kolkata', 'message', 'Send INR 50000 to vikram.alpha@okaxis', '{}');"
    )
    conn.commit()

    claims = [
        {"id": "c_v4", "text": "No source claim", "kind": "finding", "refs": [], "quotes": []},
        {"id": "c_v1", "text": "Bad ref claim", "kind": "finding", "refs": ["evt_nonexistent"], "quotes": []},
        {"id": "c_v2", "text": "Bad quote claim", "kind": "finding", "refs": ["evt_1"], "quotes": [{"event_id": "evt_1", "text": "NOT IN EVENT"}]},
        {"id": "c_v5", "text": "He is guilty of sending funds.", "kind": "finding", "refs": ["evt_1"], "quotes": [{"event_id": "evt_1", "text": "vikram.alpha@okaxis"}]},
    ]
    report = verify_claims(conn, claims)
    assert report["proposed_count"] == 4
    assert report["removed_count"] == 3
    assert report["verified_count"] == 1
    assert report["modified_count"] == 1
    reasons = " ".join(r["reason"] for r in report["removed_claims"])
    assert "Rule V4" in reasons and "Rule V1" in reasons and "Rule V2" in reasons
    assert "alleged to be involved" in report["verified_claims"][0]["text"]
    assert "guilty" not in report["verified_claims"][0]["text"].lower()


def test_spatial_and_temporal_logic():
    """Verify haversine distances, impossible travel threshold, clock offsets, and sequence/scene determinism."""
    # Known city pairs
    delhi_mumbai = haversine_km(28.6139, 77.2090, 19.0760, 72.8777)
    assert 1120.0 < delhi_mumbai < 1180.0
    noida_jaipur = haversine_km(28.6279, 77.3649, 26.9124, 75.7873)
    assert 230.0 < noida_jaipur < 270.0
    assert haversine_km(28.6139, 77.2090, 28.6139, 77.2090) == pytest.approx(0.0, abs=1e-6)

    # Clock offset apply & reverse
    corrected, orig = normalise_to_utc("2026-03-15 14:15:48", default_tz="Asia/Kolkata", clock_offset_seconds=252)
    assert "08:50:00" in corrected
    assert "08:45:48" in orig
    assert reverse_clock_offset(corrected, 252) == orig

    # Impossible travel unit check (>200 km/h flagged, normal speed not flagged)
    conn = _fresh_conn()
    conn.execute("INSERT INTO evidence (id, exhibit_id, filename, sha256, size_bytes, source_type, received_at_utc, stored_path) VALUES ('evi_1', 'EX-001', 'loc.json', 'a', 10, 'cloud_location', '2026-03-15T00:00:00Z', '/tmp/a');")
    conn.execute("INSERT INTO events (id, evidence_id, source_type, ts_utc, ts_original, tz_assumed, actor, kind, text, ref_json) VALUES ('evt_j', 'evi_1', 'cloud_location', '2026-03-15T08:00:00+00:00', '2026-03-15T08:00:00Z', 'UTC', 'D1', 'location_ping', 'Jaipur', ?);", (json.dumps({"lat": 26.9124, "lon": 75.7873, "place_name": "Jaipur", "device_id": "D1", "accuracy_m": 20}),))
    conn.execute("INSERT INTO events (id, evidence_id, source_type, ts_utc, ts_original, tz_assumed, actor, kind, text, ref_json) VALUES ('evt_n', 'evi_1', 'cloud_location', '2026-03-15T08:20:00+00:00', '2026-03-15T08:20:00Z', 'UTC', 'D1', 'location_ping', 'Noida', ?);", (json.dumps({"lat": 28.6279, "lon": 77.3649, "place_name": "Noida", "device_id": "D1", "accuracy_m": 20}),))
    conn.commit()
    build_spatial_observations(conn)
    res = analyze_spatial_relationships(conn)
    assert len(res["impossible_travel"]) == 1
    assert res["impossible_travel"][0]["implied_speed_kmh"] > 200.0


@pytest.mark.integration
def test_full_pipeline_determinism(synthetic_dataset_dir: Path):
    """Run full pipeline twice on fresh DBs and assert hashes, IDs, edges, anomalies, claims, episodes, and scenes match."""
    conn1 = _fresh_conn()
    conn2 = _fresh_conn()
    try:
        ep1, sc1, ver1 = _run_full_pipeline(conn1, data_dir=synthetic_dataset_dir)
        ep2, sc2, ver2 = _run_full_pipeline(conn2, data_dir=synthetic_dataset_dir)

        # Evidence hashes & IDs
        ev1 = [dict(r) for r in conn1.execute("SELECT id, exhibit_id, filename, sha256, size_bytes FROM evidence ORDER BY exhibit_id;").fetchall()]
        ev2 = [dict(r) for r in conn2.execute("SELECT id, exhibit_id, filename, sha256, size_bytes FROM evidence ORDER BY exhibit_id;").fetchall()]
        assert ev1 == ev2

        # Event IDs
        events1 = [r["id"] for r in conn1.execute("SELECT id FROM events ORDER BY ts_utc ASC, id ASC;").fetchall()]
        events2 = [r["id"] for r in conn2.execute("SELECT id FROM events ORDER BY ts_utc ASC, id ASC;").fetchall()]
        assert events1 == events2

        # Edges
        edges1 = [dict(r) for r in conn1.execute("SELECT id, src, dst, edge_type, basis, strength, event_ids_json FROM edges ORDER BY id;").fetchall()]
        edges2 = [dict(r) for r in conn2.execute("SELECT id, src, dst, edge_type, basis, strength, event_ids_json FROM edges ORDER BY id;").fetchall()]
        assert edges1 == edges2

        # Anomalies
        anom1 = [dict(r) for r in conn1.execute("SELECT id, kind, severity, evidence_id, event_ids_json, description FROM anomalies ORDER BY id;").fetchall()]
        anom2 = [dict(r) for r in conn2.execute("SELECT id, kind, severity, evidence_id, event_ids_json, description FROM anomalies ORDER BY id;").fetchall()]
        assert anom1 == anom2

        # Claims in deterministic mode
        assert ver1["verified_claims"] == ver2["verified_claims"]
        assert ver1["removed_claims"] == ver2["removed_claims"]

        # Sequence & scene determinism
        assert ep1 == ep2
        assert sc1 == sc2
    finally:
        conn1.close()
        conn2.close()


@pytest.mark.integration
def test_verifier_and_backend_crosscheck(tmp_path: Path, synthetic_dataset_dir: Path):
    """Standalone verifier.py and backend verify_case_integrity must agree on intact and tampered packages."""
    conn = _fresh_conn()
    try:
        _run_full_pipeline(conn, store_root=tmp_path / "store", data_dir=synthetic_dataset_dir)

        pkg_dir = tmp_path / "pkg_intact"
        assemble_case_package(conn, case_id="CROSS-CHECK", target_package_dir=pkg_dir)

        backend_ok = verify_case_integrity(conn)
        proc_ok = subprocess.run(
            [sys.executable, str(ROOT / "verifier" / "verifier.py"), "--package", str(pkg_dir)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert backend_ok["intact"] is True
        assert proc_ok.returncode == 0
        assert backend_ok["merkle_root"] in proc_ok.stdout

        # Tamper with an evidence file in the exported package AND test tampered manifest
        ev_files = sorted((pkg_dir / "evidence").iterdir())
        assert len(ev_files) > 0
        ev_files[0].chmod(0o644)
        ev_files[0].write_bytes(b"TAMPERED_DATA")

        proc_tampered = subprocess.run(
            [sys.executable, str(ROOT / "verifier" / "verifier.py"), "--package", str(pkg_dir)],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert proc_tampered.returncode != 0
        assert "TAMPERING OR CORRUPTION DETECTED" in proc_tampered.stdout

        # Tamper manifest in DB and verify backend also fails
        conn.execute("UPDATE manifests SET merkle_root = '0000' || substr(merkle_root, 5);")
        conn.commit()
        backend_tampered = verify_case_integrity(conn)
        assert backend_tampered["intact"] is False
    finally:
        conn.close()


@pytest.mark.integration
def test_ground_truth_gt01_to_gt15_recall(synthetic_dataset_dir: Path):
    """Verify all 15 planted ground-truth facts (GT-01..GT-15) are detected."""
    conn = _fresh_conn()
    try:
        _run_full_pipeline(conn, data_dir=synthetic_dataset_dir)

        gt = json.loads((synthetic_dataset_dir / "ground_truth.json").read_text(encoding="utf-8"))
        assert len(gt["planted_facts"]) == 15

        g = get_cytoscape_graph(conn)
        edge_types = {e["data"]["edge_type"] for e in g["edges"]}
        anom_kinds = {r["kind"] for r in conn.execute("SELECT kind FROM anomalies;").fetchall()}
        custody_actions = {r["action"] for r in conn.execute("SELECT action FROM custody_log;").fetchall()}

        checks = {
            "GT-01": "SAME_IDENTIFIER" in edge_types,
            "GT-02": "PATTERN_FUNNEL" in edge_types,
            "GT-03": "SAME_DEVICE" in edge_types,
            "GT-04": "ANOMALY_CHAT_GAP" in anom_kinds,
            "GT-05": "ANOMALY_OUT_OF_ORDER" in anom_kinds,
            "GT-06": "ANOMALY_IMAGE_EDITED" in anom_kinds,
            "GT-07": "SAME_MEDIA" in edge_types,
            "GT-08": "ANOMALY_BALANCE_MISMATCH" in anom_kinds,
            "GT-09": "SAME_PERSON_FUZZY" in edge_types,
            "GT-10": "SPATIAL_THREAD" in anom_kinds,
            "GT-11": "IMPOSSIBLE_TRAVEL" in anom_kinds,
            "GT-12": "SHARED_IP_CROSS_SOURCE" in edge_types,
            "GT-13": "TEMPORAL_CO_OCCURRENCE" in edge_types,
            "GT-14": "CLOCK_OFFSET_RECORDED" in custody_actions,
            "GT-15": "LOGIN_FROM_IP" in edge_types,
        }
        missing = [k for k, ok in checks.items() if not ok]
        assert not missing, f"Missing planted facts: {missing}"
    finally:
        conn.close()


@pytest.mark.integration
def test_scene_endpoint_determinism():
    """Verify /api/scene returns identical deterministic output across repeated calls."""
    with TestClient(app) as client:
        r1 = client.get("/api/scene")
        r2 = client.get("/api/scene")
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json() == r2.json()
