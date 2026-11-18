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

PACKAGE_DIR = Path(__file__).resolve().parent.parent / "backend" / "case_data" / "package_alpha"
TAMPERED_DIR = Path(__file__).resolve().parent.parent / "backend" / "case_data" / "package_tampered"


def main():
    print("=" * 70)
    print("PRAMAAN TAMPER-EVIDENT FORENSIC INTEGRITY DEMO")
    print("=" * 70)

    if not PACKAGE_DIR.exists():
        print(f"[!] Package not found at {PACKAGE_DIR}. Building demo package first...")
        from backend.app.db import get_db_connection
        from backend.app.report.package import assemble_case_package
        conn = get_db_connection("PRM-2026-0042")
        assemble_case_package(conn, "PRM-2026-0042", PACKAGE_DIR)
        conn.close()

    # 1. Verify original intact package
    print("\n>>> STEP 1: Verifying INTACT case package...")
    verifier_script = Path(__file__).resolve().parent.parent / "verifier" / "verifier.py"
    res1 = subprocess.run([sys.executable, str(verifier_script), "--package", str(PACKAGE_DIR)], capture_output=False)

    # 2. Duplicate package into tampered directory
    if TAMPERED_DIR.exists():
        shutil.rmtree(TAMPERED_DIR)
    shutil.copytree(PACKAGE_DIR, TAMPERED_DIR)

    # 3. Flip a byte in an evidence file
    print("\n>>> STEP 2: Tampering with evidence file in duplicated package...")
    target_evidence = list((TAMPERED_DIR / "evidence").glob("*.*"))[0]
    print(f"Target file: {target_evidence.name}")

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

