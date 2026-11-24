"""scripts/dev.py — Start PRAMAAN backend and frontend together (cross-platform).

Usage:
    python scripts/dev.py

Starts:
  - Backend  : uvicorn on http://127.0.0.1:8000
  - Frontend : Vite dev server on http://localhost:5173

Press Ctrl+C to stop both.
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_CMD = [sys.executable, "-m", "uvicorn", "backend.app.main:app",
               "--host", "127.0.0.1", "--port", "8000"]
FRONTEND_CMD = ["npm", "run", "dev"]
FRONTEND_CWD = REPO_ROOT / "frontend"


def _check_port(port: int) -> bool:
    """Return True if the port is already in use (IPv4 or IPv6)."""
    import socket
    for host in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((host, port), timeout=0.5):
                return True
        except OSError:
            pass
    return False


def main():
    if _check_port(8000):
        print("[dev.py] ERROR: Port 8000 is already in use. Stop the existing process first.", file=sys.stderr)
        sys.exit(1)
    if _check_port(5173):
        print("[dev.py] ERROR: Port 5173 is already in use. Stop the existing process first.", file=sys.stderr)
        sys.exit(1)

    print("\n[PRAMAAN dev.py] Starting development servers...")
    print(f"  Backend  : http://127.0.0.1:8000")
    print(f"  Frontend : http://localhost:5173")
    print(f"  API docs : http://127.0.0.1:8000/docs")
    print(f"  Health   : http://127.0.0.1:8000/api/health")
    print(f"\nPress Ctrl+C to stop both servers.\n")

    # On Windows, use shell=True for npm; on other platforms shell=False is fine.
    is_windows = sys.platform == "win32"

    backend = subprocess.Popen(
        BACKEND_CMD,
        cwd=str(REPO_ROOT),
        env={**os.environ},
    )
    # Small delay so uvicorn prints its startup banner before npm output starts
    time.sleep(1)

    frontend = subprocess.Popen(
        FRONTEND_CMD,
        cwd=str(FRONTEND_CWD),
        shell=is_windows,
        env={**os.environ},
    )

    procs = [backend, frontend]

    def _shutdown(signum=None, frame=None):
        print("\n[dev.py] Shutting down...")
        for p in procs:
            if p.poll() is None:
                if is_windows:
                    p.terminate()
                else:
                    p.send_signal(signal.SIGTERM)
        for p in procs:
            try:
                p.wait(timeout=5)
            except subprocess.TimeoutExpired:
                p.kill()
        print("[dev.py] Done.")
        sys.exit(0)

    signal.signal(signal.SIGINT, _shutdown)
    signal.signal(signal.SIGTERM, _shutdown)

    # Wait for either process to exit
    while True:
        for p in procs:
            rc = p.poll()
            if rc is not None:
                name = "Backend" if p is backend else "Frontend"
                print(f"\n[dev.py] {name} exited with code {rc}. Stopping the other server.")
                _shutdown()
        time.sleep(1)


if __name__ == "__main__":
    main()
