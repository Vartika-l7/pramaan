# PRAMAAN Production & Multi-Unit Deployment Roadmap (`docs/DEPLOYMENT_ROADMAP.md`)

This roadmap outlines the engineering steps required to transition **PRAMAAN** from a single-workstation hackathon prototype (SQLite + local filesystem + demo keys) to a shared, multi-unit deployment for cyber crime police stations and forensic laboratories.

> **Note:** No speculative throughput, cost, or accuracy percentages are claimed below; all target deployment controls are architectural requirements.

---

## Phase A — Database & Evidence Storage Migration (Single SQLite → Shared PostgreSQL + WORM Store)
1. **PostgreSQL Backend (`db.py` abstraction):**
   - Replace per-case local SQLite files with a centralized PostgreSQL cluster using strict schema isolation per case or `case_id` foreign keys with Row-Level Security (RLS).
   - Port the SQLite append-only triggers (`trg_custody_no_update`, `trg_custody_no_delete`) to PostgreSQL `BEFORE UPDATE OR DELETE` trigger functions plus database-level `REVOKE UPDATE, DELETE ON custody_log FROM app_role`.
   - Replace SQLite FTS5 (`events_fts`) with PostgreSQL `tsvector` + GIN indexes (and `pg_trgm` for transliterated entity matching).
2. **Immutable WORM Evidence Storage:**
   - Move `evidence_store/<sha256>` from local `0o444` files onto Write-Once-Read-Many (WORM) object storage (e.g., on-premise Ceph/MinIO Object Lock in Compliance Mode or hardware SAN snapshots).
   - Retain streaming SHA-256 verification before storage and periodic background scrubbing jobs.

## Phase B — Identity, Role-Based Access Control (RBAC) & Key Management
1. **Role-Based Access Control:**
   - Authenticate investigators via station LDAP/Active Directory or hardware smartcards (no external cloud SSO).
   - Enforce distinct roles matching PRAMAAN's two-workspace boundary:
     - **Evidence Custodian:** May ingest exhibits, run integrity verification, and inspect raw files.
     - **Investigator:** May run analysis pipelines, query Knowledge Graph, Reconstruction, and Assistant, and propose claims (`LEAD` tier only).
     - **Reviewing Officer / Supervisor:** Sole role authorized to issue `APPROVED` / `REJECTED` / `EDIT` decisions in the Review Queue and build court packages.
     - **External / Court Verifier:** Read-only access to exported signed case packages and `verifier.py`.
2. **HSM / PKI Signing Keys (Replacing Demo Keys):**
   - Replace the first-run local `backend/keys/ed25519_private.pem` demo keypair with FIPS 140-2/3 Hardware Security Module (HSM) or PKCS#11 USB forensic examiner tokens so private signing keys never exist in plain PEM files on disk.
   - Bind each examiner's public key to an internal agency X.509/Ed25519 certificate chain for Section 63 BSA / Section 65B IEA verification.

## Phase C — Isolated / Air-Gapped Lab Network Topology
1. **Segmented Station / Lab Deployment:**
   - Deploy PRAMAAN inside an air-gapped forensic VLAN with outbound firewall rules enforcing zero internet egress (complementing PRAMAAN's application-level `network_guard.py`).
   - Run evidence parsers inside ephemeral, unprivileged OS containers (seccomp + read-only evidence mount) so malformed suspect PDFs, images, or archives cannot compromise the host OS.
2. **Offline Model, Registry & Wheel Packaging:**
   - Mirror pinned Python wheels, Node build artifacts, Tesseract `tessdata` (`eng`, `hin`, regional scripts), optional local LLM weights (Ollama GGUF / quantized weights), and operator-supplied cell-tower / GeoIP `.mmdb` databases on signed internal artifact repositories.
   - Verify SHA-256 manifests (`BUNDLE_SHA256SUMS.txt`) and package signatures prior to deploying updates to field units.

## Phase D — Auditability & Inter-Agency Exchange
1. **Time Synchronization:**
   - Replace standalone workstation clocks with an internal stratum-1/GPS-disciplined NTP + RFC 3161 local Timestamping Authority (TSA) inside the forensic VLAN for custody timestamps.
2. **Interoperable Exports:**
   - Continue exporting self-contained ZIP court packages with `verifier.py`, GraphML knowledge graphs, Markdown/JSON event sequences, and human-signed Section 63 BSA certificates so receiving courts and oversight units need no network access or PRAMAAN installation to verify integrity.
