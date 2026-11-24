# PRAMAAN Test Slowness & Hang Investigation Report

**Plain-English report: why the test suite previously hung for over an hour, what we measured, what we fixed, and the real before/after timings.**

---

## 1. Test Inventory (Measured via `pytest --collect-only -q`)

All tests live in one folder (`tests/`): **54 tests** before fixes (**55 tests** after adding the explicit `@pytest.mark.llm` live-Ollama test), spread across 11 files:

| File | Tests |
| :--- | ---: |
| `tests/test_phase0_scaffold.py` | 3 |
| `tests/test_phase1_hardening.py` | 20 |
| `tests/test_phase1_integrity.py` | 6 |
| `tests/test_phase2_parsers.py` | 4 |
| `tests/test_phase2b_ps3_engine.py` | 3 |
| `tests/test_phase2c_assistant.py` | 1 *(+1 `llm`-marked test added)* |
| `tests/test_phase3_extraction.py` | 3 |
| `tests/test_phase4_correlation.py` | 1 |
| `tests/test_phase4_offline_and_explain.py` | 4 |
| `tests/test_phase4_unit_pyramid.py` | 8 |
| `tests/test_phase5_anomalies.py` | 1 |
| **Total (`tests/`)** | **54** *(55 with `llm` test)* |

---

## 2. Diagnosis: Root Causes (Grouped with File & Line Evidence)

### (a) Waiting on AI model / HTTP calls (Timed out >60s!)
- **Evidence:**
  - `backend/app/assistant/engine.py` line 198 called `OllamaProvider().is_available()` on **every single call** to `ask_assistant()`.
  - `backend/app/ai/provider.py` line 44 called `httpx.get("http://localhost:11434/api/tags", timeout=1.5)` with no fast-path for tests and no explicit connect timeout.
  - `scripts/eval_assistant.py` line 67 loops over all **30 questions** in `tests/assistant_eval.json`, triggering 30 sequential TCP connections to closed port `11434`. On Windows, `localhost` resolves to both `::1` and `127.0.0.1`, taking ~2 seconds per refused connection → **60+ seconds** in a single test!
  - `backend/app/api/system.py` line 29 also probed `http://localhost:11434/api/tags` on every `/api/system/capabilities` request.
- **Real timeout stack trace captured (`--timeout=60`):**
  ```text
  tests/test_phase2c_assistant.py::test_assistant_eval_metrics +++++++++++ Timeout +++++++++++
    File "tests\test_phase2c_assistant.py", line 9, in test_assistant_eval_metrics
      metrics = run_eval()
    File "scripts\eval_assistant.py", line 67, in run_eval
      resp = ask_assistant(conn, item["question"], session_id=f"eval_{item['id']}")
    File "backend\app\assistant\engine.py", line 198, in ask_assistant
      model_available = ollama.is_available()
    File "backend\app\ai\provider.py", line 44, in is_available
      r = httpx.get(f"{self.host}/api/tags", timeout=1.5)
    File "...\socket.py", line 838, in create_connection
      sock.connect(sa)
  ```

### (b) Very large generated files
- **Evidence:** `tests/test_phase1_hardening.py` lines 165–175 (`test_kat_streaming_vs_oneshot_large_file_and_os_tool`) generated a **200 MB** file (`200 * 1024` iterations of 1 KB writes) and hashed it 3 times (streaming, one-shot, and `certutil -hashfile`).

### (c) Property-style tests without configurable example budget
- **Evidence:** `tests/test_phase1_hardening.py` line 319 (`test_property_single_byte_mutation_fails_verification`) ran only 1 unseeded random check; updated to deterministic seeded `max_examples=25` by default and `100` under `--run-slow`.

### (d) Full-pipeline runs repeated per test + Python `trace.Trace` 20x–50x slowdown
- **Evidence:**
  - `scripts/run_all_checks.py` line 69–70 wrapped the entire pytest suite in Python's stdlib `trace.Trace(count=1, trace=0)`, which executes a Python hook on every single bytecode line across stdlib and third-party libraries (NumPy, Pillow, pdfplumber, ReportLab), slowing execution by 20x–50x.
  - Full dataset ingestion + analysis was repeated across `test_phase2b_ps3_engine.py` (2x), `test_phase2c_assistant.py` (1x), `test_phase4_unit_pyramid.py` (4x), `test_phase5_anomalies.py` (1x), and `scripts/run_all_checks.py` (3x).

### (e) Unclosed SQLite connections, shared DB/evidence paths, and long busy timeout
- **Evidence:**
  - `backend/app/db.py` line 249 used `sqlite3.connect(str(db_path), timeout=15.0)` with no `PRAGMA busy_timeout`.
  - `tests/test_phase2b_ps3_engine.py` lines 172–173, `tests/test_phase4_offline_and_explain.py` line 98, and `tests/test_phase4_unit_pyramid.py` lines 207–208, 244, 283 opened SQLite connections without closing them in `finally` blocks.
  - `tests/test_phase1_integrity.py`, `test_phase2_parsers.py`, `test_phase3_extraction.py`, `test_phase4_correlation.py`, and `test_phase5_anomalies.py` wrote test DBs directly into `backend/case_data/` and evidence files into `backend/evidence_store/`.

### (f) Windows `TestClient` / `socket.socketpair()` infinite deadlock in restricted environments
- **Evidence:** Inside a restricted Windows sandbox (where loopback sockets are blocked by policy), `starlette.testclient.TestClient(app)` in `tests/test_phase4_offline_and_explain.py` line 64 (`test_network_guard_blocks_external_and_counts`) and `tests/test_phase4_unit_pyramid.py` line 317 (`test_scene_endpoint_determinism`) hung **forever** (no timeout before `pytest-timeout` was installed):
  ```text
  tests/test_phase4_offline_and_explain.py::test_network_guard_blocks_external_and_counts +++ Timeout +++
    File "...\asyncio\proactor_events.py", line 787, in _make_self_pipe
      self._ssock, self._csock = socket.socketpair()
    File "...\socket.py", line 647, in socketpair
      ssock, _ = lsock.accept()
  ```
  Additionally, `test_phase4_offline_and_explain.py` line 63 did not use `with TestClient(app) as client:` for guaranteed portal teardown.

