# PRAMAAN Scope & Feature Tracking

This document inventories every feature, page, API endpoint, and background job in PRAMAAN. Every component is evaluated strictly against the 5 PS3 deliverables:
1. **Evidence Correlation Engine**
2. **Knowledge Graph Generation Framework**
3. **Crime Reconstruction Dashboard**
4. **Automated Event-Sequence Generator**
5. **Interactive Visual Investigation Platform**
*(and the underlying integrity foundation supporting them)*.

---

## Complete Component Inventory & Classification

| Component / Feature | Type | Action | PS3 Deliverable / Foundation Alignment | Detail / Reason |
| :--- | :--- | :--- | :--- | :--- |
| **Ingest, Hashing & Storage** | Backend / Store | **KEEP** | Integrity Foundation | Computes chunked SHA-256 and stores read-only under hash. |
| **Custody Log & DB Triggers** | Backend / DB | **KEEP** | Integrity Foundation | Hash-chained log with SQLite UPDATE/DELETE trigger enforcement. |
| **Merkle Root & Ed25519 Signing** | Backend / Cryptography | **KEEP** | Integrity Foundation | Cryptographic manifest sealing with Section 65B compliance. |
| **Integrity Verification Endpoint** | API (`/api/integrity`) | **KEEP** | Integrity Foundation | Real-time re-hashing and chain auditing across all exhibits. |
| **All Parsers (WhatsApp, Bank PDF/CSV, CDR, Image)** | Backend / Parsers | **KEEP** | Deliverable 4 (Event-Sequence) & Foundation | Normalises raw exhibits into chronological forensic events with reconciliation. |
| **Entity Extraction & Spans** | Backend (`app/extract`) | **KEEP** | Deliverable 2 (Knowledge Graph) | Deterministic and IndicNER entity mention extraction with exact char spans. |
| **Evidence Correlation Logic** | Backend (`app/correlate`) | **KEEP** | Deliverable 1 (Correlation Engine) | Multi-hop cross-source rule-based correlation producing scored edges. |
| **Knowledge Graph Generation** | Backend & UI (`/graph`) | **KEEP** | Deliverable 2 (Knowledge Graph) | Interactive visual graph with tier badges, strength filtering, and edge inspector. |
| **Event Timeline & Anomaly Detection** | Backend & UI (`/events`) | **KEEP** | Deliverable 3 & 4 (Event-Sequence / Reconstruction) | Chronological sequence generator, silence gap detector, and out-of-order detection. |
| **Authenticity Engine (EXIF, ELA, pHash, Bank Math)** | Backend (`app/authenticity`) | **KEEP** | Deliverable 3 & 5 (Reconstruction & Investigation) | Detects forged receipts, image modifications, and bank balance discrepancies. |
| **Claims & Deterministic Verifier** | Backend (`app/verify`) | **KEEP** | Deliverable 3 (Reconstruction Dashboard) | AI-drafted claims verified deterministically against database records. |
| **Review Queue** | Backend & UI (`/review`) | **KEEP** | Deliverable 5 (Visual Investigation) | Human-in-the-loop review queue to approve, reject, or edit AI proposals. |
| **Court Report & Signed Package** | Backend & UI (`/package`) | **KEEP** | Deliverable 3 (Crime Reconstruction) | Standalone ZIP case package, PDF generation, and offline `verifier.py`. |
| **Entities Page (`/entities`)** | Frontend Page | **FOLD** | Deliverable 2 & 5 (Graph & Evidence) | Folded into search and detail side panels within Knowledge Graph and Evidence Vault. |
| **Authenticity Page (`/authenticity`)** | Frontend Page | **FOLD** | Deliverable 5 (Evidence Vault) | Folded into a dedicated "Authenticity & Forensics" tab inside each Exhibit detail drawer. |
| **Challenge Page (`/verifier`)** | Frontend Page | **FOLD** | Deliverable 3 (Reconstruction / Review) | Folded into an actionable cross-examination trigger inside Claims and Review Queue. |
| **Audit Log Page** | Frontend Page | **FOLD** | Integrity Foundation | Folded into "Chain of Custody" tab inside Exhibit details and included in export packages. |
| **System Capabilities Panel** | UI Component | **FOLD** | Deliverable 5 (Visual Platform) | Replaced bulky modal with a lightweight popover status chip in the top CaseBar. |
| **Metrics & Benchmark Page (`/metrics`)** | Frontend Page | **CUT** | Out of core investigative workflow | Removed standalone UI page to prevent vanity metrics; benchmark preserved in `scripts/benchmark.py` and JSON. |
| **Command Palette (⌘K modal)** | UI Component | **CUT** | Redundant UI complexity | Replaced complex modal with a clean, unified quick-navigation search box. |
| **Multi-lane timeline modes** | Frontend Feature | **CUT** | Cluttered visual timeline | Retained single clean toggle (Source / Actor) to prevent noisy timeline lanes. |
| **Secondary Graph Layouts** | Frontend Feature | **CUT** | Redundant UI toggles | Standardized on one optimal physics layout (`fcose`) without distracting switchers. |
| **Non-reproducible burst/clustering heuristics** | Backend Feature | **CUT** | Unreliable heuristic | Cut ungrounded burst clustering; preserved verified silence-gap and out-of-order detectors. |
| **Duplicate Package Exports** | Backend / API | **CUT** | Redundant artifacts | Cut standalone ad-hoc export endpoints duplicating the official signed case package. |

