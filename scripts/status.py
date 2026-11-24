"""scripts/status.py — Show which PRAMAAN ports are listening and test /api/health.

Usage:
    python scripts/status.py

Prints:
  - Which of ports 8000 and 5173 are currently listening
  - The process ID owning each port (best-effort on each OS)
  - The JSON response from /api/health (or an error if unreachable)
"""

import json
import socket
import sys
import urllib.error
import urllib.request

PORTS = {
    8000: "Backend (FastAPI / uvicorn)",
    5173: "Frontend (Vite dev server)",
}
HEALTH_URL = "http://127.0.0.1:8000/api/health"


def _port_listening(port: int) -> bool:
    """Return True if something is listening on localhost (IPv4 or IPv6) on <port>."""
    for host in ("127.0.0.1", "::1"):
        try:
            with socket.create_connection((host, port), timeout=1):
                return True
        except (ConnectionRefusedError, OSError):
            continue
    return False


def _pid_for_port(port: int) -> str:
    """Best-effort: return PID owning TCP port on current OS."""
    import subprocess
    if sys.platform == "win32":
        try:
            out = subprocess.check_output(
                ["netstat", "-ano"], text=True, stderr=subprocess.DEVNULL
            )
            for line in out.splitlines():
                if f":{port} " in line and "LISTENING" in line:
                    return line.split()[-1]
        except Exception:
            pass
    else:
        for cmd in [["lsof", "-iTCP", f":{port}", "-sTCP:LISTEN", "-t"],
                    ["ss", "-tlnp", f"sport = :{port}"]]:
            try:
                out = subprocess.check_output(cmd, text=True, stderr=subprocess.DEVNULL).strip()
                if out:
                    return out.split("\n")[0].strip()
            except Exception:
                pass
    return "unknown"


def main():
    print("\n[PRAMAAN status.py]")
    print("=" * 50)

    # Port status
    print("\nPort status:")
    for port, label in PORTS.items():
        listening = _port_listening(port)
        status = "LISTENING" if listening else "not listening"
        pid = _pid_for_port(port) if listening else "-"
        print(f"  :{port}  {label}")
        print(f"         Status : {status}")
        print(f"         PID    : {pid}")

    # /api/health check
    print(f"\n/api/health → {HEALTH_URL}")
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode()
            data = json.loads(body)
            print("  HTTP status : 200 OK")
            print(f"  Response    : {json.dumps(data, indent=4)}")
    except urllib.error.HTTPError as e:
        print(f"  HTTP ERROR  : {e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"  UNREACHABLE : {e.reason}")
        print(f"  → Start the backend with: python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000")
    except Exception as e:
        print(f"  ERROR       : {e}")

    # Quick root check
    root_url = "http://127.0.0.1:8000/"
    print(f"\nGET / → {root_url}")
    try:
        req = urllib.request.Request(root_url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=3) as resp:
            body = resp.read().decode()
            data = json.loads(body)
            print(f"  HTTP status : 200 OK")
            print(f"  Response    : {json.dumps(data, indent=4)}")
    except urllib.error.HTTPError as e:
        print(f"  HTTP ERROR  : {e.code} {e.reason}")
    except urllib.error.URLError as e:
        print(f"  UNREACHABLE : {e.reason}")
    except Exception as e:
        print(f"  ERROR       : {e}")

    print("\n" + "=" * 50)
    print("Tip: open http://localhost:5173 in your browser for the UI.")
    print("     If you see an old UI at port 8000, do a hard-refresh (Ctrl+Shift+R).")
    print()


if __name__ == "__main__":
    main()
