# PRAMAAN Cryptographic & Forensic Boundaries (LIMITS.md)

This document clearly outlines what the PRAMAAN evidence integrity foundation protects against, and what it fundamentally cannot protect against due to physical and cryptographic constraints.

---

## 1. What PRAMAAN Integrity Protects Against

1. **Silent Bit Rot and Storage Corruption**
   - SHA-256 digests are computed over raw input streams during ingest and recorded in SQLite metadata.
   - Any flipped bit, truncated byte, or silent file mutation on disk immediately fails the verification check (`verify_case_integrity`) and identifies the exact failing exhibit.

2. **Retroactive Evidence Tampering & Evidence Swapping**
   - All files are stored under their SHA-256 hash in a content-addressable, read-only evidence store.
   - Replacing a file with different content (even of the exact same size) or swapping exhibits EX-001 and EX-002 is detected and flagged by both SHA-256 comparison and Merkle tree root computation.

3. **Custody Log Insertion, Deletion, and Modification**
   - The custody log uses SHA-256 hash-chaining: every entry seals the previous record's hash along with canonical JSON encoding of sequence, UTC timestamp, actor, action, and details.
   - Inserting, deleting, or editing any historical custody row breaks the cryptographic chain at that exact sequence number.
   - SQLite database triggers (`trg_custody_no_update`, `trg_custody_no_delete`) block runtime SQL `UPDATE` and `DELETE` queries at the database engine level.

4. **Package & Manifest Tampering**
   - Case exhibits, their hashes, and the deterministic Merkle root are assembled into a `manifest.json`.
   - The manifest is digitally signed using an asymmetric Ed25519 keypair.
   - Any offline modification to the manifest, case exhibits, or Merkle root invalidates the Ed25519 cryptographic signature.

5. **Accidental Dropping of Evidence Units (Audit Reconciliation)**
   - Evidence parsers implement strict accounting: every input line, CSV row, or PDF page is classified into parsed events, skipped units (with explicit reasons), or error units.
   - Nothing is silently dropped.

---

## 2. What PRAMAAN Cannot Protect Against (Inherent Boundaries)

1. **Full Host / Root Compromise**
   - If an adversary gains unrestricted root or administrative access to the forensic workstation, they have access to the raw disk, SQLite files, and the local Ed25519 private key.
   - An attacker with root control could drop database triggers, rebuild a fraudulent custody chain, recompute a new Merkle root, and re-sign with a new key.
   - **Forensic Mitigation:** The Ed25519 public key fingerprint and the Merkle root are printed physically and embedded in the Section 65B Indian Evidence Act court certificate at the time of export. The court or opposing counsel can compare the hardcopy seal against digital files on an independent machine using the standalone verifier (`verifier.py`).

2. **Absence of a Trusted Network Timestamping Authority (Offline Operation)**
   - PRAMAAN runs 100% offline with zero external network connectivity (no NTP/RFC 3161 TSA servers).
   - Timestamps in the custody log reflect the local workstation system clock (`datetime.now(timezone.utc)`).
   - **Forensic Mitigation:** All ingested exhibits record an explicit timezone assumption (`TIMEZONE_ASSUMED: Asia/Kolkata`) in the custody log and on every extracted event. Even if the local workstation clock drifted, the relative ordering of evidence is strictly preserved and enforced by the sequential hash-chain.

3. **Authenticity of Pre-Ingest Evidence (Garbage In, Integrity Preserved)**
   - Cryptographic hashing guarantees that evidence has not been altered *since the moment of ingest*. It does not guarantee that a suspect did not forge or edit a document *prior* to handing the phone or drive to the police.
   - For example, an exported WhatsApp text file edited in Notepad prior to extraction will be faithfully hashed and preserved by PRAMAAN.
   - **Forensic Mitigation:** PRAMAAN marks parser-extracted facts as `VERIFIED BY CODE` or `LEAD`. Pre-ingest authenticity must be corroborated via multi-source correlation (e.g. cross-referencing WhatsApp messages with Call Detail Records and Bank Statement timestamps).
