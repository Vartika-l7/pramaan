# PRAMAAN Stack Sanity Report

**Plain-English explanation of what was wrong, how we proved it, and how it is fixed.**

---

## 1. What Was Wrong (The Short Version)

When you opened `http://127.0.0.1:8000` (the backend address) in your browser, you saw the **old UI** from before the recent phase updates. When you opened `http://localhost:5173` (the frontend dev server), you saw the **new UI**.

**Why did this happen?**
The FastAPI backend (`backend/app/main.py`, lines 86–99) had a catch-all static file mount that automatically served whatever files were sitting inside `frontend/dist/`. That `frontend/dist/` folder was last built on **2026-11-19 at 20:18:25** (`index-BTn5FG_x.js`, `index-CWGnNtpH.css`) — **before** the new pages and redesign changes were pulled and built. Meanwhile, Vite on port `5173` compiles live from `frontend/src/`, so port `5173` showed the new code while port `8000` silently served the 5-day-old compiled files.

---

## 2. Investigation Findings (Evidence, Not Guesses)

### Every Server, Port, and Launch Entrypoint
| Way to Start | Folder | Port | Purpose |
| :--- | :--- | :--- | :--- |
| `python scripts/dev.py` *(new — recommended)* | Repo root (`pramaan/`) | `8000` + `5173` | Starts FastAPI backend and Vite frontend together; exits cleanly on `Ctrl+C`. |
| `python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000` | Repo root (`pramaan/`) | `8000` | Backend API only (`/api/*`, `/api/health`, `/docs`). |
| `python -m backend.app.main` | Repo root (`pramaan/`) | `8000` | Backend API with upfront port-in-use check. |
| `cd frontend && npm run dev` | `frontend/` | `5173` | Vite frontend dev server (proxies `/api/*` → `http://127.0.0.1:8000` via `frontend/vite.config.ts` lines 13–21). |
| `cd frontend && npm run preview` | `frontend/` | `4173` | Preview a production build after `npm run build`. |

No Dockerfiles, `Procfile`, `Makefile`, `launch.json`, or shell launch scripts existed in the repository.

### Root Cause Evidence
1. **Static mount in backend:** `backend/app/main.py` lines 86–99 mounted `frontend/dist/assets` via `StaticFiles` and registered a catch-all `@app.get("/{full_path:path}")` returning `FileResponse(frontend/dist/index.html)`.
2. **Stale build timestamp:** `frontend/dist/index.html` and `frontend/dist/assets/index-BTn5FG_x.js` were last modified on `2026-11-19 20:18:25`, whereas the active repo source (`frontend/package.json`, `backend/`, `docs/`) was updated on `2026-11-24 18:44:30`.
3. **Duplicate project check:**
   - Inside `c:\Users\Vartika Sharma\Desktop\pramaan`: only **one** `requirements.txt` (`2026-11-24 18:44:30`), **one** `backend/app/main.py`, **one** `frontend/package.json` (`2026-11-24 18:44:30`), and **one** `frontend/index.html` (`2026-11-18 19:30:29`).
   - Inside parent folder `c:\Users\Vartika Sharma\Desktop`: no duplicate copy of `pramaan` exists (only unrelated projects).
4. **Service worker check:** Searched all `.ts` and `.tsx` files in `frontend/src/` for `serviceWorker` — **0 matches**. No service worker is registered.

### How to Check Which Process Owns a Port
- **Windows (PowerShell / CMD):**
  ```powershell
  netstat -ano | findstr ":8000"
  netstat -ano | findstr ":5173"
  ```
- **macOS:**
  ```bash
  lsof -iTCP:8000 -sTCP:LISTEN
  lsof -iTCP:5173 -sTCP:LISTEN
  ```
- **Linux:**
  ```bash
  ss -tlnp 'sport = :8000 or sport = :5173'
  ```
- **Cross-platform (built-in helper):**
  ```bash
  python scripts/status.py
  ```

---

## 3. What Was Fixed

1. **Backend serves API only (`backend/app/main.py`):**
   - Removed the `StaticFiles` mount and catch-all HTML fallback for `frontend/dist/`.
   - `GET /api/health` now returns `status`, `version`, `case_id`, and the exact resolved absolute paths (`repo_root`, `db_path`, `case_data_dir`, `evidence_store`, `keys_dir`, `frontend_url`, `api_docs`).
   - `GET /` now returns a tiny JSON message pointing to `http://localhost:5173` instead of serving old HTML.
   - Added a startup path banner (`_print_startup_paths`) and port-in-use guard (`_check_port_free`) that refuses to start with a clear error message if port `8000` is already taken.
2. **Stale build archived (not deleted):**
   - Moved `frontend/dist/` → `_old_project_archive/frontend_dist_stale/dist/`.
   - Added `_old_project_archive/` to `.gitignore`.
   - Recorded every move and decision in [`docs/DECISIONS.md`](DECISIONS.md).
3. **One command to run and one command to inspect:**
   - Added [`scripts/dev.py`](../scripts/dev.py): starts backend (`:8000`) and frontend (`:5173`) together, checks both ports upfront, prints both addresses, and shuts both down cleanly on `Ctrl+C`.
   - Added [`scripts/status.py`](../scripts/status.py): checks IPv4 and IPv6 listeners on ports `8000` and `5173`, prints PIDs, and probes `/api/health` and `/`.
4. **Documentation updated:**
   - Updated [`README.md`](../README.md) with the exact port table (`8000` backend, `5173` frontend), `scripts/dev.py`, `scripts/status.py`, and production build instructions.

---

## 4. What You Should Do Now

1. **Always open the UI at [`http://localhost:5173`](http://localhost:5173)** (not `:8000`).
2. **Start both servers with one command:**
   ```bash
   python scripts/dev.py
   ```
3. **Check server health anytime:**
   ```bash
   python scripts/status.py
   ```
4. **If your browser still shows anything old on `http://127.0.0.1:8000`:** do a **hard refresh (`Ctrl+Shift+R` / `Cmd+Shift+R`)** or clear cached site data for `127.0.0.1:8000` in DevTools → Application → Clear site data. You should now see a small JSON response pointing you to `http://localhost:5173`.
