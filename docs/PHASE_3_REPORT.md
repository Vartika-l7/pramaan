# Phase 3 Report: Two-Workspace UI & Visual Redesign

## What changed
1. **Offline Design System (`frontend/src/styles/tokens.css`, `frontend/tailwind.config.js`)**:
   - Removed the external Google Fonts CDN `@import` and bundled `@fontsource/source-serif-4`, `@fontsource/ibm-plex-sans` (14px UI), and `@fontsource/ibm-plex-mono` (tabular numbers) locally.
   - Standardized CSS variables: paper `#FBF8F3`, panels `#FFFFFF`, hairline borders `#E8D9CC`, ink `#2B1B17`, muted `#7A5C52`, vermilion `#DB4A2B` (primary actions/alerts/tamper), slate teal `#2E5E6E` (Workspace 1: `VERIFIED BY CODE`), lead amber `#C97B1A` (Workspace 2: `LEAD`), and approved green `#3F7D58` (`APPROVED`).
   - Removed decorative `Sparkles` icons, stat-tile grids, heavy shadows, and hardcoded numbers.
2. **Two Workspaces, Six Pages (`LeftRail.tsx`, `CaseBar.tsx`, `WorkspaceHeader.tsx`, `App.tsx`)**:
   - Grouped the left rail into `Overview` (top), **EVIDENCE AND COURT PACKAGE** (`Evidence`, `Review and Report`), and **INVESTIGATION** (`Knowledge Graph`, `Reconstruction`, `Assistant`).
   - Made `CaseBar` single-line (`whitespace-nowrap`) with Case ID, `Synthetic case` tag, Integrity Seal (`Chain Intact` + Merkle root + `Verify`), `Run Pipeline`, compact `Status` popover, and quick jump search.
   - Added `WorkspaceHeader` at the top of every page with slate teal or amber workspace labeling.
3. **Shared Forensics Primitives & Linked Views (`HashChip.tsx`, `ExhibitChip.tsx`, `TierBadge.tsx`, `SourceViewer.tsx`, `store.ts`)**:
   - Added `HashChip` (`8…4` truncation, full-hash tooltip, one-click copy), evidence-bag `ExhibitChip`, and icon+text `TierBadge`.
   - Upgraded `SourceViewer` with `Re-hash now` server verification alongside browser WebCrypto re-hashing.
   - Added `selectedEntityId`, `selectedEventId`, and `selectedLocationId` in `store.ts` for linked selection across Graph, Reconstruction, and Assistant.
4. **Six Redesigned Pages**:
   - `OverviewPage.tsx`: Two side-by-side workspace panels with live metrics and one button each, plus a Next Steps list.
   - `EvidenceVaultPage.tsx`: Source-family filters, dense exhibit table, 4-tab detail drawer (`Chain of custody`, `Parse report`, `Authenticity`, `Mentions`), and browser WebCrypto re-hashing.
   - `ReviewAndReportPage.tsx`: Consolidated 3-step gate (`1. Review Queue` with `A/R/E/J/K` shortcuts and bulk approve; `2. Court Package` with approved-only preview, Section 63 draft marked `"DRAFT — HUMANS MUST SIGN"`, QR payload, ZIP/PDF download; `3. Verify & Trust Report` running real `verifier.py` + saved benchmark results).
   - `KnowledgeGraphPage.tsx`: Slim left filter column (search, node type, tier, strength, time range), full-height Cytoscape (`fcose`) canvas, and right `"Why this link"` / entity inspector with `"Ask about this"`.
   - `ReconstructionPage.tsx`: Three linked areas — `vis-timeline` event sequence (with original vs. corrected clock-offset timestamps), plain offline SVG Locations coordinate canvas (no map tiles or country/state outlines, impossible-travel flagged), and synchronized Scene Replay scrubber.
   - `AssistantPage.tsx`: Two-pane layout (conversation on left with starter chips and expandable `"How I got this"` / `"Explain"`; dedicated `"Evidence"` pane on right).
5. **Minimal Backend Additions (Required for Missing UI Endpoints)**:
   - `backend/app/api/evidence.py`: Added `mentions` list to `GET /api/evidence/{evidence_id}`.
   - `backend/app/api/review.py`: Added `approved_count` and `total_reviewable` to `GET /api/review/queue`, and added `POST /api/review/bulk`.
   - `backend/app/api/report.py`: Added `GET /api/report/preview` (approved items only + Section 63 draft) and `POST /api/report/verify` (executes `verifier/verifier.py` and returns real stdout/returncode).
6. **Before / After Visual Audit (`docs/UI_AUDIT.md`, `docs/ui/before/`, `docs/ui/after/`)**:
   - Captured 14 `before` screenshots and 12 `after` screenshots at `1440x900` and `1280x720`.
   - Before/after note: Replaced the 7-item flat cobalt rail, wrapping `CaseBar`, hardcoded `745 / 59 / 25 / 94.7%` Overview stat grid, and hardcoded `runVerifierDemo()` simulator with the 6-page two-workspace layout, live database metrics, offline SVG coordinate canvas, synchronized Scene Replay, and real `verifier.py` execution.

## Why
Investigators and courts need an immediate visual boundary between provable/human-approved material (slate teal) and AI-assisted investigative leads (amber), with Review and Report acting as the sole gate between them. Removing CDN fonts, hardcoded numbers, and decorative clutter ensures strict offline operation, honest forensic reporting, and fast keyboard-driven review.

## How to explain this to judges in three sentences
PRAMAAN separates the UI into two color-coded workspaces—slate teal for deterministic, court-ready evidence and amber for AI-assisted investigation leads—connected by a single human-gated Review and Report workflow. Every metric, graph link, timeline step, and assistant citation traces back to SHA-256 hashed exhibits through clickable evidence-bag chips and a live Source Viewer. The platform runs 100% offline with locally bundled fonts, an offline coordinate canvas without external map tiles, and a real standalone `verifier.py` audit.

## What is still weak
- In `ReconstructionPage.tsx`, the offline SVG coordinate canvas uses a linear lat/lon bounding-box projection rather than an equirectangular cosine-corrected projection (adequate for regional distances, slightly stretched at extreme latitudes).
- The court package QR code currently renders a `QrCode` icon alongside the JSON payload string rather than a scannable matrix SVG generator.

## How I tested it
1. Built the TypeScript + Vite production bundle (`npm --prefix frontend run build`) — exited 0 with all `@fontsource` fonts bundled locally.
2. Ran the full backend test suite (`.venv/bin/pytest -q`) — **42 passed in 4.90s**.
3. Seeded the synthetic dataset (`scripts/seed_demo.py`) and captured live `after` screenshots of all 6 pages at `1440x900` and `1280x720` in `docs/ui/after/` using headless Chrome.
