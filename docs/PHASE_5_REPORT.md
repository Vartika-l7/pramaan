# Phase 5 Report: Finishing and Submission Readiness (`docs/PHASE_5_REPORT.md`)

## What changed
1. **End-to-End Demo Flow Fixes (`backend/app/api/analyze.py`, `backend/app/api/assistant.py`, `backend/app/assistant/engine.py`, `backend/app/report/render.py`, `backend/app/main.py`)**:
   - Wired AI claim drafting (`get_ai_provider()` + `record_ai_run()`) and deterministic verification (`verify_claims()`) into `execute_full_pipeline()` so clicking **Run Pipeline** populates the Review Queue automatically.
   - Enforced the human-approval gate inside `backend/app/report/render.py`: `generate_court_report_pdf()` now includes only `status = 'APPROVED'` claims, edges, and anomalies instead of `IN ('APPROVED', 'VERIFIED')` or unapproved anomalies.
   - Fixed `_deterministic_plan()` in `backend/app/assistant/engine.py` so unanswerable questions mentioning a person name (e.g., `"What is the flight number for Vikram's trip to Dubai?"`) fall through to FTS5 `search_text()` and refuse cleanly (`100%` unanswerable refusal rate on `tests/assistant_eval.json`).
   - Updated `/api/assistant/promote` to enforce Rule V4 (rejecting empty `refs` with HTTP 400) and run `verify_claims()` so valid promoted answers enter the Review Queue as `VERIFIED`.
   - Added SPA static serving fallback in `backend/app/main.py` when `frontend/dist/` is present, so a single `OFFLINE=1 uvicorn` process serves both the API and UI offline.
2. **UI Demo Polish (`frontend/src/pages/*.tsx`, `frontend/src/components/case/CaseBar.tsx`, `frontend/vite.config.ts`)**:
   - `EvidenceVaultPage.tsx`: Added recursive folder drag-and-drop (`webkitGetAsEntry`), sequential **Upload Folder** (`webkitdirectory`) input, complete 7-family filters (`cctv_index`, `cctv_video`, `cloud_location`, `cloud_activity`, `social_telegram`, `social_generic`), side-by-side **Original vs. ELA Heatmap** viewer for edited screenshots (`imageData.anomaly`), and row-by-row bank statement arithmetic table highlighting `FAIL` rows in vermilion (`statementData.has_arithmetic_mismatch`).
   - `KnowledgeGraphPage.tsx`: Fixed `NODE_TYPES` (`ACCOUNT`, `EMAIL_ADDRESS`, `EXHIBIT`, `URL`), preserved 1-hop neighborhood and matching `reason_text` edges during search, and added clickable **Matching Correlation Links** in the right Inspector.
   - `ReconstructionPage.tsx`: Fixed `sceneData.presence` (replacing `spatial_observations`), `IMPOSSIBLE_TRAVEL` uppercase matching, `currentStep.place_name`/`text`, and added **Sequence Anomalies & Clock Offsets**, **Generated Episodes**, and an **Anomalies & Clock Offsets Only** filter toggle.
   - `CaseBar.tsx` & `OverviewPage.tsx`: Renamed button to **Verify now** and updated `SOURCE_FAMILY_MAP`.
3. **Scripts, Hygiene & Packaging (`scripts/`, `requirements.txt`, `.gitignore`, `docs/SCOPE.md`, `backend/app/integrity/signer.py`)**:
   - Removed tracked runtime artifacts and demo private keys (`backend/keys/`, `backend/case_data/`, `backend/evidence_store/`) from git tracking and added them (plus `offline_bundle/`, `release/`, `frontend/dist/`) to `.gitignore`. Documented in `signer.py` and `README.md` that first-run Ed25519 keys are demo keys.
   - Removed 7 dead unrouted frontend page files, empty `frontend/src/components/command/`, unused `cmdk` from `frontend/package.json`, and unused Python deps (`pandas`, `faker`, `jinja2`, `pyhanko`) from `requirements.txt`; logged every removal in `docs/SCOPE.md`. Pinned all Python and npm dependency versions.
   - Configured Vite `manualChunks` and silenced `exifread` INFO/WARNING noise on PNGs (`backend/app/parsers/image.py`).
   - Fixed `sys.path` in `scripts/eval_assistant.py` and `scripts/tamper_demo.py` (plus `chmod(0o644)` before tampering read-only exhibits), expanded `scripts/benchmark.py` to all 20 evidence files and all 15 `GT` checks + `time_to_first_graph_sec` + `full_analysis_time_sec`, updated `scripts/make_offline_bundle.py` & `scripts/check_offline.py` so pre-built bundles run `run_all_checks.py` with zero npm build, and added `scripts/make_release.py`.
4. **Submission Documentation & Release**:
   - Wrote `README.md`, `docs/DEMO_SCRIPT.md`, `docs/PERFORMANCE.md`, `docs/ARCHITECTURE.md`, `docs/API.md`, `docs/DEPLOYMENT_ROADMAP.md`, `docs/DATASET.md`, updated `docs/LIMITS.md`, and completed `docs/FINAL_CHECKLIST.md`.

## Why
A hackathon prototype only survives live judging if a fresh offline checkout or air-gap USB bundle installs cleanly on the first attempt, every UI panel matches the backend JSON schema with zero dead views or hardcoded stats, and the cryptographic custody and human-approval guarantees hold under real inspection and tampering.