### (g) Model downloads potentially attempted offline
- **Evidence:** `backend/app/extract/names.py` lines 89–92 loads `transformers.pipeline("ner", model="ai4bharat/IndicNER")` when `USE_INDIC_NER=1`. Tests did not set `HF_HUB_OFFLINE=1` or `TRANSFORMERS_OFFLINE=1`.

---

## 3. What Changed

1. **Global pytest config & markers (`pytest.ini`, `tests/conftest.py`):**
   - Set global `timeout = 60`, `testpaths = tests`, and registered markers `slow`, `llm`, `integration`.
   - Added `--run-slow` and `--run-llm` CLI flags; `slow` and `llm` tests are skipped by default.
   - Set `HF_HUB_OFFLINE=1`, `TRANSFORMERS_OFFLINE=1`, and `PRAMAAN_FAKE_LLM=1` (unless `--run-llm` is passed) automatically in tests.
   - Added session-scoped `synthetic_dataset_dir` fixture (one temporary copy per test session) and autouse `isolated_storage_env` fixture so every test uses its own temporary DB, evidence store, and ELA directory.
2. **Fast-fail network & SQLite timeouts (`backend/app/ai/provider.py`, `backend/app/api/system.py`, `backend/app/db.py`):**
   - All Ollama HTTP calls use explicit `httpx.Timeout(..., connect=2.0)` and fail fast to `DeterministicProvider`.
   - `PRAMAAN_FAKE_LLM=1` bypasses Ollama network probes immediately in tests.
   - SQLite `connect(..., timeout=3.0)` + `PRAGMA busy_timeout = 3000;`.
3. **Configurable heavy test sizes & guaranteed teardown (`tests/`, `scripts/eval_assistant.py`):**
   - `test_kat_streaming_vs_oneshot_large_file_and_os_tool` hashes **32 MB** by default and **200 MB** under `--run-slow`.
   - `test_property_single_byte_mutation_fails_verification` runs **25** seeded mutation checks by default and **100** under `--run-slow`.
   - Closed all SQLite connections and `TestClient` portals in `try/finally` / `with` blocks.
   - Isolated `scripts/eval_assistant.py` storage in a temporary directory.
4. **Two-mode verification runner (`scripts/run_all_checks.py`):**
   - Replaced slow `trace.Trace` with C-speed `pytest-cov` in `--full` mode.
   - Added `--fast` (target <2 min) and `--full` modes, per-stage progress + elapsed time, global timeout, and a guaranteed summary table even on failure or timeout.

---

## 4. Before vs. After Timings (Real Measured Outputs)

| Run | Before | After |
| :--- | :--- | :--- |
| Full pytest suite (`tests/`) | **> 1 hour (hung forever)**; with `--timeout=60`: **TIMEOUT at 60s** on `test_assistant_eval_metrics` (and `test_network_guard_blocks_external_and_counts` in sandbox) | **47.56s** (`54 passed, 1 skipped` in `--fast`) |
| `scripts/eval_assistant.py` (30 questions) | **> 60s (timed out)** waiting on 30 Ollama probes | **4.30s** (`--fast`) / **5.55s** (`--full`) |
| `python scripts/run_all_checks.py --fast` | Did not exist (single slow mode using `trace.Trace`) | **76.28s total** (all stages PASS, `GT=15/15`) |
| `python scripts/run_all_checks.py --full` | **> 1 hour** (`trace.Trace` + hangs) | **232.38s total** (3m 52s — pytest `--run-slow` + coverage + `npm run build` offline check + determinism + verifier + GT 15/15 + assistant eval, all PASS) |

### Real `--fast` Output
```text
======================================================================================
PRAMAAN VERIFICATION SUMMARY  |  mode=--fast  |  total=76.28s
======================================================================================
Stage                                Status        Time  Detail / First Failure
--------------------------------------------------------------------------------------
Pytest (fast)                        PASS        53.91s  54 passed, 1 skipped in 47.56s
Offline End-to-End Check             SKIPPED      0.00s  skipped in --fast (covered by test_phase4_offline_and_explain; run --full for npm build)
Pipeline Determinism                 PASS        17.77s  2 independent runs identical
Verifier Cross-Check                 PASS         0.00s  intact & tampered agreed
Ground-Truth Recall (GT-01..GT-15)   PASS         0.00s  15/15 (100.0%)
Assistant Eval (synthetic)           PASS         4.30s  citation_precision=0.682, keyword_recall=0.5, refusal=1.0
======================================================================================
```

### Real `--full` Output
```text
======================================================================================
PRAMAAN VERIFICATION SUMMARY  |  mode=--full  |  total=232.38s
======================================================================================
Stage                                Status        Time  Detail / First Failure
--------------------------------------------------------------------------------------
Pytest (full)                        PASS       128.03s  54 passed, 1 skipped in 119.44s (0:01:59)
Offline End-to-End Check             PASS        75.19s  
Pipeline Determinism                 PASS        23.14s  2 independent runs identical
Verifier Cross-Check                 PASS         0.00s  intact & tampered agreed
Ground-Truth Recall (GT-01..GT-15)   PASS         0.00s  15/15 (100.0%)
Assistant Eval (synthetic)           PASS         5.55s  citation_precision=0.682, keyword_recall=0.5, refusal=1.0
======================================================================================
```
