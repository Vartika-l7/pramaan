"""Single-command PRAMAAN Verification & Test Pyramid Runner.

Usage:
    python scripts/run_all_checks.py --fast   # Fast verification (target < 2 min)
    python scripts/run_all_checks.py --full   # Full suite (+ --run-slow + coverage + offline build)

Always prints progress per stage with elapsed time, enforces a per-stage and global
timeout, and ALWAYS prints a final summary table even if a stage fails or times out.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

# Ensure offline / fast-fail environment for all verification stages
os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
os.environ.setdefault("PRAMAAN_FAKE_LLM", "1")


@dataclass
class StageResult:
    name: str
    status: str  # PASS | FAIL | TIMEOUT | SKIPPED
    elapsed_s: float
    detail: str = ""
    first_failure: str = ""


def _extract_first_failure(output: str) -> str:
    """Pull the first FAILED / ERROR test node id from pytest output if present."""
    for pattern in (
        r"FAILED\s+(\S+)",
        r"ERROR\s+(\S+)",
        r"(tests/\S+::\S+)\s+(?:FAILED|ERROR)",
    ):
        m = re.search(pattern, output)
        if m:
            return m.group(1)
    for line in output.splitlines():
        if "Timeout" in line or "FAIL" in line or "Error" in line:
            return line.strip()[:120]
    return ""


def _run_subprocess_stage(
    name: str,
    cmd: list[str],
    timeout_s: int,
    env: Optional[dict[str, str]] = None,
    detail_extractor: Optional[Callable[[str], str]] = None,
) -> StageResult:
    print(f"\n[{name}] Starting (timeout={timeout_s}s)...", flush=True)
    t0 = time.monotonic()
    run_env = {**os.environ, **(env or {})}
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(ROOT),
            env=run_env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        elapsed = time.monotonic() - t0
        combined = (proc.stdout or "") + "\n" + (proc.stderr or "")
        detail = detail_extractor(combined) if detail_extractor else ""
        if proc.returncode == 0:
            print(f"[{name}] PASS in {elapsed:.2f}s" + (f" — {detail}" if detail else ""), flush=True)
            return StageResult(name=name, status="PASS", elapsed_s=elapsed, detail=detail)
        first_fail = _extract_first_failure(combined)
        print(f"[{name}] FAIL in {elapsed:.2f}s (exit={proc.returncode})", flush=True)
        if first_fail:
            print(f"  First failure: {first_fail}", flush=True)
        return StageResult(
            name=name,
            status="FAIL",
            elapsed_s=elapsed,
            detail=detail or f"exit code {proc.returncode}",
            first_failure=first_fail,
        )
    except subprocess.TimeoutExpired as exc:
        elapsed = time.monotonic() - t0
        out = ""
        if exc.stdout:
            out += exc.stdout.decode("utf-8", errors="ignore") if isinstance(exc.stdout, bytes) else exc.stdout
        if exc.stderr:
            out += "\n" + (exc.stderr.decode("utf-8", errors="ignore") if isinstance(exc.stderr, bytes) else exc.stderr)
        first_fail = _extract_first_failure(out) or f"timed out after {timeout_s}s"
        print(f"[{name}] TIMEOUT after {elapsed:.2f}s — {first_fail}", flush=True)
        return StageResult(
            name=name,
            status="TIMEOUT",
            elapsed_s=elapsed,
            detail=f"exceeded {timeout_s}s",
            first_failure=first_fail,
        )


def _run_pipeline_snapshot(tmp_dir: Path) -> tuple[dict, sqlite3.Connection, Path]:
    from backend.app.db import SCHEMA_SQL
    from backend.app.ingest.service import ingest_file
    from backend.app.ingest.registry import parse_and_store_evidence
    from backend.app.extract.resolve import run_entity_extraction
    from backend.app.correlate.edges import generate_correlation_edges
    from backend.app.correlate.patterns import detect_mule_funnel_pattern
    from backend.app.timeline.anomalies import detect_timeline_anomalies, detect_spatial_movement
    from backend.app.authenticity.exif import inspect_image_authenticity
    from backend.app.authenticity.statement_checks import verify_statement_arithmetic
    from backend.app.sequence.generator import generate_event_sequence
    from backend.app.scene.reconstructor import reconstruct_scene
    from backend.app.ai.provider import DeterministicProvider
    from backend.app.verify.claim_verifier import verify_claims
    from backend.app.report.package import assemble_case_package
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
            "anomalies": [dict(r) for r in conn.execute("SELECT id, kind, severity, description FROM anomalies ORDER BY id ASC;").fetchall()],
            "claims": ver["verified_claims"],
            "episodes": episodes,
            "scene": scene,
        }
        return snap, conn, pkg_dir
    finally:
        ingest_svc.EVIDENCE_STORE_DIR = orig_store
        ela_mod.ELA_DIR = orig_ela
        exif_mod.ELA_DIR = orig_ela


def _stage_determinism_verifier_gt() -> list[StageResult]:
    from backend.app.ingest.service import verify_case_integrity
    from backend.app.correlate.graph import get_cytoscape_graph

    print("\n[Determinism + Verifier + GT-01..GT-15] Starting...", flush=True)
    t0 = time.monotonic()
    try:
        with tempfile.TemporaryDirectory(prefix="pramaan_checks_") as tmp:
            tmp_path = Path(tmp)
            snap1, conn1, pkg1 = _run_pipeline_snapshot(tmp_path / "run1")
            snap2, conn2, _ = _run_pipeline_snapshot(tmp_path / "run2")
            try:
                determinism_ok = snap1 == snap2

                be_ok = verify_case_integrity(conn1)["intact"] is True
                st_ok = subprocess.run(
                    [sys.executable, str(ROOT / "verifier" / "verifier.py"), "--package", str(pkg1)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).returncode == 0

                first_ev = sorted((pkg1 / "evidence").iterdir())[0]
                first_ev.chmod(0o644)
                first_ev.write_bytes(b"TAMPERED")
                st_tamper_fail = subprocess.run(
                    [sys.executable, str(ROOT / "verifier" / "verifier.py"), "--package", str(pkg1)],
                    capture_output=True,
                    text=True,
                    timeout=30,
                ).returncode != 0
                conn1.execute("UPDATE manifests SET merkle_root = '0000' || substr(merkle_root, 5);")
                conn1.commit()
                be_tamper_fail = verify_case_integrity(conn1)["intact"] is False
                crosscheck_ok = be_ok and st_ok and st_tamper_fail and be_tamper_fail

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
            finally:
                conn1.close()
                conn2.close()

        elapsed = time.monotonic() - t0
        print(
            f"[Determinism + Verifier + GT-01..GT-15] DONE in {elapsed:.2f}s "
            f"(determinism={'PASS' if determinism_ok else 'FAIL'}, "
            f"verifier={'PASS' if crosscheck_ok else 'FAIL'}, GT={gt_found}/15)",
            flush=True,
        )
        return [
            StageResult(
                name="Pipeline Determinism",
                status="PASS" if determinism_ok else "FAIL",
                elapsed_s=elapsed,
                detail="2 independent runs identical" if determinism_ok else "snapshot mismatch",
                first_failure="" if determinism_ok else "determinism_mismatch",
            ),
            StageResult(
                name="Verifier Cross-Check",
                status="PASS" if crosscheck_ok else "FAIL",
                elapsed_s=0.0,
                detail="intact & tampered agreed" if crosscheck_ok else "backend/verifier disagreement",
                first_failure="" if crosscheck_ok else "verifier_crosscheck",
            ),
            StageResult(
                name="Ground-Truth Recall (GT-01..GT-15)",
                status="PASS" if gt_found == 15 else "FAIL",
                elapsed_s=0.0,
                detail=f"{gt_found}/15 ({gt_found / 15 * 100:.1f}%)" + (f" missing={gt_missing}" if gt_missing else ""),
                first_failure="" if gt_found == 15 else f"missing:{','.join(gt_missing)}",
            ),
        ]
    except Exception as exc:
        elapsed = time.monotonic() - t0
        print(f"[Determinism + Verifier + GT-01..GT-15] FAIL in {elapsed:.2f}s: {exc}", flush=True)
        return [
            StageResult(
                name="Determinism + Verifier + GT",
                status="FAIL",
                elapsed_s=elapsed,
                detail=str(exc),
                first_failure=str(exc)[:120],
            )
        ]


def _stage_assistant_eval() -> StageResult:
    from scripts.eval_assistant import run_eval

    print("\n[Assistant Eval (synthetic)] Starting...", flush=True)
    t0 = time.monotonic()
    try:
        res = run_eval()
        elapsed = time.monotonic() - t0
        (ROOT / "data" / "case_alpha" / "assistant_eval_results.json").write_text(
            json.dumps(res, indent=2) + "\n", encoding="utf-8"
        )
        detail = (
            f"citation_precision={res['citation_precision']}, "
            f"keyword_recall={res['keyword_recall']}, "
            f"refusal={res['unanswerable_refusal_rate']}"
        )
        print(f"[Assistant Eval (synthetic)] PASS in {elapsed:.2f}s — {detail}", flush=True)
        return StageResult(name="Assistant Eval (synthetic)", status="PASS", elapsed_s=elapsed, detail=detail)
    except Exception as exc:
        elapsed = time.monotonic() - t0
        print(f"[Assistant Eval (synthetic)] FAIL in {elapsed:.2f}s: {exc}", flush=True)
        return StageResult(
            name="Assistant Eval (synthetic)",
            status="FAIL",
            elapsed_s=elapsed,
            detail=str(exc),
            first_failure=str(exc)[:120],
        )


def _pytest_summary_line(output: str) -> str:
    for line in reversed(output.splitlines()):
        s = line.strip().strip("=").strip()
        if any(k in s for k in ("passed", "failed", "skipped", "error")):
            return s
    return ""


def _print_summary(mode: str, results: list[StageResult], total_s: float) -> None:
    print("\n" + "=" * 86)
    print(f"PRAMAAN VERIFICATION SUMMARY  |  mode=--{mode}  |  total={total_s:.2f}s")
    print("=" * 86)
    print(f"{'Stage':<36} {'Status':<9} {'Time':>8}  {'Detail / First Failure'}")
    print("-" * 86)
    for r in results:
        info = r.detail
        if r.first_failure:
            info = f"{info} | first_fail={r.first_failure}" if info else f"first_fail={r.first_failure}"
        print(f"{r.name:<36} {r.status:<9} {r.elapsed_s:>7.2f}s  {info}")
    print("=" * 86)


def main() -> int:
    parser = argparse.ArgumentParser(description="PRAMAAN Verification & Test Runner")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--fast", action="store_true", help="Fast verification (excludes slow/llm; target < 2 min)")
    group.add_argument("--full", action="store_true", help="Full verification (includes --run-slow, coverage, offline build)")
    parser.add_argument("--global-timeout", type=int, default=None, help="Global timeout in seconds")
    args = parser.parse_args()

    mode = "full" if args.full else "fast"
    global_timeout = args.global_timeout or (180 if mode == "fast" else 600)
    t_start = time.monotonic()
    results: list[StageResult] = []

    print("=" * 86)
    print(f"PRAMAAN VERIFICATION RUNNER  |  mode=--{mode}  |  global_timeout={global_timeout}s")
    print("=" * 86)

    def _remaining() -> int:
        return max(10, int(global_timeout - (time.monotonic() - t_start)))

    try:
        # Stage 1: Pytest
        if mode == "fast":
            pytest_cmd = [
                sys.executable, "-m", "pytest", "tests/",
                "--timeout=60", "-q",
            ]
        else:
            pytest_cmd = [
                sys.executable, "-m", "pytest", "tests/",
                "--run-slow", "--timeout=60", "-q",
                "--cov=backend/app", "--cov-report=term-missing",
            ]

        pytest_res = _run_subprocess_stage(
            name=f"Pytest ({mode})",
            cmd=pytest_cmd,
            timeout_s=min(120 if mode == "fast" else 300, _remaining()),
            detail_extractor=_pytest_summary_line,
        )
        results.append(pytest_res)

        # Stage 2: Offline Check (full mode runs build + audit + guarded pipeline)
        if mode == "full":
            offline_res = _run_subprocess_stage(
                name="Offline End-to-End Check",
                cmd=[sys.executable, str(ROOT / "scripts" / "check_offline.py")],
                timeout_s=min(180, _remaining()),
                env={"OFFLINE": "1"},
            )
            results.append(offline_res)
        else:
            results.append(StageResult(
                name="Offline End-to-End Check",
                status="SKIPPED",
                elapsed_s=0.0,
                detail="skipped in --fast (covered by test_phase4_offline_and_explain; run --full for npm build)",
            ))

        # Stage 3: Determinism + Verifier Cross-Check + GT-01..GT-15 Recall
        if time.monotonic() - t_start < global_timeout:
            results.extend(_stage_determinism_verifier_gt())
        else:
            results.append(StageResult("Determinism + Verifier + GT", "TIMEOUT", 0.0, "global timeout reached"))

        # Stage 4: Assistant Eval
        if time.monotonic() - t_start < global_timeout:
            results.append(_stage_assistant_eval())
        else:
            results.append(StageResult("Assistant Eval (synthetic)", "TIMEOUT", 0.0, "global timeout reached"))

    finally:
        total_s = time.monotonic() - t_start
        _print_summary(mode, results, total_s)

    all_ok = all(r.status in ("PASS", "SKIPPED") for r in results)
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
