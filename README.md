# PRAMAAN — Digital Evidence Correlation and Crime Reconstruction Engine

PRAMAAN is an offline-first, AI-assisted digital forensics prototype built for **Problem Statement 3 (Digital Evidence Correlation and Crime Reconstruction Engine)**. It correlates heterogeneous digital evidence across mobile devices, social media, CCTV footage metadata, cloud services, financial records, emails, and network logs while preserving a cryptographic chain of custody and requiring explicit human approval before any finding enters a court report.

> **Synthetic Dataset Notice:** All files in `data/case_alpha/` belong to a fictional demonstration case (`PRM-2026-0042`, *Alpha Wealth Club*). All persons, phone numbers, bank accounts, UPI IDs, email addresses, and IP addresses (`203.0.113.0/24`) are synthetic and fictional.

---

## Core Deliverables Implemented
1. **Evidence Correlation Engine** — 10 pluggable deterministic correlators (`backend/app/correlate/edges.py`) + mule funnel pattern detector (`patterns.py`), producing `LEAD` links with feature-derived strength formulas.
2. **Knowledge Graph Generation Framework** — Deterministic SHA-256 node/edge IDs, Cytoscape (`fcose`) visual graph, `"Why this link"` inspector, and JSON / GraphML export (`GET /api/graph/export`).
3. **Crime Reconstruction Dashboard** — Editorial two-workspace UI (`Evidence and Court Package` in midnight ink & deep teal; `Investigation` in slate blue & muted amber; offline-bundled `DM Serif Display`, `Plus Jakarta Sans`, and `JetBrains Mono`), separated by a single human-gated `Review and Report` admissibility workflow.
4. **Automated Event-Sequence Generator** — Deterministic timeline segmentation into titled episodes (`EP-001`…), preserving original vs. clock-offset-corrected timestamps and exporting JSON / Markdown.
5. **Interactive Visual Investigation Platform** — Linked views across Overview, Evidence Vault, Knowledge Graph, Reconstruction (Timeline + plain offline Coordinate Canvas + Scene Replay), Assistant, and Review and Report.

---

## Prerequisites
- **Required:** Python **3.11 or 3.12** (`venv` + `pip`)
- **Required for frontend UI:** Node.js 18+ and `npm` (run via `python scripts/dev.py` or `cd frontend && npm run dev`; production build via `cd frontend && npm run build`).

### Optional Components (Degrade Gracefully When Absent)
| Component | Purpose | Behavior When Absent |
| :--- | :--- | :--- |
| **Ollama** (`llama3.2`, `mistral`) | Local offline LLM drafting & Q&A | Falls back automatically to `DeterministicProvider` / `"model unavailable, deterministic mode"`. |
| **Tesseract OCR** (`eng`, `hin`) | Text extraction from screenshots | `ImageParser` still records SHA-256, pHash, EXIF, dimensions, and ELA heatmaps (`ocr_status: "UNAVAILABLE"`). |
| **IndicNER (`transformers`)** | Transformer NER (`USE_INDIC_NER=1`) | Uses built-in regex, honorific stripping, Devanagari transliteration, and RapidFuzz matching. |
| **Offline GeoIP `.mmdb`** | IP geolocation (`GEOIP_DB_PATH`) | `lookup_ip_location()` explicitly returns `"location unknown"`. |

---

## Running PRAMAAN (Ports & Commands)

PRAMAAN uses a single clean split between backend API and frontend UI:

| Service | Address / Port | Folder | Command |
| :--- | :--- | :--- | :--- |
| **Backend API** (FastAPI / Uvicorn) | `http://127.0.0.1:8000` (`/api/*`, `/api/health`, `/docs`) | repo root | `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000` |
| **Frontend UI** (Vite dev server) | `http://localhost:5173` (proxies `/api` → `:8000`) | `frontend/` | `cd frontend && npm run dev` |
| **Both together** (Recommended) | Backend `:8000` + Frontend `:5173` | repo root | `python scripts/dev.py` |
| **Check running status & ports** | Probes `:8000`, `:5173`, `/api/health`, `/` | repo root | `python scripts/status.py` |
| **Frontend production build** | Outputs static assets to `frontend/dist/` | `frontend/` | `cd frontend && npm run build` (preview with `npm run preview`) |

> **Important:** The backend on port `8000` serves **ONLY** `/api/*` endpoints (plus a small JSON redirect notice at `/`). Always open **`http://localhost:5173`** in your browser for the UI during development.

### 1. Air-Gapped / Offline Bundle Install (All OSes, Zero Internet)
If you received an `offline_bundle/` directory (built via `python scripts/make_offline_bundle.py`), follow [`docs/OFFLINE_INSTALL.md`](docs/OFFLINE_INSTALL.md):

