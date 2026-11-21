# PRAMAAN Live Demo Script (`docs/DEMO_SCRIPT.md`)

Measured end-to-end on a clean database (`PRM-2026-0042`, offline mode `OFFLINE=1`, Apple M4 / macOS 15.6 / Python 3.12.12).

> **Pre-demo clean reset (optional):**
> Remove `backend/case_data/`, `backend/evidence_store/`, and `backend/keys/` before starting so PRAMAAN initializes a fresh SQLite database and generates its first-run local demo Ed25519 keypair.
> Start the backend in offline mode:
> `OFFLINE=1 uvicorn backend.app.main:app --host 127.0.0.1 --port 8000`
> Open `http://127.0.0.1:8000/` in your browser (or `http://localhost:5173/` when running Vite dev).

---

## Step 1 — Clean Start & Evidence Folder Ingest (~1–2 seconds)
1. Start on **Overview** (`/`).
   - **Expected on-screen result:** Top `CaseBar` displays `PRM-2026-0042`, `Synthetic case`, Integrity Seal `CHAIN INTACT · 0 exhibits · root genesis`, and `Status` popover shows `OFFLINE` and `Network use: 0 outbound connections`.
2. Navigate to **Evidence** (`/evidence`).
3. Drag and drop the `data/case_alpha/` folder (or click **Upload Folder** and select `data/case_alpha/`) — 20 evidence files across all 7 source families (non-evidence reference JSONs/tower registry are skipped automatically on folder upload).
   - **Measured timing:** ~0.14s (20 exhibits via HTTP) + UI render.
   - **Expected on-screen result:** Sequential exhibit IDs `EX-001` through `EX-020` appear with truncated SHA-256 `HashChip`s (`8…4`), sizes, and `PENDING` parse status. The top Integrity Seal updates to `CHAIN INTACT · 20 exhibits · root ffc4d6d4…69f7`.

---

## Step 2 — Run Analysis Pipeline (~2 seconds)
1. Click **Run Pipeline** (vermilion button in the top `CaseBar`).
   - **Measured timing:** ~1.4s–1.8s end-to-end on the synthetic dataset.
   - **Expected on-screen result:** All 20 exhibits transition to `PARSED`; 84 normalized entities, 1,200 mentions, 16 episodes, 19+ anomalies, correlation edges, and 3 verified AI claims (1 removed by Rule V4) populate across the database.
   - Return briefly to **Overview** (`/`): the left **Evidence and Court Package** panel (slate teal) shows `Integrity Seal Intact`, `20` exhibits hashed, all source families, and `0 of N items approved for the report`; the right **Investigation** panel (amber) shows the strongest `LEAD` correlation, anomaly counts by severity, and a suggested starter question.

---

## Step 3 — Knowledge Graph & "Why This Link" (~15 seconds)
1. Navigate to **Knowledge Graph** (`/graph`).
   - **Expected on-screen result:** Cytoscape `fcose` graph renders with `LEAD` links dashed amber and `APPROVED` links green (`202` nodes, `263` edges including episode/observation links).
2. Type `vikram.alpha@okaxis` into **Search Entities**.
3. Click the `SAME_IDENTIFIER` link in the graph or in the **Matching Correlation Links** list on the right.
   - **Expected on-screen result:** Right panel opens **Why This Link** showing `EX-010 → EX-020` / `EX-002 → EX-020`, `Basis: Exact Identifier Match`, `Exact UPI 'vikram.alpha@okaxis' appears across both ...`, `Deterministic strength: 100% (feature-derived, never model-stated)`, clickable `EX-` source chips, and `Approve` / `Reject` buttons.
4. Clear the search box and search for `203.0.113.45`. Click the `SHARED_IP_CROSS_SOURCE` edge.
   - **Expected on-screen result:** **Why This Link** shows `Email header IP 203.0.113.45 matches IP 203.0.113.45 in network log`, `Deterministic strength: 95%`, and cited exhibits (`email_support.eml`, `mailbox_investigator.mbox`, `network_portal_logs.csv`).

---

## Step 4 — Crime Scene Reconstruction & Sequence Replay (~25 seconds)
1. Navigate to **Reconstruction** (`/reconstruction`).
2. Click **Regenerate Sequence** (top right; ~0.17s).
   - **Expected on-screen result:** `vis-timeline` populates across source lanes; **Locations (Offline Coordinate Canvas)** plots cell-tower, cloud-GPS, and CCTV points on a plain coordinate grid (no map tiles); **Generated Episodes** lists `EP-001` through `EP-016`.
