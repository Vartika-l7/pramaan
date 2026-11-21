# PRAMAAN Cryptographic & Forensic Boundaries (`docs/LIMITS.md`)

This document clearly outlines what the PRAMAAN evidence integrity foundation and analysis engines protect against, and what they fundamentally cannot guarantee due to physical, cryptographic, and operational constraints.

---

## 1. What PRAMAAN Integrity Protects Against

1. **Silent Bit Rot and Storage Corruption**
   - SHA-256 digests are computed over raw streaming 1 MB chunks during ingest and recorded in SQLite metadata.
   - Any flipped bit, truncated byte, or silent file mutation on disk immediately fails `verify_case_integrity()` and identifies the exact failing exhibit (`failed_exhibit`).

2. **Retroactive Evidence Tampering & Evidence Swapping**
   - All files are stored under their SHA-256 hash in a content-addressable, read-only (`0o444`) evidence store (`backend/evidence_store/<sha256>`).
   - Replacing a file with different content or swapping exhibits fails both SHA-256 comparison and deterministic Merkle tree root computation.

3. **Custody Log Insertion, Deletion, and Modification**
   - `custody_log` uses SHA-256 hash-chaining across canonical JSON records (`seq`, `ts_utc`, `actor`, `action`, `evidence_id`, `details`).
   - SQLite triggers (`trg_custody_no_update`, `trg_custody_no_delete`) block SQL `UPDATE` and `DELETE` queries at the database engine level.

4. **Package & Manifest Tampering**
   - Case exhibits, hashes, and the deterministic Merkle root are serialized to `manifest.json` and signed with Ed25519 (`manifest.sig`).
   - Standalone `verifier/verifier.py` independently validates file hashes, Merkle root, `audit_log.json` hash chain, and Ed25519 signature offline.

5. **Silent Evidence Dropping (Unit Reconciliation)**
   - Every parser implements `parse_with_report()`, guaranteeing `total_units == parsed_events + len(skipped_units) + len(errors)`.

6. **Unapproved AI Output Entering Court Reports**
   - AI outputs are hashed into `ai_runs` + `custody_log`, filtered by deterministic Rules V1–V5, and restricted to `LEAD` tier until a human explicitly approves them in **Review and Report**. Only `APPROVED` claims and edges enter the court report preview and PDF.

---

## 2. What PRAMAAN Cannot Protect Against (Inherent Boundaries)

1. **First-Run Demo Signing Keys vs. Production HSM/PKI**
   - On first run, `backend/app/integrity/signer.py` generates a local Ed25519 keypair in `backend/keys/` (`ed25519_private.pem`, `ed25519_public.pem`). **These are demo keys for local evaluation only.**
   - Anyone with root/host access to the demo workstation can read the local PEM file and drop SQLite triggers.
   - **Mitigation:** Exported court packages embed the Merkle root and public key fingerprint in the Section 63 BSA / Section 65B IEA draft certificate and QR payload for independent offline verification (`verifier.py`). Production deployments must use HSMs or smartcard PKI (see [`docs/DEPLOYMENT_ROADMAP.md`](DEPLOYMENT_ROADMAP.md)).

2. **Absence of a Trusted Network Timestamping Authority (Strict Offline Mode)**
   - Under `OFFLINE=1`, PRAMAAN blocks all non-loopback sockets (`0 outbound connections`), so no external NTP or RFC 3161 TSA server is contacted.
   - Custody timestamps come from the workstation's local UTC clock (`datetime.now(timezone.utc)`), and evidence without embedded offsets records `TIMEZONE_ASSUMED` (`Asia/Kolkata`).

3. **Authenticity of Pre-Ingest Evidence ("Garbage In, Integrity Preserved")**
   - SHA-256 hashing proves an exhibit was not altered *after ingest*, not that it was genuine prior to seizure.
   - **Mitigation:** PRAMAAN surfaces EXIF/ELA indicators, bank running-balance discrepancies, and cross-source correlation checks as `LEAD` / `TAMPERED` indicators for human verification.

4. **Optional Offline Binaries & Reference Data**
   - **CCTV Video:** `CCTVVideoParser` provides cryptographic hashing, provenance, and container metadata (`ffprobe` if installed) — **no video/face analytics** are performed.
   - **IP Geolocation:** Without an operator-supplied offline `.mmdb` (`GEOIP_DB_PATH`), `lookup_ip_location()` returns `"location unknown"`.
   - **OCR & Local LLM:** When Tesseract or Ollama are absent, `ImageParser` marks `ocr_status: "UNAVAILABLE"` and AI flows operate in `DeterministicProvider` mode without inventing facts.
