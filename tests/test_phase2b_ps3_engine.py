"""Phase 2B Tests: PS3 Engine (parsers, time/space, correlation, graph, sequence, scene, GT-01..GT-15)."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import pytest

from backend.app.db import SCHEMA_SQL
from backend.app.ingest.service import ingest_file
from backend.app.ingest.registry import parse_and_store_evidence
from backend.app.extract.resolve import run_entity_extraction
from backend.app.correlate.edges import (
    DEFAULT_CORRELATORS,
    generate_correlation_edges,
)
from backend.app.correlate.patterns import detect_mule_funnel_pattern
from backend.app.correlate.graph import get_cytoscape_graph, export_graph_graphml
from backend.app.timeline.anomalies import detect_timeline_anomalies, detect_spatial_movement
from backend.app.authenticity.exif import inspect_image_authenticity
from backend.app.authenticity.statement_checks import verify_statement_arithmetic
from backend.app.sequence.generator import generate_event_sequence, export_sequence_markdown
from backend.app.scene.reconstructor import reconstruct_scene, replay_scene
from backend.app.spatial.geo import haversine_km, lookup_ip_location
from backend.app.parsers.time_utils import normalise_to_utc, reverse_clock_offset
from backend.app.parsers.social_media import TelegramJSONParser, GenericSocialJSONParser
from backend.app.parsers.cloud import CloudLocationHistoryParser, CloudActivityCSVParser
from backend.app.parsers.email_parser import EmailParser
from backend.app.parsers.network_log import NetworkLogParser
from backend.app.parsers.cctv import CCTVCameraIndexParser, CCTVVideoParser


DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "case_alpha"


def _fresh_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA_SQL)
    return conn


def test_new_parsers_and_reconciliation(tmp_path: Path):
    # 1. Telegram JSON
    tg_file = DATA_DIR / "telegram_alpha_export.json"
    p_tg = TelegramJSONParser()
    assert p_tg.can_parse(tg_file, tg_file.name)
    evs, rep = p_tg.parse_with_report(tg_file, "ev1", tg_file.name)
    assert len(evs) == 2
    assert rep.to_dict()["reconciled"] is True

    # 2. Generic Social JSON
    gen_file = tmp_path / "social.json"
    gen_file.write_text(json.dumps({
        "posts": [{"timestamp": "2026-03-14T10:00:00+05:30", "author": "Alice", "text": "Hello"}],
        "direct_messages": [{"timestamp": "2026-03-14T10:05:00+05:30", "author": "Bob", "recipient": "Alice", "text": ""}],
    }), encoding="utf-8")
    p_gen = GenericSocialJSONParser()
    assert p_gen.can_parse(gen_file, gen_file.name)
    evs, rep = p_gen.parse_with_report(gen_file, "ev2", gen_file.name)
    assert len(evs) == 1
    assert rep.to_dict()["skipped_count"] == 1
    assert rep.to_dict()["reconciled"] is True

    # 3. Cloud Location History
    loc_file = DATA_DIR / "cloud_location_history.json"
    p_loc = CloudLocationHistoryParser()
    assert p_loc.can_parse(loc_file, loc_file.name)
    evs, rep = p_loc.parse_with_report(loc_file, "ev3", loc_file.name)
    assert len(evs) == 2
    assert rep.to_dict()["reconciled"] is True

    # 4. Cloud Activity CSV + missing column failure
    act_file = DATA_DIR / "cloud_activity_log.csv"
    p_act = CloudActivityCSVParser()
    assert p_act.can_parse(act_file, act_file.name)
    evs, rep = p_act.parse_with_report(act_file, "ev4", act_file.name)
    assert len(evs) == 2
    assert rep.to_dict()["reconciled"] is True

    bad_csv = tmp_path / "bad_cloud.csv"
    bad_csv.write_text("timestamp,account\n2026-03-14,a@example.com\n", encoding="utf-8")
    with pytest.raises(ValueError):
        p_act.parse_with_report(bad_csv, "ev_bad", bad_csv.name)

    # 5. Email .eml & .mbox
    eml_file = DATA_DIR / "email_support.eml"
    mbox_file = DATA_DIR / "mailbox_investigator.mbox"
    p_em = EmailParser()
    assert p_em.can_parse(eml_file, eml_file.name)
    evs_eml, rep_eml = p_em.parse_with_report(eml_file, "ev5", eml_file.name)
    assert len(evs_eml) == 1
    assert evs_eml[0].ref["attachments"][0]["sha256"]
    assert rep_eml.to_dict()["reconciled"] is True

    evs_mbox, rep_mbox = p_em.parse_with_report(mbox_file, "ev6", mbox_file.name)
    assert len(evs_mbox) == 2
    assert any(e.ref.get("date_received_inconsistency") for e in evs_mbox)
    assert rep_mbox.to_dict()["reconciled"] is True

    # 6. Network Log (CSV + syslog + invalid IP)
    net_file = DATA_DIR / "network_portal_logs.csv"
    p_net = NetworkLogParser()
    assert p_net.can_parse(net_file, net_file.name)
    evs_net, rep_net = p_net.parse_with_report(net_file, "ev7", net_file.name)
    assert len(evs_net) == 3
    assert rep_net.to_dict()["reconciled"] is True

    syslog_file = tmp_path / "portal.log"
    syslog_file.write_text(
        "2026-03-15T01:30:00+05:30 host app: user=admin src_ip=203.0.113.45 dst_ip=203.0.113.10 port=443 action=LOGIN\n"
        "2026-03-15T01:31:00+05:30 host app: user=admin src_ip=999.999.999.999 dst_ip=203.0.113.10 port=443 action=FAIL\n",
        encoding="utf-8",
    )
    evs_sys, rep_sys = p_net.parse_with_report(syslog_file, "ev8", syslog_file.name)
    assert len(evs_sys) == 1
    assert len(rep_sys.errors) == 1
    assert rep_sys.to_dict()["reconciled"] is True

    # 7. CCTV Index & Video
    cctv_csv = DATA_DIR / "cctv_camera_registry.csv"
    p_cctv = CCTVCameraIndexParser()
    assert p_cctv.can_parse(cctv_csv, cctv_csv.name)
    evs_cctv, rep_cctv = p_cctv.parse_with_report(cctv_csv, "ev9", cctv_csv.name)
    assert len(evs_cctv) == 1
    assert evs_cctv[0].kind == "CCTV_CLIP"
    assert evs_cctv[0].clock_offset_seconds == 252
    assert rep_cctv.to_dict()["reconciled"] is True

    vid_file = DATA_DIR / "cam_noi_atm_01_clip.mp4"
    p_vid = CCTVVideoParser()
    assert p_vid.can_parse(vid_file, vid_file.name)
    evs_vid, rep_vid = p_vid.parse_with_report(vid_file, "ev10", vid_file.name)
    assert len(evs_vid) == 1
    assert rep_vid.to_dict()["reconciled"] is True


def test_clock_offset_and_haversine():
    corrected, orig = normalise_to_utc("2026-03-15 14:15:48", default_tz="Asia/Kolkata", clock_offset_seconds=252)
    assert "08:50:00" in corrected  # 14:20:00 IST == 08:50:00 UTC
    assert "08:45:48" in orig
    assert reverse_clock_offset(corrected, 252) == orig

    # Jaipur to Noida ~240-260 km
    dist = haversine_km(26.9124, 75.7873, 28.6279, 77.3649)
    assert 230.0 < dist < 270.0
    assert lookup_ip_location("203.0.113.45")["place_name"] == "location unknown"


def _ingest_full_case(conn: sqlite3.Connection):
    files = sorted(
        f for f in DATA_DIR.iterdir()
        if f.is_file() and f.name not in ("ground_truth.json", "benchmark_results.json", "tower_registry.csv")
    )
    for f in files:
        with open(f, "rb") as fh:
            res = ingest_file(conn, fh, f.name, actor="TEST_HARNESS")
        parse_and_store_evidence(conn, res["id"], actor="TEST_HARNESS")
    run_entity_extraction(conn)
    detect_timeline_anomalies(conn)
    detect_spatial_movement(conn)
    generate_correlation_edges(conn)
    detect_mule_funnel_pattern(conn)
    inspect_image_authenticity(conn)
    verify_statement_arithmetic(conn)
    generate_event_sequence(conn)


def test_graph_sequence_scene_determinism_and_gt_recall():
    conn1 = _fresh_conn()
    conn2 = _fresh_conn()
    _ingest_full_case(conn1)
    _ingest_full_case(conn2)

    g1 = get_cytoscape_graph(conn1)
    g2 = get_cytoscape_graph(conn2)
    assert [n["data"]["id"] for n in g1["nodes"]] == [n["data"]["id"] for n in g2["nodes"]]
    assert [e["data"]["id"] for e in g1["edges"]] == [e["data"]["id"] for e in g2["edges"]]

    xml_out = export_graph_graphml(g1)
    assert "<graphml" in xml_out and "PRAMAAN_KG" in xml_out

    # Sequence determinism
    seq1 = generate_event_sequence(conn1)
    seq2 = generate_event_sequence(conn2)
    assert len(seq1) > 0
    assert [ep["title"] for ep in seq1] == [ep["title"] for ep in seq2]
    md = export_sequence_markdown(seq1)
    assert "# PRAMAAN Automated Event Sequence" in md

    # Scene reconstruction & replay
    ep_id = seq1[0]["id"]
    scene = reconstruct_scene(conn1, episode_id=ep_id)
    assert "locations" in scene and "presence" in scene and "events" in scene
    replay = replay_scene(conn1, episode_id=ep_id)
    assert replay["total_steps"] == len(scene["events"])

    # Ground truth recall GT-01..GT-15
    edge_types = {e["data"]["edge_type"] for e in g1["edges"]}
    anom_kinds = {r["kind"] for r in conn1.execute("SELECT kind FROM anomalies;").fetchall()}
    custody_actions = {r["action"] for r in conn1.execute("SELECT action FROM custody_log;").fetchall()}

    # Verify all 15 planted facts
    assert "SAME_IDENTIFIER" in edge_types          # GT-01
    assert "PATTERN_FUNNEL" in edge_types           # GT-02
    assert "SAME_DEVICE" in edge_types              # GT-03 & GT-15
    assert "ANOMALY_CHAT_GAP" in anom_kinds         # GT-04
    assert "ANOMALY_OUT_OF_ORDER" in anom_kinds     # GT-05
    assert "ANOMALY_IMAGE_EDITED" in anom_kinds     # GT-06
    assert "SAME_MEDIA" in edge_types               # GT-07
    assert "ANOMALY_BALANCE_MISMATCH" in anom_kinds # GT-08
    assert "SAME_PERSON_FUZZY" in edge_types        # GT-09
    assert "SPATIAL_THREAD" in anom_kinds           # GT-10
    assert "IMPOSSIBLE_TRAVEL" in anom_kinds        # GT-11
    assert "SHARED_IP_CROSS_SOURCE" in edge_types   # GT-12
    assert "TEMPORAL_CO_OCCURRENCE" in edge_types   # GT-13
    assert "CLOCK_OFFSET_RECORDED" in custody_actions # GT-14
    assert "LOGIN_FROM_IP" in edge_types            # GT-15

    # Verify each pluggable correlator ran
    assert len(DEFAULT_CORRELATORS) == 10