3. In **Sequence Anomalies & Clock Offsets**:
   - Point out the **6h 14m chat silence gap** (`ANOMALY_CHAT_GAP`: `2026-03-14 23:45` to `2026-03-15 05:59`) and switch to `EP-011` (or inspect `TEMPORAL_CO_OCCURRENCE`) to show the **`ADMIN_PORTAL_LOGIN`** from `203.0.113.45` at `2026-03-15T01:30:00+05:30` that occurred *inside* the silence gap.
   - Point out the **out-of-order message** (`ANOMALY_OUT_OF_ORDER`: `15/03/2026 14:18` appearing after `14:35`).
   - Point out **`CLOCK_OFFSET_APPLIED (+252s)`** on `CAM-NOI-ATM-01` (`orig 2026-03-15 14:15:48 → 2026-03-15T08:50:00+00:00 via NTP drift audit (+4m12s)`).
   - Point out the **`IMPOSSIBLE_TRAVEL`** flag (`D1` observed in Jaipur at `14:00 IST` and Noida Sector 62 ATM at `14:20 IST`, dashed vermilion trajectory on the Locations canvas).
4. Select episode **`EP-013`** in **Scene Replay** (or click `EP-013` in Generated Episodes) and step through with **Next step** / the scrubber slider to replay events, actors, places (`not established` when absent), and applied clock offsets.

---

## Step 5 — Evidence Authenticity Indicators (~15 seconds)
1. Navigate to **Evidence** (`/evidence`).
2. Click `screenshot_withdrawal_edited.jpg` (`EX-016`), then switch to the **Authenticity** tab in the detail drawer.
   - **Expected on-screen result:** `TAMPERED` badge, **Edited-Screenshot Indicators Detected** showing `EXIF Software: PixelMod Editor Pro v2.4`, `Created: 2026:03:15 14:00:00 · Modified: 2026:03:16 09:30:00`, elevated ELA hotspot ratio, and side-by-side **Original Exhibit** vs **Error Level Analysis (ELA)** heatmap.
3. Close the drawer, click `bank_statement_mule_A.pdf` (`EX-002`), and switch to **Authenticity**.
   - **Expected on-screen result:** `TAMPERED` badge and the **Bank Ledger Arithmetic Check** table highlighting row `#10` (`15/03/2026 · IMPS/DR/60741199005/To Sunita Verma`) in vermilion with `Stated: 2,20,000` vs `Expected: 1,90,000` (`FAIL`).

---

## Step 6 — Investigator Assistant (~20 seconds)
1. Navigate to **Assistant** (`/assistant`).
2. Ask 3 questions:
   - Question 1: `Who is connected to vikram.alpha@okaxis?` → returns cited connections in the left pane and cited claims/exhibit chips in the right **Evidence** pane (`model unavailable, deterministic mode`).
   - Question 2: `What happened between 10 pm and 5 am on night 3?` → cites the 6h 14m silence gap and `ADMIN_PORTAL_LOGIN`.
   - Question 3 (unanswerable): `What is the flight number for Vikram's trip to Dubai?` → refuses with `I found nothing in the evidence about that.` (`0 cited claims`; **Add to review queue** is disabled per Rule V4).
3. On Question 1's card, click **How I got this** (and optionally **Explain answer**) to inspect the tool calls (`connections`, `search_text`), AI run SHA-256, and verifier outcome.
4. Click **Add to review queue** on Question 1's card → confirms `Verified & added to Review Queue (Workspace 1) awaiting human approval.`

---

## Step 7 — Keyboard Review, Signed Package, Standalone Verifier & Tamper Test (~30 seconds)
1. Navigate to **Review and Report** (`/review`).
2. In **1. Review Queue**:
   - Press `J` / `K` to step through items, `A` to approve at least 2 verified claims (including the promoted answer) and 1 lead edge, and optionally `R` to reject or `E` to edit a claim.
3. Switch to **2. Court Package** and click **Build Package** (~0.23s–0.47s).
   - **Expected on-screen result:** Approved Findings table updates with only human-approved items; **Section 63 Certificate Annexure** displays `DRAFT — HUMANS MUST SIGN`, the consolidated Merkle root, and QR payload.
4. Switch to **3. Verify & Trust Report** and click **Run verifier.py**.
   - **Expected on-screen result:** `PASS (exit 0)` and `FINAL VERDICT: ALL CRYPTOGRAPHIC CHECKS PASSED [VERIFIED BY CODE]`.
5. In a terminal, run the standalone tamper demonstration:
   ```bash
   python scripts/tamper_demo.py
   ```
   - **Expected output:** Verifies intact package (`PASS`), flips byte 0 of `bank_statement_meera.pdf`, and fails verification (`FINAL VERDICT: TAMPERING OR CORRUPTION DETECTED [FAILED]`), naming `EX-001 (bank_statement_meera.pdf): HASH MISMATCH!`.
6. **Live Integrity Seal Tamper Test in the App:**
   - Locate any stored file in `backend/evidence_store/` (e.g., `EX-001`'s SHA-256 file), temporarily `chmod 644` and modify 1 byte, then click **Verify now** in the top `CaseBar`.
   - **Expected on-screen result:** The Integrity Seal immediately turns **vermilion** (`TAMPERING DETECTED · Exhibit: EX-001`), and Overview reflects the breach. *(Restore the original file bytes and `chmod 444` afterward if continuing the demo.)*
