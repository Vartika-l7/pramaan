# Phase 4 Report: Offline Guarantee, Test Pyramid, and AI Explainability

## What changed
1. **Offline Network Guard & Status Counter (`backend/app/network_guard.py`, `backend/app/main.py`, `backend/app/api/system.py`, `frontend/src/components/case/CaseBar.tsx`)**:
   - Added a socket-level network guard enabled automatically under `OFFLINE=1` (and in tests) that blocks and counts any attempt to open a socket to a non-local address (`OfflineNetworkError`), while permitting loopback (`127.0.0.1`, `::1`, `localhost`, `AF_UNIX`).
   - Wired `/api/system/capabilities` (`network_use.outbound_connections`) and the `CaseBar` Status popover to display `"Network use: 0 outbound connections"` from the live counter.
2. **Offline Verification & Air-Gap Bundle (`scripts/check_offline.py`, `scripts/make_offline_bundle.py`, `docs/OFFLINE_INSTALL.md`, `requirements.txt`)**:
   - Created `scripts/check_offline.py`: builds the frontend, scans source and `frontend/dist` for any runtime external URL fetches (excluding XML namespaces and bundled third-party library license/doc strings), verifies `@fontsource` fonts (`source-serif-4`, `ibm-plex-sans`, `ibm-plex-mono`) and assets are locally bundled, runs the full forensic pipeline + standalone `verifier.py` under the Network Guard, and exits non-zero on any violation.
   - Created `scripts/make_offline_bundle.py` and `docs/OFFLINE_INSTALL.md` to produce a USB-ready air-gap bundle (`wheels/`, `frontend_dist/`, `app/`, `install_offline.py`, `BUNDLE_SHA256SUMS.txt`) and document USB copying and graceful offline degradation for optional Ollama models, Tesseract OCR language packs, IndicNER, and GeoIP DBs.
   - Added `pytz>=2024.1` to `requirements.txt` after the clean-venv offline install test revealed `backend/app/parsers/whatsapp.py` depended on it transitively.
3. **Test Pyramid, Determinism Fixes & Coverage (`scripts/run_all_checks.py`, `tests/test_phase4_unit_pyramid.py`, `tests/test_phase4_offline_and_explain.py`, `docs/coverage.txt`)**:
   - Made pipeline IDs deterministic across repeated runs in `ingest/service.py`, `ingest/registry.py`, `extract/resolve.py`, `timeline/anomalies.py`, `authenticity/exif.py`, `authenticity/statement_checks.py`, `verify/claim_verifier.py`, `ai/provider.py`, `parsers/image.py`, and `parsers/cctv.py`.
   - Fixed `ingest/service.py` to verify and repair content-addressed files if corrupted on disk, and fixed `api/report.py` (`merkle_root, _` tuple unpacking and `episodes` query).
   - Built unit tests for all 13 parsers, all extractors, anomaly detectors, verifier rules (`V1`, `V2`, `V4`, `V5`), spatial/temporal logic (haversine, impossible travel, clock offset apply/reverse, sequence/scene determinism), verifier vs. backend cross-check (intact & tampered), full pipeline determinism, and `GT-01`..`GT-15` recall.
   - Created single-command `scripts/run_all_checks.py` and saved backend line coverage to `docs/coverage.txt` (**62.0%**, 4506/7263 statements).
4. **Tamper-Evident AI Run Records & Explainability (`backend/app/ai/run_records.py`, `backend/app/db.py`, `backend/app/ai/provider.py`, `backend/app/assistant/engine.py`, `backend/app/verify/challenger.py`, `frontend/src/components/ui/ExplainPanel.tsx`, `frontend/src/pages/AssistantPage.tsx`, `frontend/src/pages/ReviewAndReportPage.tsx`, `frontend/src/pages/KnowledgeGraphPage.tsx`)**:
   - Added `ai_runs` table and `claims.ai_run_id` column; every AI call (claim drafting, assistant Q&A, lead suggestion, challenger objections) records timestamp, task, model name/version, `{"temperature": 0, "seed": 42}`, exact prompt, input record IDs, raw output, verifier result, and appends its SHA-256 (`AI_RUN_RECORDED` / `AI_VERIFIER_RECORDED`) to the hash-chained `custody_log`. Also fixed `OllamaProvider` `"stream": False`.
   - Built the 4-part expandable `ExplainPanel` on every AI-generated claim, assistant answer, lead, and objection: (1) What the model saw (record IDs + exhibit chips), (2) What the model said (raw + custody SHA-256), (3) What the verifier kept and removed, and (4) Who approved it (`reviewer at ts` or `"not yet approved"`).
   - Upgraded Graph `"Why This Link"` to display explicit deterministic basis labels and `"Deterministic strength: X% (feature-derived, never model-stated)"`, and upgraded the Trust Report in Review and Report to display deterministic test coverage alongside measured `synthetic dataset` evaluation metrics.