1. Verify bundle checksums:
   - **macOS / Linux:** `cd offline_bundle && shasum -a 256 -c BUNDLE_SHA256SUMS.txt`
   - **Windows (PowerShell):**
     ```powershell
     cd offline_bundle
     python -c "import hashlib, pathlib; bad=[p for line in open('BUNDLE_SHA256SUMS.txt') for h,p in [line.strip().split('  ',1)] if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h]; print('OK' if not bad else f'FAILED: {bad}')"
     ```
2. Install strictly offline using local wheels:
   ```bash
   python install_offline.py --venv .venv
   ```
3. Run the backend from `offline_bundle/app/`:
   - **macOS / Linux:**
     ```bash
     cd app
     OFFLINE=1 .venv/bin/python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
     ```
   - **Windows (PowerShell):**
     ```powershell
     cd app
     $env:OFFLINE="1"
     ..\.venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
     ```

### 2. Source Install — macOS & Linux
```bash
# 1. Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# 2. Install pinned Python dependencies
python -m pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend && npm ci && cd ..

# 4. Start backend (:8000) and frontend (:5173) together
OFFLINE=1 python scripts/dev.py
```

### 3. Source Install — Windows (PowerShell)
```powershell
# 1. Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 2. Install pinned Python dependencies
python -m pip install -r requirements.txt

# 3. Install frontend dependencies
cd frontend
npm ci
cd ..

# 4. Start backend (:8000) and frontend (:5173) together
$env:OFFLINE="1"
python scripts/dev.py
```

To build the production frontend bundle (`frontend/dist/`):
```bash
cd frontend && npm run build
# Preview the production build locally (default port 4173):
npm run preview
```

---

## Verification, Demo & Benchmark Commands
All scripts are cross-platform Python scripts:
```bash
# Fast verification (default pytest suite + determinism + verifier cross-check + 15/15 GT recall + assistant eval; ~76s)
python scripts/run_all_checks.py --fast

# Full verification (adds --run-slow 200 MB hash & 100 mutation checks, backend coverage, and full offline frontend build)
python scripts/run_all_checks.py --full

# Run pytest directly (60s global timeout per test; excludes slow & live-LLM tests by default)
python -m pytest
python -m pytest --run-slow          # include 200 MB hashing & extended mutation tests
python -m pytest --run-llm           # include live local Ollama connectivity test

# Run strict offline check (0 outbound connections, bundled fonts/assets)
OFFLINE=1 python scripts/check_offline.py

# Seed synthetic dataset (optional; or upload data/case_alpha/ via the Evidence page)
python scripts/seed_demo.py

# Run tamper-detection demonstration against a case package
python scripts/tamper_demo.py

# Run performance & accuracy benchmark on synthetic dataset
python scripts/benchmark.py

# Verify an exported case package independently (stdlib + optional cryptography)
python verifier/verifier.py --package backend/case_data/packages/package_PRM-2026-0042
```

> **Note on Demo Signing Keys:** On first run, PRAMAAN generates a local Ed25519 keypair in `backend/keys/` (`ed25519_private.pem`, `ed25519_public.pem`). These are **demo keys** for local evaluation and are excluded from version control.

---

## Documentation Index
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — System architecture & Mermaid diagram
- [`docs/API.md`](docs/API.md) — REST & SSE API reference
- [`docs/DECISIONS.md`](docs/DECISIONS.md) — Engineering decisions, removals, and archive log
- [`docs/STACK_SANITY_REPORT.md`](docs/STACK_SANITY_REPORT.md) — Single-source-of-truth backend/frontend port & build report
- [`docs/TEST_SLOWNESS_REPORT.md`](docs/TEST_SLOWNESS_REPORT.md) — Test timeout diagnosis, fixes, and before/after timings
- [`docs/DEMO_SCRIPT.md`](docs/DEMO_SCRIPT.md) — Step-by-step live demo script & timings
- [`docs/DATASET.md`](docs/DATASET.md) — Synthetic case inventory & 15 planted ground-truth facts
- [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) — Measured benchmark metrics (`synthetic dataset, this machine`)
- [`docs/DEPLOYMENT_ROADMAP.md`](docs/DEPLOYMENT_ROADMAP.md) — Roadmap to multi-user law-enforcement deployment
- [`docs/OFFLINE_INSTALL.md`](docs/OFFLINE_INSTALL.md) — Air-gap USB bundle guide
- [`docs/LIMITS.md`](docs/LIMITS.md) — Cryptographic & forensic boundaries
- [`docs/FINAL_CHECKLIST.md`](docs/FINAL_CHECKLIST.md) — Phase 5 QA sign-off checklist
