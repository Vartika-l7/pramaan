"""Single-command PRAMAAN Verification & Test Pyramid Runner (Phase 4 Part B).

Usage:
    python scripts/run_all_checks.py

Runs:
1. Full pytest test suite with backend line-coverage tracking -> saves `docs/coverage.txt`.
2. Offline end-to-end verification (`scripts/check_offline.py`).
3. Pipeline determinism check (two independent runs).
4. Standalone verifier.py vs backend cross-check (intact & tampered).
5. Ground-truth recall check (GT-01..GT-15).
6. Investigator Assistant evaluation (`scripts/eval_assistant.py`) -> saves `assistant_eval_results.json`.
Prints a concise one-page summary and exits non-zero if any check fails.
"""

from __future__ import annotations

import dis
import json
import sqlite3
import subprocess
import sys
import tempfile
import trace
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pytest
from backend.app.db import SCHEMA_SQL
from backend.app.ingest.service import ingest_file, verify_case_integrity
from backend.app.ingest.registry import parse_and_store_evidence
from backend.app.extract.resolve import run_entity_extraction
from backend.app.correlate.edges import generate_correlation_edges
from backend.app.correlate.patterns import detect_mule_funnel_pattern
from backend.app.correlate.graph import get_cytoscape_graph
from backend.app.timeline.anomalies import detect_timeline_anomalies, detect_spatial_movement
from backend.app.authenticity.exif import inspect_image_authenticity
from backend.app.authenticity.statement_checks import verify_statement_arithmetic
from backend.app.sequence.generator import generate_event_sequence
from backend.app.scene.reconstructor import reconstruct_scene
from backend.app.ai.provider import DeterministicProvider
from backend.app.verify.claim_verifier import verify_claims
from backend.app.report.package import assemble_case_package
from scripts.eval_assistant import run_eval


def _executable_lines(py_path: Path) -> set[int]:
    """Return executable statement line numbers in a Python source file via bytecode line table."""
    src = py_path.read_text(encoding="utf-8")
    code = compile(src, str(py_path), "exec")
    lines: set[int] = set()

    def walk(c):
        for _, line in dis.findlinestarts(c):
            if line and line > 0:
                lines.add(line)
        for const in c.co_consts:
            if isinstance(const, type(c)):
                walk(const)

    walk(code)
    return lines


def run_pytest_with_coverage() -> tuple[int, str, str]:
    """Run full pytest suite while measuring backend/app Python line coverage."""
    tracer = trace.Trace(count=1, trace=0)
    exit_code = tracer.runfunc(pytest.main, ["-q", str(ROOT / "tests")])
    results = tracer.results()

    executed_by_file: dict[str, set[int]] = {}
    for (filename, lineno), count in results.counts.items():
        if count > 0:
            resolved = str(Path(filename).resolve())
            executed_by_file.setdefault(resolved, set()).add(lineno)

    backend_app_dir = (ROOT / "backend" / "app").resolve()
    py_files = sorted(backend_app_dir.rglob("*.py"))

    rows = []
    total_stmts = 0
    total_miss = 0
    for fpath in py_files:
        exec_lines = _executable_lines(fpath)
        if not exec_lines:
            continue
        hit_lines = executed_by_file.get(str(fpath), set()) & exec_lines
        stmts = len(exec_lines)
        miss = stmts - len(hit_lines)
        pct = (len(hit_lines) / stmts) * 100.0
        total_stmts += stmts
        total_miss += miss
        rel = fpath.relative_to(ROOT).as_posix()
        rows.append((rel, stmts, miss, pct))

    total_cov = ((total_stmts - total_miss) / max(1, total_stmts)) * 100.0
    lines_out = [
        "PRAMAAN Backend Code Coverage Report (measured via Python stdlib trace)",
        "=" * 78,
        f"{'Module':<50} {'Stmts':>7} {'Miss':>7} {'Cover':>9}",
        "-" * 78,
    ]
    for rel, stmts, miss, pct in rows:
        lines_out.append(f"{rel:<50} {stmts:>7} {miss:>7} {pct:>8.1f}%")
    lines_out.append("-" * 78)
    lines_out.append(f"{'TOTAL':<50} {total_stmts:>7} {total_miss:>7} {total_cov:>8.1f}%")
    cov_text = "\n".join(lines_out) + "\n"

    cov_path = ROOT / "docs" / "coverage.txt"
    cov_path.write_text(cov_text, encoding="utf-8")
    cov_summary = f"{total_cov:.1f}% ({total_stmts - total_miss}/{total_stmts} statements)"
    return int(exit_code), cov_summary, cov_text


