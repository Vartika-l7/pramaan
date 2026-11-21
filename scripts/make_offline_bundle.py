"""Build an Air-Gapped Offline Install Bundle for PRAMAAN (Phase 4 Part A.3).

Creates a self-contained directory containing:
- `wheels/`: Python wheels downloaded from `requirements.txt`
- `frontend_dist/`: Built static Vite frontend with bundled fonts
- `app/`: Backend, verifier, scripts, tests, docs, synthetic dataset
- `install_offline.py`: Cross-platform offline installer (`pip install --no-index --find-links wheels`)
- `BUNDLE_SHA256SUMS.txt`: SHA-256 checksums for every file in the bundle
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def _find_npm() -> str:
    for cand in ("npm.cmd", "npm"):
        found = shutil.which(cand)
        if found:
            return found
    raise FileNotFoundError("npm executable not found in PATH")


def _ignore_runtime_artifacts(_dir: str, names: list[str]) -> list[str]:
    ignored = []
    for name in names:
        if name in {"__pycache__", ".pytest_cache", ".venv", "node_modules", ".git", "offline_bundle"}:
            ignored.append(name)
        elif name.endswith((".pyc", ".pyo", ".db", ".db-wal", ".db-shm")):
            ignored.append(name)
    return ignored


INSTALL_SCRIPT_TEMPLATE = '''"""Cross-platform offline installer for PRAMAAN air-gap bundle."""

from __future__ import annotations

import argparse
import hashlib
import subprocess
import sys
from pathlib import Path


def verify_checksums(bundle_dir: Path) -> None:
    sums_file = bundle_dir / "BUNDLE_SHA256SUMS.txt"
    if not sums_file.exists():
        raise FileNotFoundError("BUNDLE_SHA256SUMS.txt missing")
    lines = [ln.strip() for ln in sums_file.read_text(encoding="utf-8").splitlines() if ln.strip()]
    for ln in lines:
        expected, rel_path = ln.split("  ", 1)
        target = bundle_dir / rel_path
        if not target.exists():
            raise FileNotFoundError(f"Missing bundle file: {rel_path}")
        h = hashlib.sha256(target.read_bytes()).hexdigest()
        if h != expected:
            raise RuntimeError(f"Checksum mismatch for {rel_path}")
    print(f"[PASS] Verified {len(lines)} bundle files via SHA-256.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Install PRAMAAN strictly offline from local wheels.")
    parser.add_argument("--venv", default=".venv", help="Target virtual environment directory")
    parser.add_argument("--skip-checksum", action="store_true", help="Skip SHA-256 bundle check")
    args = parser.parse_args()

    bundle_dir = Path(__file__).resolve().parent
    if not args.skip_checksum:
        verify_checksums(bundle_dir)

    venv_dir = Path(args.venv)
    if not venv_dir.exists():
        print(f"Creating virtual environment at {venv_dir}...")
        subprocess.run([sys.executable, "-m", "venv", str(venv_dir)], check=True)

    py_bin = venv_dir / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")
    wheels_dir = bundle_dir / "wheels"
    req_file = bundle_dir / "app" / "requirements.txt"

    print("Installing Python packages strictly offline (--no-index --find-links)...")
    subprocess.run(
        [
            str(py_bin),
            "-m",
            "pip",
            "install",
            "--no-index",
            "--find-links",
            str(wheels_dir),
            "-r",
            str(req_file),
        ],
        check=True,
    )
    print("[PASS] Offline install complete.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
'''


def build_offline_bundle(output_dir: Path, skip_build: bool = False, skip_wheels: bool = False) -> Path:
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # 1. Build frontend and copy static dist
    if not skip_build:
        npm_bin = _find_npm()
        print("[1/4] Building static frontend...")
        subprocess.run([npm_bin, "run", "build"], cwd=str(ROOT / "frontend"), check=True)
    dist_src = ROOT / "frontend" / "dist"
    if not dist_src.exists():
        raise RuntimeError("frontend/dist not found; run without --skip-build")
    shutil.copytree(dist_src, output_dir / "frontend_dist")

    # 2. Download/build Python wheels
    wheels_dir = output_dir / "wheels"
    wheels_dir.mkdir(parents=True, exist_ok=True)
    if not skip_wheels:
        print("[2/4] Downloading Python wheels from requirements.txt...")
        subprocess.run(
            [sys.executable, "-m", "pip", "download", "-r", str(ROOT / "requirements.txt"), "-d", str(wheels_dir)],
            check=True,
        )
        # Convert any source archives (.tar.gz / .zip) into prebuilt wheels so air-gap install needs no build backend
        for sdist in list(wheels_dir.glob("*.tar.gz")) + list(wheels_dir.glob("*.zip")):
            subprocess.run(
                [sys.executable, "-m", "pip", "wheel", "--no-deps", "--wheel-dir", str(wheels_dir), str(sdist)],
                check=True,
            )
            sdist.unlink()
    else:
        print("[2/4] Skipping wheel download (--skip-wheels).")

    # 3. Copy application files
    print("[3/4] Copying backend, verifier, scripts, data, tests, docs, and static frontend...")
    app_dir = output_dir / "app"
    app_dir.mkdir(parents=True, exist_ok=True)
    for folder in ("backend", "verifier", "scripts", "data", "tests", "docs"):
        src = ROOT / folder
        if src.exists():
            shutil.copytree(src, app_dir / folder, ignore=_ignore_runtime_artifacts)
    # Include pre-built static frontend inside app/frontend/dist so uvicorn & check_offline.py work out of the box
    shutil.copytree(dist_src, app_dir / "frontend" / "dist")
    # Remove runtime evidence_store/packages/keys contents inside bundle app
    for clean_sub in (
        app_dir / "backend" / "evidence_store",
        app_dir / "backend" / "case_data",
        app_dir / "backend" / "keys",
    ):
        if clean_sub.exists():
            shutil.rmtree(clean_sub)
            clean_sub.mkdir(parents=True, exist_ok=True)
    for fname in ("requirements.txt", "README.md"):
        if (ROOT / fname).exists():
            shutil.copy2(ROOT / fname, app_dir / fname)

    (output_dir / "install_offline.py").write_text(INSTALL_SCRIPT_TEMPLATE, encoding="utf-8")

    # 4. Generate SHA-256 checksum manifest for the bundle
    print("[4/4] Generating BUNDLE_SHA256SUMS.txt...")
    checksum_lines = []
    file_count = 0
    for fpath in sorted(output_dir.rglob("*")):
        if fpath.is_file() and fpath.name not in ("BUNDLE_SHA256SUMS.txt", "bundle_manifest.json"):
            rel = fpath.relative_to(output_dir).as_posix()
            digest = _sha256_file(fpath)
            checksum_lines.append(f"{digest}  {rel}")
            file_count += 1

    (output_dir / "BUNDLE_SHA256SUMS.txt").write_text("\n".join(checksum_lines) + "\n", encoding="utf-8")
    manifest = {
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "python_version": sys.version.split()[0],
        "platform": sys.platform,
        "total_files": file_count,
        "wheel_count": len(list(wheels_dir.glob("*"))),
        "checksum_file": "BUNDLE_SHA256SUMS.txt",
    }
    (output_dir / "bundle_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[DONE] Air-gap bundle created at {output_dir} ({file_count} files, {manifest['wheel_count']} wheels).")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Create PRAMAAN air-gap offline install bundle.")
    parser.add_argument("--output", default=str(ROOT / "offline_bundle"), help="Output bundle directory")
    parser.add_argument("--skip-build", action="store_true", help="Reuse existing frontend/dist")
    parser.add_argument("--skip-wheels", action="store_true", help="Skip pip download")
    args = parser.parse_args()

    build_offline_bundle(Path(args.output), skip_build=args.skip_build, skip_wheels=args.skip_wheels)
    return 0


if __name__ == "__main__":
    sys.exit(main())
