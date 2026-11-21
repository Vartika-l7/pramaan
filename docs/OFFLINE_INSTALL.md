# PRAMAAN Air-Gap & Offline Installation Guide

This document describes how to build, transfer via USB, verify, and install **PRAMAAN** on an air-gapped workstation (Windows, macOS, or Linux) with **zero internet access**.

---

## 1. Preparing the Air-Gap Bundle (On a Connected Build Machine)

Run the automated bundle builder from the repository root:

```bash
python scripts/make_offline_bundle.py --output offline_bundle
```

This creates `offline_bundle/` containing:
- `wheels/` — All Python wheel/source distributions from `requirements.txt` (`pip download -r requirements.txt -d offline_bundle/wheels`).
- `frontend_dist/` — Built static frontend (`npm run build`) with locally bundled `@fontsource` fonts and zero CDN references.
- `app/` — Backend, standalone `verifier/verifier.py`, scripts, tests, docs, and the `data/case_alpha` synthetic dataset.
- `install_offline.py` — Cross-platform offline installer script.
- `BUNDLE_SHA256SUMS.txt` — SHA-256 checksums for every file in the bundle.

---

## 2. Verifying the Bundle After USB Transfer

Before installing on the air-gapped machine, verify that no files were corrupted or altered during USB transfer:

### Linux / macOS
```bash
cd offline_bundle
shasum -a 256 -c BUNDLE_SHA256SUMS.txt
```

### Windows (PowerShell) or Any OS (Python)
```bash
python -c "import hashlib, pathlib; bad=[p for line in open('BUNDLE_SHA256SUMS.txt') for h,p in [line.strip().split('  ',1)] if hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()!=h]; print('OK' if not bad else f'FAILED: {bad}')"
```

---

## 3. Installing Offline (Zero Network Required)

### Option A: Automated Cross-Platform Installer
```bash
cd offline_bundle
python install_offline.py --venv .venv
```

### Option B: Manual Virtual Environment Install
Create a clean virtual environment and install strictly from local wheels:

```bash
python -m venv .venv
```

Activate it:
- **macOS / Linux:** `source .venv/bin/activate`
- **Windows (PowerShell):** `.venv\Scripts\Activate.ps1`

Install offline using `--no-index --find-links`:
```bash
python -m pip install --no-index --find-links wheels -r app/requirements.txt
```

Verify offline execution with the built-in network guard enabled:
```bash
cd app
OFFLINE=1 python scripts/check_offline.py
```

---

## 4. Copying Optional Offline Models & Binaries via USB

PRAMAAN's core forensic pipeline (hashing, custody chain, Merkle trees, Ed25519 signing, all 13 evidence parsers, correlation engine, knowledge graph, spatial/temporal analysis, event sequence, crime scene reconstruction, deterministic claim verification, and deterministic assistant) runs **100% out of the box** using only the Python wheels and static frontend above.

The following **optional** components can be copied onto the air-gapped machine via USB to enable enhanced capabilities:

### 4.1 Ollama Local LLM Weights (Optional)
1. On a connected machine with Ollama installed:
   ```bash
   ollama pull llama3.2
   ollama pull mistral
   ```
2. Copy the Ollama models directory to USB:
   - **macOS / Linux:** `~/.ollama/models/`
   - **Windows:** `%USERPROFILE%\.ollama\models\`
3. On the air-gapped machine, copy `models/` into the same location (or set `OLLAMA_MODELS=/path/to/usb/models`) and start `ollama serve`.

### 4.2 Tesseract OCR Engine & Language Packs (Optional)
1. Install the offline OS package/installer for `tesseract` (e.g., Windows UB-Mannheim installer `.exe`, macOS `.pkg`/Homebrew bottle, or Linux `.deb`/`.rpm`).
2. Copy the trained language data files to USB:
   - `eng.traineddata` (English)
   - `hin.traineddata` (Hindi / Devanagari)
3. Place them in the Tesseract `tessdata/` directory and set `TESSDATA_PREFIX` if installed in a custom path.

### 4.3 Optional IndicNER Transformer Model (Optional)
1. Download the Hugging Face model snapshot on a connected machine into a local cache folder (e.g., `hf_cache/`).
2. Copy `hf_cache/` to the air-gapped machine via USB.
3. Set environment variables before starting the backend:
   ```bash
   export USE_INDIC_NER=1
   export TRANSFORMERS_OFFLINE=1
   export HF_HOME=/path/to/hf_cache
   ```

### 4.4 Optional Offline GeoIP Database (Optional)
1. Copy your offline MaxMind/GeoLite2 `.mmdb` file via USB.
2. Set `GEOIP_DB_PATH=/path/to/GeoLite2-City.mmdb`.

---

## 5. Graceful Degradation When Optional Files Are Absent

Every optional feature degrades gracefully offline without crashing, without making outbound network calls, and without inventing facts:

| Optional Component | Status When Files Absent | Graceful Fallback Behavior |
| :--- | :--- | :--- |
| **Ollama LLM** (`llama3.2`, `mistral`) | Unavailable | Automatically switches to `DeterministicProvider` and `"model unavailable, deterministic mode"` in the Assistant. All claims still pass through deterministic Rules V1–V5. |
| **Tesseract OCR** (`eng.traineddata`, `hin.traineddata`) | Unavailable | `ImageParser` still computes SHA-256, perceptual hash (`pHash`), dimensions, EXIF metadata, and ELA heatmaps, and sets `ocr_status: "UNAVAILABLE"` with an explicit note. |
| **IndicNER (`transformers`)** | Disabled (`USE_INDIC_NER=0`) | `extract/names.py` & `extract/language.py` use deterministic regex, honorific stripping, Devanagari-to-Latin transliteration, and RapidFuzz matching. |
| **Offline GeoIP DB** (`GEOIP_DB_PATH`) | Absent | `spatial/geo.py` (`lookup_ip_location`) explicitly returns `"location unknown"` instead of guessing coordinates or calling an external IP lookup API. |
