# Phase 1 Report: Evidence Foundation Audit & Hardening

## What changed
1. **Reconciliation Accounting Engine (`ParseReport`)**:
   - Added `ParseReport`, `SkippedUnit`, and `ParseErrorUnit` abstractions in `backend/app/parsers/base.py`.
   - Updated WhatsApp, Bank CSV, Call Log, and Bank PDF parsers to implement `parse_with_report()`, ensuring mathematical reconciliation:
     $$\text{Input Units} = \text{Parsed Events} + \text{Skipped Units} + \text{Errors}$$
   - Added `parse_report_json` column to the `evidence` SQLite table and surfaced `parse_report` in `GET /api/evidence/{id}`.
2. **Parser Hardening & Validation**:
   - Bank CSV (`BankCSVParser`) and Call Log (`CallLogParser`) now strictly validate column schemas upon ingest and fail loudly with descriptive errors instead of silent omissions.
   - WhatsApp parser (`WhatsAppParser`) now detects and categorizes deleted message markers (`kind="deleted_message"`) across both Android and iOS formats.
   - Added byte offset and byte length tracking to Bank CSV and Call Log records alongside WhatsApp events.
3. **True Pluggable Parser Architecture**:
   - Added `registry.detect_source_type()`, eliminating hardcoded file extension checks from ingest and custody services.
   - Verified that new evidence formats can be plugged in by adding a class and calling `registry.register(parser)` without touching ingest, hashing, or custody logic.
4. **Ingest Security & Edge-Case Protection**:
   - Filename sanitization via `Path(filename).name` blocks directory traversal attacks (e.g., `../../sensitive_file`).
   - Added configurable `MAX_UPLOAD_SIZE_BYTES` (default 500 MB) preventing unconstrained stream exhaustion.
   - Duplicate file uploads map to the existing exhibit, avoid re-writing to disk, and record a `DUPLICATE_INGEST_ATTEMPT` event in the hash-chained custody log.
   - Temporary upload files are guaranteed to be cleaned up in a `finally` block even when ingestion encounters errors.
5. **Manifest & End-to-End Cryptographic Verification**:
   - Digital signatures generated on package export are recorded in the `manifests` table and verified by `verify_case_integrity()`.
   - Added NIST KAT (Known-Answer Test) suite and property-style tamper detection tests.
6. **Documentation**:
   - Created `docs/AUDIT.md`, `docs/SCOPE.md`, and `docs/LIMITS.md`.

## Why
In digital forensics and criminal investigations under the Indian Evidence Act (including Section 65B requirements), evidence cannot be presented if there is any doubt regarding its provenance, chain of custody, or potential alteration. If an evidence parser silently ignores 10 rows from a bank statement or skips deleted WhatsApp messages, critical exculpatory or incriminating evidence would be lost. Furthermore, the integrity engine must mathematically prove that every byte ingested remains unmodified, that duplicate submissions are audited, and that third-party tampering is detected down to the exact exhibit and sequence number.

## How to explain this to judges in three sentences
PRAMAAN establishes an uncompromised chain of custody by hashing all incoming evidence streams with SHA-256 and locking them in an immutable, append-only SQLite log protected by database engine triggers. Every parsed record links back to its exact byte offset and line number in the raw evidence, backed by a reconciliation report proving zero silently dropped records. The entire case is cryptographically sealed into a Merkle tree and signed with Ed25519, allowing any court or independent examiner to verify the integrity of the evidence offline with a single click.

## What is still weak
- While WhatsApp, Bank CSV, and Call Log parsers capture line numbers and byte offsets, Bank PDF parsing relies on `pdfplumber` page and table row indices rather than exact PDF stream byte offsets.
- When direct database modifications are performed outside SQLite (such as direct raw hex editing of the database file on disk), the database triggers are bypassed; however, PRAMAAN's application-level `verify_chain()` and Merkle root recomputation detect this corruption immediately upon verification.
- Offline workstations cannot consult an external RFC 3161 Timestamping Authority (TSA), so timestamps reflect the local system clock at the moment of ingest, which is explicitly recorded in `tz_assumed`.

## How I tested it
Ran the complete test suite including newly created Known-Answer Tests (KAT), tamper detection tests, edge-case tests, and reconciliation tests:
- NIST SHA-256 Known-Answer Tests for empty input and "abc".
- 200 MB streaming vs one-shot hash verification against Windows OS `certutil -hashfile`.
- Single-bit file tampering tests and property-style random mutation test.
- Custody log UPDATE and DELETE rejection via database triggers.
- Custody log row deletion and reordering detection.
- Path traversal rejection and file upload limit enforcement.
- Schema validation tests for malformed CSV and CDR logs.
- WhatsApp reconciliation test accounting for preamble lines, multi-line continuations, empty lines, and deleted message markers.

### Command Execution Output
```
============================= test session starts =============================
platform win32 -- Python 3.12.4, pytest-8.3.4, pluggy-1.6.0
rootdir: C:\Users\Vartika Sharma\Desktop\pramaan
plugins: anyio-4.11.0, Faker-40.54.0, langsmith-0.8.18, cov-5.0.0
collected 38 items

tests\test_phase0_scaffold.py ...                                        [  7%]
tests\test_phase1_hardening.py ....................                      [ 60%]
tests\test_phase1_integrity.py ......                                    [ 76%]
tests\test_phase2_parsers.py ....                                        [ 86%]
tests\test_phase3_extraction.py ...                                      [ 94%]
tests\test_phase4_correlation.py .                                       [ 97%]
tests\test_phase5_anomalies.py .                                         [100%]

============================= 38 passed in 9.93s ==============================
```