def _run_pipeline_snapshot(tmp_dir: Path) -> tuple[dict, sqlite3.Connection, Path]:
    import backend.app.ingest.service as ingest_svc
    import backend.app.authenticity.exif as exif_mod
    import backend.app.authenticity.ela as ela_mod

    orig_store = ingest_svc.EVIDENCE_STORE_DIR
    orig_ela = ela_mod.ELA_DIR
    ingest_svc.EVIDENCE_STORE_DIR = tmp_dir / "evidence_store"
    ela_mod.ELA_DIR = tmp_dir / "ela"
    ela_mod.ELA_DIR.mkdir(parents=True, exist_ok=True)
    exif_mod.ELA_DIR = ela_mod.ELA_DIR

    try:
        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.executescript(SCHEMA_SQL)

        data_dir = ROOT / "data" / "case_alpha"
        skip = {"ground_truth.json", "benchmark_results.json", "assistant_eval_results.json", "tower_registry.csv"}
        for f in sorted(p for p in data_dir.iterdir() if p.is_file() and p.name not in skip):
            with open(f, "rb") as fh:
                res = ingest_file(conn, fh, f.name, actor="CHECK_RUNNER")
            parse_and_store_evidence(conn, res["id"], actor="CHECK_RUNNER")

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
        anoms = [dict(r) for r in conn.execute("SELECT id, kind, severity, description FROM anomalies ORDER BY id ASC;").fetchall()]
        edges = [dict(r) for r in conn.execute("SELECT id, src, dst, edge_type, reason_text FROM edges ORDER BY id ASC;").fetchall()]
        drafted = prov.draft_claims({"events": events, "anomalies": anoms, "edges": edges})
        ver = verify_claims(conn, drafted)

        pkg_dir = tmp_dir / "pkg"
        assemble_case_package(conn, case_id="PRM-2026-0042", target_package_dir=pkg_dir)

        snap = {
            "evidence": [dict(r) for r in conn.execute("SELECT id, exhibit_id, sha256 FROM evidence ORDER BY exhibit_id;").fetchall()],
            "event_ids": [r["id"] for r in conn.execute("SELECT id FROM events ORDER BY ts_utc ASC, id ASC;").fetchall()],
            "edges": [dict(r) for r in conn.execute("SELECT id, src, dst, edge_type, basis, strength FROM edges ORDER BY id;").fetchall()],
            "anomalies": [dict(r) for r in conn.execute("SELECT id, kind, severity, description FROM anomalies ORDER BY id;").fetchall()],
            "claims": ver["verified_claims"],
            "episodes": episodes,
            "scene": scene,
        }
        return snap, conn, pkg_dir
    finally:
        ingest_svc.EVIDENCE_STORE_DIR = orig_store
        ela_mod.ELA_DIR = orig_ela
        exif_mod.ELA_DIR = orig_ela


