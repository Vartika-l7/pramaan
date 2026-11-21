#!/usr/bin/env python3
"""PRAMAAN Tamper Demonstration Script.

Simulates a physical or digital evidence tampering attempt by copying a case
package, flipping a single byte in an evidence file, and running the standalone
verifier to demonstrate tamper detection.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_PKG = ROOT / "backend" / "case_data" / "packages" / "package_PRM-2026-0042"
LEGACY_PKG = ROOT / "backend" / "case_data" / "package_alpha"
PACKAGE_DIR = DEFAULT_PKG if DEFAULT_PKG.exists() else LEGACY_PKG
TAMPERED_DIR = ROOT / "backend" / "case_data" / "package_tampered"


def main():
    print("=" * 70)
    print("PRAMAAN TAMPER-EVIDENT FORENSIC INTEGRITY DEMO")
    print("=" * 70)

    pkg_dir = DEFAULT_PKG if DEFAULT_PKG.exists() else PACKAGE_DIR
    if not pkg_dir.exists():
        print(f"[!] Package not found at {pkg_dir}. Building demo package first...")
        from backend.app.db import init_db
        from backend.app.report.package import assemble_case_package
        conn = init_db("PRM-2026-0042")
        cur = conn.execute("SELECT COUNT(*) FROM evidence;")
        if cur.fetchone()[0] == 0:
            conn.close()
            from scripts.seed_demo import seed
            seed("PRM-2026-0042")
            conn = init_db("PRM-2026-0042")
        assemble_case_package(conn, "PRM-2026-0042", pkg_dir)
        conn.close()

    # 1. Verify original intact package
    print("\n>>> STEP 1: Verifying INTACT case package...")
    verifier_script = ROOT / "verifier" / "verifier.py"
    res1 = subprocess.run([sys.executable, str(verifier_script), "--package", str(pkg_dir)], capture_output=False)

    # 2. Duplicate package into tampered directory
    if TAMPERED_DIR.exists():
        for p in TAMPERED_DIR.rglob("*"):
            if p.is_file():
                try:
                    p.chmod(0o644)
                except OSError:
                    pass
        shutil.rmtree(TAMPERED_DIR)
    shutil.copytree(pkg_dir, TAMPERED_DIR)

    # 3. Flip a byte in an evidence file
    print("\n>>> STEP 2: Tampering with evidence file in duplicated package...")
    target_evidence = sorted((TAMPERED_DIR / "evidence").glob("*.*"))[0]
    print(f"Target file: {target_evidence.name}")
    try:
        target_evidence.chmod(0o644)
    except OSError:
        pass

    with open(target_evidence, "r+b") as f:
        data = bytearray(f.read())
        # Flip the very first byte
        original_byte = data[0]
        data[0] = original_byte ^ 0xFF
        f.seek(0)
        f.write(data)

    print(f"[x] Flipped byte 0 from 0x{original_byte:02x} to 0x{data[0]:02x} in {target_evidence.name}.")

    # 4. Run standalone verifier on tampered package
    print("\n>>> STEP 3: Running standalone verifier on TAMPERED package...")
    res2 = subprocess.run([sys.executable, str(verifier_script), "--package", str(TAMPERED_DIR)], capture_output=False)

    print("\n" + "=" * 70)
    if res2.returncode != 0:
        print("[SUCCESS] Verifier correctly detected evidence tampering and failed as expected!")
    else:
        print("[ERROR] Verifier failed to catch the tampered byte.")
    print("=" * 70)


if __name__ == "__main__":
    main()