## How to explain this to judges in three sentences
PRAMAAN is now a clean, reproducible `v1.0` submission that installs strictly offline from a SHA-256-verified USB bundle (`0 outbound connections`) and generates its demo Ed25519 keys on first run without storing private keys in git. Every step of the live demo—from folder ingest, cross-source UPI/IP correlation, 6h 14m silence-gap/clock-offset/impossible-travel reconstruction, ELA and bank-math checks, to keyboard review and standalone `verifier.py` verification—runs deterministically against real SQLite data. Any byte-level tampering in the exported package or live evidence store immediately fails verification and turns the Integrity Seal vermilion, while unapproved Investigation leads are strictly blocked from entering the court report PDF.

## What is still weak
- **Interactive Chrome Browser Attachment:** Chrome remote debugging (`DevToolsActivePort`) was not enabled in the host Chrome profile during this session, so interactive mouse/keyboard clicks in the live Chrome DOM could not be executed via `chrome_devtools` MCP; instead, the TypeScript compiler (`tsc --noEmit`), Vite production build, static asset audit (`check_offline.py`), and a full end-to-end HTTP walkthrough against the live `OFFLINE=1` FastAPI server (`demo_verify.py`) verified every backend/SPA route.
- **Platform-Specific Wheels:** The offline bundle built on this machine contains `macosx_11_0_arm64` / `macosx_14_0_arm64` wheels; targeting Windows or Linux air-gapped workstations requires running `scripts/make_offline_bundle.py` on a matching OS/architecture (or downloading target-platform wheels).
- **Assistant Keyword Recall:** In deterministic mode without an Ollama LLM, `keyword_recall` is `0.500` on the 30-question synthetic evaluation set (with `1.000` unanswerable refusal rate and `0.682` citation precision).

## How I tested it
1. **Full Workspace Verification (`OFFLINE=1 .venv/bin/python scripts/run_all_checks.py`)**:
```text
54 passed, 1 warning in 74.39s (0:01:14)

========================================================================
PRAMAAN ONE-PAGE VERIFICATION SUMMARY (SYNTHETIC DATASET)
========================================================================
1. Test Pyramid (pytest)       : PASS (backend coverage: 62.0% (4568/7365 statements))
2. Offline Check               : PASS (0 outbound connections)
3. Pipeline Determinism        : PASS (identical IDs, hashes, edges, anomalies, claims, episodes, scenes)
4. Verifier Cross-Check        : PASS (intact & tampered agreed)
5. Ground-Truth Recall         : 15/15 (100.0%) [All GT-01..GT-15 detected]
6. Assistant Eval (synthetic)  : citation_precision=0.682, keyword_recall=0.5, unanswerable_refusal_rate=1.0, verifier_removed_share=0.0
7. Coverage Report Saved       : docs/coverage.txt
========================================================================
```
2. **Fresh-Install Offline Bundle Test (`/tmp/pramaan_fresh_install_test/offline_bundle`)**:
```text
[PASS] Verified 486 bundle files via SHA-256.
Successfully installed ... (63 wheels via --no-index --find-links)
[PASS] Offline install complete.
53 passed, 1 warning in 106.73s (0:01:46)
1. Test Pyramid (pytest)       : PASS (backend coverage: 62.0% (4563/7365 statements))
2. Offline Check               : PASS (0 outbound connections)
3. Pipeline Determinism        : PASS (identical IDs, hashes, edges, anomalies, claims, episodes, scenes)
4. Verifier Cross-Check        : PASS (intact & tampered agreed)
5. Ground-Truth Recall         : 15/15 (100.0%) [All GT-01..GT-15 detected]
6. Assistant Eval (synthetic)  : citation_precision=0.682, keyword_recall=0.5, unanswerable_refusal_rate=1.0, verifier_removed_share=0.0
7. Coverage Report Saved       : docs/coverage.txt
```
3. **End-to-End Live Offline Server Demo & Tamper Test (`demo_verify.py` + `scripts/tamper_demo.py`)**:
   - Clean DB upload of 20 exhibits (`0.14s`), `POST /api/analyze` (`1.83s`), Knowledge Graph (`202` nodes, `263` edges, `vikram.alpha@okaxis` `1.0` + `203.0.113.45` `0.95`), Reconstruction (`16` episodes, `ANOMALY_CHAT_GAP`, `ANOMALY_OUT_OF_ORDER`, `IMPOSSIBLE_TRAVEL`, CCTV `+252s` offset), Evidence authenticity (`PixelMod Editor Pro v2.4` + ELA heatmap; Bank row `#10` `220000` vs `190000`), Assistant (`Q1`, `Q2`, `Q3` refused, promote verified), Review & Report (`PASS` from `verifier.py`), `scripts/tamper_demo.py` (`FINAL VERDICT: TAMPERING OR CORRUPTION DETECTED [FAILED]`, `EX-001 (bank_statement_meera.pdf): HASH MISMATCH!`), live file tamper -> `/api/integrity/verify` returned `intact: False`, `failed_exhibit: EX-001`, and `outbound_connections: 0`.
4. **Performance Benchmark (`scripts/benchmark.py`, `synthetic dataset, this machine`)**:
   - `Hash Throughput: 1066.5 MB/s (0.96 s/GB)`
   - `Parse Throughput: 709.2 WhatsApp messages/sec | 763.5 total events/sec (760 events across 20 files in 0.995s)`
   - `Time to First Graph: 1.252s (170 nodes, 139 edges)`
   - `Full Analysis Time (demo case): 1.402s`
   - `Planted Forensic Fact Detection: 15/15 (100.0%)`