## Why
A court-admissible digital forensics platform cannot rely on external networks, non-reproducible AI outputs, or unexplained confidence scores. Enforcing a socket-level offline guard, bundling all assets/wheels, proving pipeline determinism and 15/15 ground-truth recall through a single verification command, and hashing every AI run into the custody log with a 4-part Explain panel ensures investigators and judges can independently audit every claim from raw exhibit to court report.

## How to explain this to judges in three sentences
PRAMAAN enforces strict offline operation with a socket-level Network Guard (`0 outbound connections`), locally bundled fonts and Python wheels, and an air-gap USB installer verified by SHA-256 checksums. A single verification command proves our deterministic evidence correlation, knowledge graph, event sequence, and crime scene reconstruction engines are reproducible across runs and detect all 15/15 planted ground-truth facts on the synthetic dataset. Every AI-generated claim, assistant answer, lead, and objection is hashed into the tamper-evident custody log and exposes a 4-part Explain panel showing what the model saw, what it said raw, what the deterministic verifier kept or removed, and who approved it.

## What is still weak
- Overall backend statement coverage measured by `scripts/run_all_checks.py` is **62.0%** (4506/7263 statements); fastAPI route error branches and optional Ollama/Tesseract/WeasyPrint branches have lower coverage when those optional binaries are absent.
- `assistant_eval_results.json` in deterministic mode remains at `citation_precision=0.591`, `keyword_recall=0.227`, and `unanswerable_refusal_rate=0.625` on the 30-question synthetic eval set.
- `scripts/make_offline_bundle.py` downloads platform-specific wheels for the build host OS/architecture (`macosx_11_0_arm64` here); targeting a different air-gap OS requires running `make_offline_bundle.py` on that matching OS/architecture.

## How I tested it
1. **Single-command full verification (`python scripts/run_all_checks.py`)**:
```text
========================================================================
PRAMAAN FULL VERIFICATION & TEST PYRAMID
========================================================================

[1/6] Running pytest test pyramid & measuring backend coverage...
53 passed, 1 warning in 76.18s (0:01:16)

========================================================================
PRAMAAN ONE-PAGE VERIFICATION SUMMARY (SYNTHETIC DATASET)
========================================================================
1. Test Pyramid (pytest)       : PASS (backend coverage: 62.0% (4506/7263 statements))
2. Offline Check               : PASS (0 outbound connections)
3. Pipeline Determinism        : PASS (identical IDs, hashes, edges, anomalies, claims, episodes, scenes)
4. Verifier Cross-Check        : PASS (intact & tampered agreed)
5. Ground-Truth Recall         : 15/15 (100.0%) [All GT-01..GT-15 detected]
6. Assistant Eval (synthetic)  : citation_precision=0.591, keyword_recall=0.227, unanswerable_refusal_rate=0.625, verifier_removed_share=0.0
7. Coverage Report Saved       : docs/coverage.txt
========================================================================
```

2. **Clean virtual environment air-gap install test (`pip install --no-index --find-links`)**:
   - Downloaded wheels from `requirements.txt`, built an offline bundle with `scripts/make_offline_bundle.py`, created a fresh virtual environment (`/tmp/pramaan_clean_venv_test`), installed strictly via `pip install --no-index --find-links /tmp/pramaan_wheels -r requirements.txt`, and ran `OFFLINE=1 /tmp/pramaan_clean_venv_test/bin/python -m pytest -q` on `test_phase4_offline_and_explain.py`, `test_phase4_unit_pyramid.py`, and `test_phase1_integrity.py`: **17 passed, 1 warning in 6.12s**.
