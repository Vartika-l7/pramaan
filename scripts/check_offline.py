"""Offline End-to-End Verification Script for PRAMAAN (Phase 4 Part A).

Verifies:
1. Frontend builds cleanly offline (`npm run build`).
2. Zero external URL fetches, CDN links, or non-local endpoints exist in source or built assets
   (excluding standard XML namespaces and static license/doc strings inside bundled npm libs).
3. All @fontsource fonts and UI assets are bundled locally in `frontend/dist/assets`.
4. Full forensic pipeline (ingest -> parse -> extract -> correlate -> spatial -> sequence ->
   scene -> AI draft/verify -> assistant -> leads -> challenger -> package -> verifier.py)
   runs cleanly with the Network Guard enabled and records 0 outbound socket connections.
"""

from __future__ import annotations

import os
import re
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.app.network_guard import (
    install_network_guard,
    uninstall_network_guard,
    reset_guard_stats,
    get_outbound_count,
    get_blocked_attempts,
)
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
from backend.app.verify.challenger import run_challenger_analysis
from backend.app.assistant.engine import ask_assistant
from backend.app.assistant.tools import suggest_next_leads
from backend.app.report.package import assemble_case_package

# Standard XML namespaces and static license/doc warning strings inside bundled third-party JS libs
ALLOWED_DIST_URL_PREFIXES = (
    "http://www.w3.org/",
    "http://www.apache.org/licenses/",
    "http://opensource.org/licenses/",
    "https://tldrlegal.com/license/",
    "https://reactjs.org/docs/error-decoder.html",
    "http://momentjs.com/guides/",
    "https://github.com/uuidjs/uuid",
    "https://github.com/visjs",
    "https://visjs.github.io/vis-timeline",
    "http://visjs.org/",
    "http://almende.com",
    "http://engelschall.com",
    "http://naver.github.io/egjs",
    "https://github.com/gre/bezier-easing",
    "https://github.com/jquery/jquery",
    "https://jquery.org/license/",
    "https://github.com/zloirock/core-js",
    "http://en.wikipedia.org/wiki/MIT_License",
)

ALLOWED_BACKEND_URL_PREFIXES = (
    "http://localhost",
    "http://127.0.0.1",
    "http://graphml.graphdrawing.org/",
    "http://www.w3.org/",
    "http://",
    "https://",
)


def _find_npm() -> str:
    for cand in ("npm.cmd", "npm"):
        found = shutil.which(cand)
        if found:
            return found
    raise FileNotFoundError("npm executable not found in PATH")


def build_frontend() -> None:
    frontend_dir = ROOT / "frontend"
    npm_bin = _find_npm()
    print("[1/4] Building frontend production bundle...")
    proc = subprocess.run(
        [npm_bin, "run", "build"],
        cwd=str(frontend_dir),
        capture_output=True,
        text=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"Frontend build failed:\n{proc.stdout}\n{proc.stderr}")
    print("  [PASS] Frontend built cleanly.")


def scan_urls_and_assets() -> None:
    print("[2/4] Scanning source and build output for external URLs and runtime fetches...")
    violations = []

    # Check frontend/index.html and frontend/src (strict: zero external URLs)
    for target in [ROOT / "frontend" / "index.html", *(ROOT / "frontend" / "src").rglob("*")]:
        if not target.is_file() or target.suffix not in (".html", ".ts", ".tsx", ".css", ".js"):
            continue
        text = target.read_text("utf-8", errors="ignore")
        for url in re.findall(r'https?://[^\s"\'<>)]+', text):
            violations.append(f"Source URL in {target.relative_to(ROOT)}: {url}")

    # Check frontend/dist for runtime fetch/CDN patterns and unapproved URLs
    dist_dir = ROOT / "frontend" / "dist"
    if not dist_dir.exists():
        raise RuntimeError("frontend/dist does not exist after build")

    runtime_fetch_pattern = re.compile(
        r'(?:fetch\s*\(\s*["\']https?://|src\s*=\s*["\']https?://|href\s*=\s*["\']https?://|@import\s+url\(\s*["\']?https?://|new\s+WebSocket\s*\(\s*["\']wss?://)',
        re.IGNORECASE,
    )
    for f in dist_dir.rglob("*"):
        if not f.is_file() or f.suffix not in (".html", ".js", ".css"):
            continue
        text = f.read_text("utf-8", errors="ignore")
        if runtime_fetch_pattern.search(text):
            violations.append(f"Runtime external fetch/CDN tag in {f.relative_to(ROOT)}")
        for url in re.findall(r'https?://[^\s"\'<>\\)]+', text):
            if not any(url.startswith(pref) for pref in ALLOWED_DIST_URL_PREFIXES):
                violations.append(f"Unexpected URL in dist ({f.relative_to(ROOT)}): {url}")

    # Check backend/app for unexpected external URLs
    for f in (ROOT / "backend" / "app").rglob("*.py"):
        text = f.read_text("utf-8", errors="ignore")
        for url in re.findall(r'https?://[^\s"\'<>),]+', text):
            if url in ("http://", "https://"):
                continue
            if not any(url.startswith(pref) for pref in ALLOWED_BACKEND_URL_PREFIXES[:-2]):
                violations.append(f"External URL in backend ({f.relative_to(ROOT)}): {url}")

    if violations:
        raise RuntimeError("Offline URL audit failed:\n  - " + "\n  - ".join(violations))
    print("  [PASS] Zero external runtime fetches or CDN URLs detected.")

    print("[3/4] Verifying bundled fonts and static assets in frontend/dist...")
    assets_dir = dist_dir / "assets"
    if not assets_dir.exists():
        raise RuntimeError("frontend/dist/assets missing")
    asset_names = [p.name for p in assets_dir.iterdir() if p.is_file()]
    required_fonts = ["source-serif-4", "ibm-plex-sans", "ibm-plex-mono"]
    for font_prefix in required_fonts:
        if not any(name.startswith(font_prefix) and name.endswith(".woff2") for name in asset_names):
            raise RuntimeError(f"Bundled woff2 font missing for {font_prefix}")
    if not (dist_dir / "index.html").exists():
        raise RuntimeError("frontend/dist/index.html missing")
    print(f"  [PASS] Verified {len(asset_names)} bundled assets including all 3 local font families.")


