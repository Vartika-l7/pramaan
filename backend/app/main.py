"""PRAMAAN FastAPI Application Entrypoint."""

from contextlib import asynccontextmanager
import os
import socket
import sys
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.config import BASE_DIR, CASE_DATA_DIR, DEFAULT_CASE_ID, EVIDENCE_STORE_DIR, KEYS_DIR
from backend.app.db import get_db_path, init_db
from backend.app.network_guard import install_network_guard
from backend.app.api.integrity import router as integrity_router
from backend.app.api.evidence import router as evidence_router
from backend.app.api.events import router as events_router
from backend.app.api.entities import router as entities_router
from backend.app.api.graph import router as graph_router
from backend.app.api.anomalies import router as anomalies_router
from backend.app.api.authenticity import router as authenticity_router
from backend.app.api.analyze import router as analyze_router
from backend.app.api.claims import router as claims_router
from backend.app.api.review import router as review_router
from backend.app.api.system import router as system_router
from backend.app.api.report import router as report_router
from backend.app.api.benchmark import router as benchmark_router
from backend.app.api.sequence import router as sequence_router
from backend.app.api.scene import router as scene_router
from backend.app.api.assistant import router as assistant_router

# ---------------------------------------------------------------------------
# Resolved paths — printed at startup so there is no ambiguity
# ---------------------------------------------------------------------------
_REPO_ROOT = BASE_DIR.resolve()
_DB_PATH = get_db_path().resolve()
_EVIDENCE_STORE = EVIDENCE_STORE_DIR.resolve()
_CASE_DATA_DIR = CASE_DATA_DIR.resolve()
_KEYS_DIR = KEYS_DIR.resolve()
_FRONTEND_URL = os.getenv("PRAMAAN_FRONTEND_URL", "http://localhost:5173")


def _resolve_listen_port() -> int:
    """Detect port from CLI args (--port N) or PRAMAAN_PORT env var (default 8000)."""
    argv = sys.argv
    for i, arg in enumerate(argv):
        if arg == "--port" and i + 1 < len(argv):
            try:
                return int(argv[i + 1])
            except ValueError:
                pass
        elif arg.startswith("--port="):
            try:
                return int(arg.split("=", 1)[1])
            except ValueError:
                pass
    return int(os.getenv("PRAMAAN_PORT", "8000"))


def _check_port_free(port: int, host: str = "127.0.0.1") -> None:
    """Exit with a clear message if the target port is already in use."""
    in_use = False
    for addr in (host, "::1"):
        try:
            with socket.create_connection((addr, port), timeout=0.5):
                in_use = True
                break
        except OSError:
            pass
    if not in_use:
        # Also verify we can bind exclusively (without SO_REUSEADDR, which allows
        # duplicate binds on Windows).
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host, port))
            except OSError:
                in_use = True
    if in_use:
        print(
            f"\n[PRAMAAN] ERROR: Port {port} is already in use on {host}.\n"
            f"  Run `python scripts/status.py` to see which process owns port {port},\n"
            f"  stop that process, or run with a different --port.\n",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)


def _print_startup_paths(port: int) -> None:
    print(
        f"\n[PRAMAAN] Backend starting on http://127.0.0.1:{port}\n"
        f"  Repo root : {_REPO_ROOT}\n"
        f"  Case ID   : {DEFAULT_CASE_ID}\n"
        f"  Database  : {_DB_PATH}\n"
        f"  Evidence  : {_EVIDENCE_STORE}\n"
        f"  Keys dir  : {_KEYS_DIR}\n"
        f"  Frontend  : {_FRONTEND_URL}  (dev server — backend serves API only)\n"
        f"  API docs  : http://127.0.0.1:{port}/docs\n"
        f"  Health    : http://127.0.0.1:{port}/api/health\n"
        f"  NOTE: The backend serves ONLY /api/* endpoints.\n"
        f"        Open {_FRONTEND_URL} in your browser for the UI.\n",
        flush=True,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Enforce offline network guard when OFFLINE=1
    if os.getenv("OFFLINE", "0") == "1":
        install_network_guard()
    port = _resolve_listen_port()
    # Refuse to start if launched via uvicorn (non-reload) and port is already bound.
    # (Under --reload, uvicorn's parent reloader already owns the listening socket;
    #  scripts/dev.py and `python -m backend.app.main` check the port before uvicorn starts.)
    if "uvicorn" in " ".join(sys.argv).lower() and "--reload" not in sys.argv:
        _check_port_free(port)
    # Initialize SQLite database and triggers
    init_db()
    _print_startup_paths(port)
    yield


app = FastAPI(
    title="PRAMAAN Digital Forensics Engine",
    description="Offline, AI-Assisted Evidence Correlation & Crime Reconstruction Framework",
    version="2.0.0",
    lifespan=lifespan,
)

# Enable CORS for localhost Vite frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers — ALL under /api prefix (see individual router files)
app.include_router(integrity_router)
app.include_router(evidence_router)
app.include_router(events_router)
app.include_router(entities_router)
app.include_router(graph_router)
app.include_router(anomalies_router)
app.include_router(authenticity_router)
app.include_router(analyze_router)
app.include_router(claims_router)
app.include_router(review_router)
app.include_router(system_router)
app.include_router(report_router)
app.include_router(benchmark_router)
app.include_router(sequence_router)
app.include_router(scene_router)
app.include_router(assistant_router)


@app.get("/api/health")
def health_check():
    """Health check — returns version, resolved paths, and frontend URL."""
    port = _resolve_listen_port()
    return {
        "status": "ok",
        "version": app.version,
        "engine": "PRAMAAN",
        "mode": "offline",
        "repo_root": str(_REPO_ROOT),
        "case_id": DEFAULT_CASE_ID,
        "db_path": str(get_db_path().resolve()),
        "case_data_dir": str(_CASE_DATA_DIR),
        "evidence_store": str(_EVIDENCE_STORE),
        "keys_dir": str(_KEYS_DIR),
        "frontend_url": _FRONTEND_URL,
        "api_docs": f"http://127.0.0.1:{port}/docs",
        "synthetic_notice": "Synthetic case PRM-2026-0042. All persons and identifiers are fictional.",
    }


@app.get("/")
def root():
    """Root path — points browser to the Vite frontend dev server."""
    port = _resolve_listen_port()
    return {
        "message": "PRAMAAN API — backend only. Open the frontend URL for the UI.",
        "ui": _FRONTEND_URL,
        "docs": f"http://127.0.0.1:{port}/docs",
        "health": f"http://127.0.0.1:{port}/api/health",
    }


# NOTE: StaticFiles mount for frontend/dist has been intentionally removed.
# The backend serves ONLY /api/* routes. To preview a production build, run
# `cd frontend && npm run build && npm run preview` (or serve frontend/dist).
# This change is recorded in docs/DECISIONS.md.


if __name__ == "__main__":
    import uvicorn

    port = _resolve_listen_port()
    _check_port_free(port)
    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=port)
