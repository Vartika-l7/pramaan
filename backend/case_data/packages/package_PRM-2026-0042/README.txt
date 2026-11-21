================================================================================
PRAMAAN STANDALONE EVIDENCE PACKAGE: PRM-2026-0042
================================================================================

This package contains signed, tamper-evident digital evidence, investigative findings,
and cryptographic audit trails for Case PRM-2026-0042.

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
  3. Recompute and match the Merkle root (e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855)
  4. Walk and verify the entire audit log hash chain
  5. Validate the Ed25519 signature
================================================================================