def run_guarded_pipeline() -> None:
    print("[4/4] Running full forensic demo pipeline under Network Guard...")
    os.environ["OFFLINE"] = "1"
    reset_guard_stats()
    install_network_guard()

    data_dir = ROOT / "data" / "case_alpha"
    skip_files = {"ground_truth.json", "benchmark_results.json", "assistant_eval_results.json", "tower_registry.csv"}

    with tempfile.TemporaryDirectory(prefix="pramaan_offline_check_") as tmpdir:
        tmp_path = Path(tmpdir)
        import backend.app.ingest.service as ingest_svc
        import backend.app.authenticity.exif as exif_mod
        import backend.app.authenticity.ela as ela_mod
        orig_store = ingest_svc.EVIDENCE_STORE_DIR
        orig_ela = ela_mod.ELA_DIR
        ingest_svc.EVIDENCE_STORE_DIR = tmp_path / "evidence_store"
        ela_mod.ELA_DIR = tmp_path / "ela_heatmaps"
        ela_mod.ELA_DIR.mkdir(parents=True, exist_ok=True)
        exif_mod.ELA_DIR = ela_mod.ELA_DIR
        try:
            conn = sqlite3.connect(":memory:")
            conn.row_factory = sqlite3.Row
            conn.executescript(SCHEMA_SQL)

            files = sorted(f for f in data_dir.iterdir() if f.is_file() and f.name not in skip_files)
            for f in files:
                with open(f, "rb") as fh:
                    res = ingest_file(conn, fh, f.name, actor="OFFLINE_CHECK")
                parse_and_store_evidence(conn, res["id"], actor="OFFLINE_CHECK")

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
            events = [dict(r) for r in conn.execute("SELECT id, ts_utc, kind, text, amount, actor, counterparty FROM events LIMIT 50;").fetchall()]
            anoms = [dict(r) for r in conn.execute("SELECT id, kind, severity, description FROM anomalies;").fetchall()]
            edges = [dict(r) for r in conn.execute("SELECT id, src, dst, edge_type, reason_text FROM edges;").fetchall()]
            drafted = prov.draft_claims({"events": events, "anomalies": anoms, "edges": edges})
            verify_claims(conn, drafted)

            ask_assistant(conn, "Who is connected to vikram.alpha@okaxis?", session_id="offline_check")
            suggest_next_leads(conn)
            run_challenger_analysis(conn)

            pkg_dir = tmp_path / "pkg_PRM-2026-0042"
            assemble_case_package(conn, case_id="PRM-2026-0042", target_package_dir=pkg_dir)
            conn.close()
        finally:
            ingest_svc.EVIDENCE_STORE_DIR = orig_store
            ela_mod.ELA_DIR = orig_ela
            exif_mod.ELA_DIR = orig_ela

        proc = subprocess.run(
            [sys.executable, str(ROOT / "verifier" / "verifier.py"), "--package", str(pkg_dir)],
            capture_output=True,
            text=True,
        )
        if proc.returncode != 0:
            raise RuntimeError(f"Standalone verifier failed during offline check:\n{proc.stdout}\n{proc.stderr}")

    outbound = get_outbound_count()
    blocked = get_blocked_attempts()
    if outbound != 0 or blocked:
        raise RuntimeError(f"Network Guard detected {outbound} outbound attempts: {blocked}")

    print(
        f"  [PASS] Full pipeline + verifier completed offline "
        f"(episodes={len(episodes)}, scene_events={len(scene['events'])}, outbound_connections={outbound})."
    )


def main() -> int:
    try:
        build_frontend()
        scan_urls_and_assets()
        run_guarded_pipeline()
        print("\nOFFLINE CHECK PASSED: 0 outbound connections, all fonts/assets local.")
        return 0
    except Exception as exc:
        print(f"\n[FAIL] OFFLINE CHECK FAILED: {exc}", file=sys.stderr)
        return 1
    finally:
        uninstall_network_guard()


if __name__ == "__main__":
    sys.exit(main())