---

## Removals and Deprecations Log

| Date | Component / Feature | Action | Reason |
| :--- | :--- | :--- | :--- |
| 2026-11-19 | `MetricsPage.tsx` (`/metrics`) | **CUT** | Investigating officers need workflow tools, not benchmark graphs in navigation. Benchmark scripts remain in `scripts/benchmark.py`. |
| 2026-11-19 | Heavy `CommandPalette.tsx` | **CUT** | Replaced with focused search box in `CaseBar.tsx` for cleaner visual investigation experience. |
| 2026-11-19 | Extra Graph Layout engines | **CUT** | Cytoscape pinned to deterministic `fcose` physics layout to prevent erratic node shifting. |
| 2026-11-19 | Uncalibrated burst detectors | **CUT** | Only deterministic mathematical anomalies (median-gap chat silences and inverted timestamps) are retained. |
| 2026-11-22 | `ReviewQueuePage.tsx` + `CasePackagePage.tsx` | **FOLD** | Consolidated into the 3-step `ReviewAndReportPage.tsx` (`/review`) gate so human review, court package export, and standalone verification live in one flow. |
| 2026-11-22 | `EventSequencePage.tsx` (`/events`) | **FOLD** | Renamed and expanded into `ReconstructionPage.tsx` (`/reconstruction`) with offline Locations coordinate canvas and synchronized Scene Replay (`/events` redirects to `/reconstruction`). |
| 2026-11-22 | `CommandPalette.tsx` (unused file) | **CUT** | Removed unused legacy file (already cut in Phase 2A in favor of CaseBar quick navigation). |
| 2026-11-22 | Legacy unrouted pages (`AuthenticityPage.tsx`, `CasePackagePage.tsx`, `EntitiesPage.tsx`, `EventSequencePage.tsx`, `MetricsPage.tsx`, `ReviewQueuePage.tsx`, `VerifierChallengePage.tsx`) | **CUT** | Dead files superseded by the 6-page layout (`EvidenceVaultPage`, `ReviewAndReportPage`, `KnowledgeGraphPage`, `ReconstructionPage`, `AssistantPage`, `OverviewPage`). |
| 2026-11-22 | Unused npm dependency `cmdk` | **CUT** | Unused after cutting `CommandPalette.tsx`; removed from `frontend/package.json` and pinned all versions. |
| 2026-11-22 | Unused Python dependencies (`pandas`, `faker`, `jinja2`, `pyhanko`) | **CUT** | Zero imports in `backend/`, `scripts/`, `tests/`, or `verifier/`; removed from `requirements.txt` and pinned remaining versions. |
