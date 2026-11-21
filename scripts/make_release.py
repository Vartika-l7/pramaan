"""Cross-platform release ZIP builder for PRAMAAN (Phase 5).

Packages source code, documentation, synthetic dataset (`data/case_alpha`),
and the offline bundle SHA-256 checksum manifest (`BUNDLE_SHA256SUMS.txt`)
into `release/pramaan-v1.0-release.zip` + `.sha256`.
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            h.update(chunk)
    return h.hexdigest()


def build_release_zip(version: str = "v1.0", bundle_dir: Path | None = None) -> Path:
    release_dir = ROOT / "release"
    release_dir.mkdir(parents=True, exist_ok=True)
    zip_path = release_dir / f"pramaan-{version}-release.zip"
    if zip_path.exists():
        zip_path.unlink()

    exclude_dirs = {
        ".git",
        ".venv",
        "venv",
        "env",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        "backend/keys",
        "backend/case_data",
        "backend/evidence_store",
        "offline_bundle",
        "release",
    }

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for fpath in sorted(ROOT.rglob("*")):
            if not fpath.is_file():
                continue
            rel = fpath.relative_to(ROOT).as_posix()
            if any(
                rel == ex or rel.startswith(ex + "/") or f"/{ex}/" in f"/{rel}"
                for ex in exclude_dirs
            ):
                continue
            if rel.endswith((".pyc", ".pyo", ".db", ".db-wal", ".db-shm", ".DS_Store")):
                continue
            zf.write(fpath, f"pramaan-{version}/{rel}")

        if bundle_dir and (bundle_dir / "BUNDLE_SHA256SUMS.txt").exists():
            zf.write(
                bundle_dir / "BUNDLE_SHA256SUMS.txt",
                f"pramaan-{version}/BUNDLE_SHA256SUMS.txt",
            )
            if (bundle_dir / "bundle_manifest.json").exists():
                zf.write(
                    bundle_dir / "bundle_manifest.json",
                    f"pramaan-{version}/bundle_manifest.json",
                )

    digest = sha256_file(zip_path)
    (release_dir / f"pramaan-{version}-release.zip.sha256").write_text(
        f"{digest}  {zip_path.name}\n", encoding="utf-8"
    )
    print(f"[DONE] Created {zip_path} ({zip_path.stat().st_size} bytes, sha256={digest})")
    return zip_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Build PRAMAAN release ZIP archive.")
    parser.add_argument("--version", default="v1.0", help="Release tag version")
    parser.add_argument(
        "--bundle",
        default=str(ROOT / "offline_bundle"),
        help="Offline bundle directory containing BUNDLE_SHA256SUMS.txt",
    )
    args = parser.parse_args()
    bdir = Path(args.bundle)
    build_release_zip(version=args.version, bundle_dir=bdir if bdir.exists() else None)
    return 0


if __name__ == "__main__":
    sys.exit(main())