def main() -> int:
    print("=" * 72)
    print("PRAMAAN FULL VERIFICATION & TEST PYRAMID")
    print("=" * 72)

    # 1. Pytest + Coverage
    print("\n[1/6] Running pytest test pyramid & measuring backend coverage...")
    pytest_rc, cov_summary, _ = run_pytest_with_coverage()
    pytest_ok = pytest_rc == 0

    # 2. Offline Check
    print("\n[2/6] Running offline end-to-end verification (scripts/check_offline.py)...")
    off_proc = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_offline.py")],
        capture_output=True,
        text=True,
    )
    offline_ok = off_proc.returncode == 0
    if not offline_ok:
        print(off_proc.stdout)
        print(off_proc.stderr)

    # 3, 4, 5. Determinism + Verifier Cross-check + GT-01..GT-15 Recall
    print("\n[3/6] Verifying pipeline determinism, verifier cross-check, and GT-01..GT-15 recall...")
    with tempfile.TemporaryDirectory(prefix="pramaan_checks_") as tmp:
        tmp_path = Path(tmp)
        snap1, conn1, pkg1 = _run_pipeline_snapshot(tmp_path / "run1")
        snap2, conn2, _ = _run_pipeline_snapshot(tmp_path / "run2")

        determinism_ok = snap1 == snap2

        # Cross-check intact
        be_ok = verify_case_integrity(conn1)["intact"] is True
        st_ok = subprocess.run(
            [sys.executable, str(ROOT / "verifier" / "verifier.py"), "--package", str(pkg1)],
            capture_output=True,
            text=True,
        ).returncode == 0

        # Cross-check tampered
        first_ev = sorted((pkg1 / "evidence").iterdir())[0]
        first_ev.chmod(0o644)
        first_ev.write_bytes(b"TAMPERED")
        st_tamper_fail = subprocess.run(
            [sys.executable, str(ROOT / "verifier" / "verifier.py"), "--package", str(pkg1)],
            capture_output=True,
            text=True,
        ).returncode != 0
        conn1.execute("UPDATE manifests SET merkle_root = '0000' || substr(merkle_root, 5);")
        conn1.commit()
        be_tamper_fail = verify_case_integrity(conn1)["intact"] is False
        crosscheck_ok = be_ok and st_ok and st_tamper_fail and be_tamper_fail

        # GT-01..GT-15 recall
        g = get_cytoscape_graph(conn1)
        edge_types = {e["data"]["edge_type"] for e in g["edges"]}
        anom_kinds = {r["kind"] for r in conn1.execute("SELECT kind FROM anomalies;").fetchall()}
        custody_actions = {r["action"] for r in conn1.execute("SELECT action FROM custody_log;").fetchall()}
        gt_checks = {
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
        gt_found = sum(1 for v in gt_checks.values() if v)
        gt_missing = [k for k, v in gt_checks.items() if not v]

        conn1.close()
        conn2.close()

    # 6. Assistant Evaluation
    print("\n[4/6] Running Assistant evaluation on synthetic dataset...")
    eval_res = run_eval()
    (ROOT / "data" / "case_alpha" / "assistant_eval_results.json").write_text(
        json.dumps(eval_res, indent=2) + "\n", encoding="utf-8"
    )

    # One-page summary
    print("\n" + "=" * 72)
    print("PRAMAAN ONE-PAGE VERIFICATION SUMMARY (SYNTHETIC DATASET)")
    print("=" * 72)
    print(f"1. Test Pyramid (pytest)       : {'PASS' if pytest_ok else 'FAIL'} (backend coverage: {cov_summary})")
    print(f"2. Offline Check               : {'PASS (0 outbound connections)' if offline_ok else 'FAIL'}")
    print(f"3. Pipeline Determinism        : {'PASS (identical IDs, hashes, edges, anomalies, claims, episodes, scenes)' if determinism_ok else 'FAIL'}")
    print(f"4. Verifier Cross-Check        : {'PASS (intact & tampered agreed)' if crosscheck_ok else 'FAIL'}")
    print(f"5. Ground-Truth Recall         : {gt_found}/15 ({gt_found / 15 * 100:.1f}%)" + (f" [Missing: {gt_missing}]" if gt_missing else " [All GT-01..GT-15 detected]"))
    print(
        f"6. Assistant Eval (synthetic)  : citation_precision={eval_res['citation_precision']}, "
        f"keyword_recall={eval_res['keyword_recall']}, "
        f"unanswerable_refusal_rate={eval_res['unanswerable_refusal_rate']}, "
        f"verifier_removed_share={eval_res['verifier_removed_share']}"
    )
    print(f"7. Coverage Report Saved       : docs/coverage.txt")
    print("=" * 72)

    all_ok = pytest_ok and offline_ok and determinism_ok and crosscheck_ok and (gt_found == 15)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
