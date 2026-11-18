"""Case Package Assembler: ZIP archive, manifests, signatures, and verifier."""

from __future__ import annotations

import csv
import json
import shutil
import sqlite3
import zipfile
from pathlib import Path
from typing import Dict, Any

from backend.app.config import CASE_DATA_DIR, KEYS_DIR
from backend.app.integrity.merkle import compute_case_merkle_root
from backend.app.integrity.signer import sign_data, PUBLIC_KEY_PATH
from backend.app.report.render import generate_court_report_pdf
from backend.app.verify.challenger import run_challenger_analysis

PACKAGES_DIR = CASE_DATA_DIR / "packages"
PACKAGES_DIR.mkdir(parents=True, exist_ok=True)


def assemble_case_package(
    conn: sqlite3.Connection,
    case_id: str = "PRM-2026-0042",
    target_package_dir: Path | None = None,
) -> Path:
    """Build the signed, tamper-evident court package folder and ZIP."""
    pkg_dir = target_package_dir or (PACKAGES_DIR / f"package_{case_id}")
    if pkg_dir.exists():
        shutil.rmtree(pkg_dir)
    pkg_dir.mkdir(parents=True, exist_ok=True)

    evidence_sub = pkg_dir / "evidence"
    evidence_sub.mkdir(parents=True, exist_ok=True)

    # 1. Copy evidence files & collect hashes
    cursor = conn.cursor()
    cursor.execute("SELECT exhibit_id, filename, sha256, size_bytes, stored_path FROM evidence ORDER BY exhibit_id ASC;")
    exhibits_rows = cursor.fetchall()

    exhibits_manifest = []
    hashes_csv_rows = [["exhibit_id", "filename", "sha256", "size_bytes"]]

    for r in exhibits_rows:
        src_path = Path(r["stored_path"])
        if src_path.exists():
            dest = evidence_sub / r["filename"]
            shutil.copy2(src_path, dest)

        ex_dict = {
            "exhibit_id": r["exhibit_id"],
            "filename": r["filename"],
            "sha256": r["sha256"],
            "size_bytes": r["size_bytes"],
        }
        exhibits_manifest.append(ex_dict)
        hashes_csv_rows.append([r["exhibit_id"], r["filename"], r["sha256"], str(r["size_bytes"])])

    # 2. Compute Merkle root & write manifest.json
    merkle_root, _ = compute_case_merkle_root(conn)
    manifest_data = {
        "case_id": case_id,
        "merkle_root": merkle_root,
        "total_exhibits": len(exhibits_manifest),
        "exhibits": exhibits_manifest,
    }
    manifest_path = pkg_dir / "manifest.json"
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest_data, f, indent=2, ensure_ascii=False)

    # 3. Cryptographically sign manifest with Ed25519
    manifest_bytes = manifest_path.read_bytes()
    sig_b64, pub_b64 = sign_data(manifest_bytes)

    with open(pkg_dir / "manifest.sig", "w", encoding="utf-8") as f:
        f.write(sig_b64)

    # Copy public key PEM
    if PUBLIC_KEY_PATH.exists():
        shutil.copy2(PUBLIC_KEY_PATH, pkg_dir / "public_key.pem")

    # 4. Generate Court Report PDF
    pdf_path = pkg_dir / "report.pdf"
    generate_court_report_pdf(conn, pdf_path, case_id=case_id)

    # 5. Export Audit Log JSON
    cursor.execute("SELECT * FROM custody_log ORDER BY seq ASC;")
    custody_rows = [dict(r) for r in cursor.fetchall()]
    cursor.execute("SELECT * FROM reviews ORDER BY rowid ASC;")
    review_rows = [dict(r) for r in cursor.fetchall()]

    audit_path = pkg_dir / "audit_log.json"
    with open(audit_path, "w", encoding="utf-8") as f:
        json.dump({"custody_log": custody_rows, "reviews": review_rows}, f, indent=2)

    # 6. Export evidence_hashes.csv
    csv_path = pkg_dir / "evidence_hashes.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerows(hashes_csv_rows)

    # 7. Generate Internal Defence Weakness Report (HTML)
    challenges = run_challenger_analysis(conn)
    html_lines = [
        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Internal Defence Weakness Report</title>",
        "<style>body{font-family:sans-serif;padding:30px;line-height:1.6;color:#2B1B17;background:#FBF8F3}",
        ".box{background:#FFF;border:1px solid #E8D9CC;padding:15px;margin-bottom:15px;border-radius:6px}",
        ".high{border-left:5px solid #DB4A2B}.med{border-left:5px solid #C97B1A}",
        ".tag{display:inline-block;padding:2px 8px;font-size:10px;font-family:monospace;border-radius:4px;font-weight:bold}",
        ".tag-high{background:#FDF1EE;color:#DB4A2B}.tag-med{background:#FDF6E9;color:#C97B1A}",
        "</style></head><body>",
        f"<h1>INTERNAL CONFIDENTIAL: DEFENCE WEAKNESS REPORT</h1>",
        f"<p><b>Case:</b> {case_id} | <b>Total Potential Objections:</b> {challenges['total_objections']}</p>",
        "<p><i>This document is prepared for internal prosecution strategy only and must not be disclosed in open court filings.</i></p>",
    ]
    for obj in challenges["objections"]:
        cls = "high" if obj["severity"] == "HIGH" else "med"
        tag_cls = "tag-high" if obj["severity"] == "HIGH" else "tag-med"
        html_lines.append(f"<div class='box {cls}'>")
        html_lines.append(f"<span class='tag {tag_cls}'>{obj['severity']} RISK</span> <b>{obj['title']}</b>")
        html_lines.append(f"<p><b>Anticipated Defence Argument:</b> {obj['argument']}</p>")
        html_lines.append(f"<p style='color:#3F7D58'><b>Suggested Remedy:</b> {obj['suggested_fix']}</p>")
        html_lines.append("</div>")
    html_lines.append("</body></html>")

    with open(pkg_dir / "defence_weakness_report.html", "w", encoding="utf-8") as f:
        f.write("\n".join(html_lines))

    # 8. Copy standalone verifier.py
    src_verifier = Path(__file__).resolve().parent.parent.parent.parent / "verifier" / "verifier.py"
    if src_verifier.exists():
        shutil.copy2(src_verifier, pkg_dir / "verifier.py")

    # 9. Write README.txt
    readme_text = f"""================================================================================
PRAMAAN STANDALONE EVIDENCE PACKAGE: {case_id}
================================================================================

This package contains signed, tamper-evident digital evidence, investigative findings,
and cryptographic audit trails for Case {case_id}.

CONTENTS:
  - report.pdf                     Official examination report with Section 63 BSA draft
  - manifest.json                  Evidence manifest and Merkle root digest
  - manifest.sig                   Ed25519 digital signature of manifest.json
  - public_key.pem                 Ed25519 public key used for signature verification
  - audit_log.json                 Append-only, hash-chained custody & review log
  - evidence_hashes.csv            Exhibit inventory and SHA-256 hashes
  - defence_weakness_report.html   Internal cross-examination analysis (CONFIDENTIAL)
  - verifier.py                    Standalone verification script
  - evidence/                      Raw ingested digital evidence exhibits

OFFLINE VERIFICATION INSTRUCTIONS:
To verify this case package independently on any Windows, macOS, or Linux machine
without internet access, run:

    python verifier.py --package .

The verifier will:
  1. Re-hash every evidence file in /evidence using SHA-256
  2. Verify all hashes against manifest.json
  3. Recompute and match the Merkle root ({merkle_root})
  4. Walk and verify the entire audit log hash chain
  5. Validate the Ed25519 signature
================================================================================
"""
    with open(pkg_dir / "README.txt", "w", encoding="utf-8") as f:
        f.write(readme_text)

    # 10. Create ZIP Archive
    zip_path = PACKAGES_DIR / f"case_{case_id}_package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in pkg_dir.rglob("*"):
            if file.is_file():
                zf.write(file, file.relative_to(pkg_dir))

    return zip_path

