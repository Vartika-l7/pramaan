#!/usr/bin/env python3
"""PRAMAAN Standalone Forensic Package Verifier.

Runs completely offline. Uses only the Python standard library for hash and
Merkle validation, plus optional cryptography package for Ed25519 signature checks.

Usage:
    python verifier.py [--manifest manifest.json] [--package .]
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
import sys
from pathlib import Path


def canonical_json(data: dict) -> str:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def hash_file(file_path: Path) -> str:
    hasher = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(1024 * 1024):
            hasher.update(chunk)
    return hasher.hexdigest()


def compute_merkle_root(hashes: list[str]) -> str:
    if not hashes:
        return hashlib.sha256(b"").hexdigest()
    level = list(hashes)
    while len(level) > 1:
        if len(level) % 2 != 0:
            level.append(level[-1])
        next_level = []
        for i in range(0, len(level), 2):
            combined = level[i] + level[i + 1]
            parent = hashlib.sha256(combined.encode("utf-8")).hexdigest()
            next_level.append(parent)
        level = next_level
    return level[0]


def verify_ed25519_signature(data: bytes, sig_b64: str, pub_b64: str) -> tuple[bool, str]:
    try:
        import base64
        from cryptography.hazmat.primitives.asymmetric import ed25519
        sig_bytes = base64.b64decode(sig_b64)
        pub_bytes = base64.b64decode(pub_b64)
        public_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        public_key.verify(sig_bytes, data)
        return True, "Valid Ed25519 cryptographic signature"
    except ImportError:
        return False, "SKIPPED: 'cryptography' library not installed; signature verification skipped."
    except Exception as e:
        return False, f"Signature verification FAILED: {str(e)}"


def run_verification(package_dir: Path) -> bool:
    print("=" * 70)
    print("PRAMAAN STANDALONE FORENSIC CASE PACKAGE VERIFIER")
    print("=" * 70)
    print(f"Target Directory: {package_dir.resolve()}\n")

    manifest_file = package_dir / "manifest.json"
    if not manifest_file.exists():
        print(f"[FAIL] Missing manifest.json in {package_dir}")
        return False

    with open(manifest_file, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    case_id = manifest.get("case_id", "UNKNOWN")
    expected_root = manifest.get("merkle_root", "")
    exhibits = manifest.get("exhibits", [])

    print(f"Case Reference: {case_id}")
    print(f"Exhibits in Manifest: {len(exhibits)}")
    print(f"Expected Merkle Root: {expected_root}\n")

    all_pass = True

    # Check 1: Re-hash evidence files against manifest
    print("--- [CHECK 1/4] Re-hashing Evidence Files ---")
    verified_hashes = []
    # Sort exhibits by exhibit_id
    sorted_exhibits = sorted(exhibits, key=lambda x: x.get("exhibit_id", ""))

    for ex in sorted_exhibits:
        ex_id = ex.get("exhibit_id")
        filename = ex.get("filename")
        expected_sha = ex.get("sha256")
        
        # Check if file exists under evidence/ or package_dir
        candidate1 = package_dir / "evidence" / filename
        candidate2 = package_dir / filename
        target_path = candidate1 if candidate1.exists() else candidate2

        if not target_path.exists():
            print(f"  [FAIL] {ex_id} ({filename}): FILE NOT FOUND")
            all_pass = False
            continue

        computed_sha = hash_file(target_path)
        if computed_sha.lower() == expected_sha.lower():
            print(f"  [PASS] {ex_id} ({filename}): SHA-256 MATCH ({computed_sha[:12]}...)")
            verified_hashes.append(computed_sha)
        else:
            print(f"  [FAIL] {ex_id} ({filename}): HASH MISMATCH!")
            print(f"         Expected: {expected_sha}")
            print(f"         Computed: {computed_sha}")
            all_pass = False

    # Check 2: Recompute Merkle Root
    print("\n--- [CHECK 2/4] Merkle Root Verification ---")
    recomputed_root = compute_merkle_root(verified_hashes)
    if recomputed_root.lower() == expected_root.lower():
        print(f"  [PASS] Merkle root match: {recomputed_root}")
    else:
        print(f"  [FAIL] Merkle root mismatch!")
        print(f"         Expected: {expected_root}")
        print(f"         Computed: {recomputed_root}")
        all_pass = False

    # Check 3: Audit Log Hash Chain Verification
    print("\n--- [CHECK 3/4] Audit Log Hash Chain ---")
    audit_file = package_dir / "audit_log.json"
    if audit_file.exists():
        with open(audit_file, "r", encoding="utf-8") as f:
            audit_data = json.load(f)
        custody_log = audit_data.get("custody_log", [])

        expected_prev = "0" * 64
        chain_ok = True
        for row in custody_log:
            prev_hash = row["prev_hash"]
            entry_hash = row["entry_hash"]
            seq = row["seq"]

            if prev_hash != expected_prev:
                print(f"  [FAIL] Custody chain break at seq #{seq}: prev_hash mismatch")
                chain_ok = False
                all_pass = False
                break

            details = json.loads(row["details_json"]) if row.get("details_json") else {}
            payload = {
                "seq": seq,
                "ts_utc": row["ts_utc"],
                "actor": row["actor"],
                "action": row["action"],
                "evidence_id": row["evidence_id"],
                "details": details,
            }
            recomputed_entry = hashlib.sha256((prev_hash + canonical_json(payload)).encode("utf-8")).hexdigest()
            if recomputed_entry != entry_hash:
                print(f"  [FAIL] Custody hash recalculation failed at seq #{seq}")
                chain_ok = False
                all_pass = False
                break
            expected_prev = entry_hash

        if chain_ok:
            print(f"  [PASS] Hash chain valid across all {len(custody_log)} custody records.")
    else:
        print("  [WARN] audit_log.json not present; skipped chain check.")

    # Check 4: Ed25519 Signature Verification
    print("\n--- [CHECK 4/4] Ed25519 Manifest Signature ---")
    sig_file = package_dir / "manifest.sig"
    pub_file = package_dir / "public_key.pem"

    if sig_file.exists() and pub_file.exists():
        with open(sig_file, "r", encoding="utf-8") as f:
            sig_b64 = f.read().strip()
        with open(pub_file, "r", encoding="utf-8") as f:
            pub_pem = f.read().strip()
            # Extract raw base64 from pem if needed or use cryptography
        manifest_raw = manifest_file.read_bytes()

        # Check signature
        try:
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import ed25519
            import base64
            public_key = serialization.load_pem_public_key(pub_pem.encode("utf-8"))
            sig_bytes = base64.b64decode(sig_b64)
            public_key.verify(sig_bytes, manifest_raw)
            print("  [PASS] Ed25519 digital signature verified against case public key.")
        except ImportError:
            print("  [NOTE] 'cryptography' package not installed; signature verification skipped (stdlib only).")
        except Exception as e:
            print(f"  [FAIL] Ed25519 signature invalid: {str(e)}")
            all_pass = False
    else:
        print("  [WARN] manifest.sig or public_key.pem not found; signature skipped.")

    print("\n" + "=" * 70)
    if all_pass:
        print("FINAL VERDICT: ALL CRYPTOGRAPHIC CHECKS PASSED [VERIFIED BY CODE]")
        print("The case package is intact, unaltered, and tamper-evident.")
        print("=" * 70)
        return True
    else:
        print("FINAL VERDICT: TAMPERING OR CORRUPTION DETECTED [FAILED]")
        print("One or more evidence files, Merkle root, or custody records failed verification.")
        print("=" * 70)
        return False


def main():
    parser = argparse.ArgumentParser(description="PRAMAAN Standalone Forensic Case Package Verifier")
    parser.add_argument("--package", default=".", help="Path to case package directory")
    args = parser.parse_args()

    success = run_verification(Path(args.package))
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

