"""Offline Network Guard for PRAMAAN.

Blocks and counts any attempt to open a socket to a non-local address when
enabled (via `OFFLINE=1` environment variable or `install_network_guard()`).
"""

from __future__ import annotations

import ipaddress
import os
import socket
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional, Tuple


class OfflineNetworkError(OSError):
    """Raised when code attempts an outbound non-local network connection under OFFLINE guard."""


_LOCK = Lock()
_GUARD_ACTIVE = False
_OUTBOUND_COUNT = 0
_BLOCKED_ATTEMPTS: List[Dict[str, Any]] = []

_ORIG_CONNECT = socket.socket.connect
_ORIG_CONNECT_EX = socket.socket.connect_ex
_ORIG_CREATE_CONNECTION = socket.create_connection

_LOCAL_HOSTS = {
    "",
    "localhost",
    "localhost.localdomain",
    "127.0.0.1",
    "::1",
    "::ffff:127.0.0.1",
    "0.0.0.0",
    "::",
}


def is_local_host(host: Any) -> bool:
    """Return True if host refers strictly to loopback / local interface."""
    if host is None:
        return True
    if not isinstance(host, str):
        return False
    h = host.strip().lower().rstrip(".")
    if h in _LOCAL_HOSTS:
        return True
    # Handle IPv6 zone IDs like fe80::1%lo0 or ::1%lo0
    if "%" in h:
        h = h.split("%", 1)[0]
        if h in _LOCAL_HOSTS:
            return True
    try:
        ip = ipaddress.ip_address(h)
        return ip.is_loopback or ip.is_unspecified
    except ValueError:
        return False


def _extract_host_port(address: Any) -> Tuple[Optional[str], Optional[int]]:
    if isinstance(address, tuple) and len(address) >= 2:
        return str(address[0]), int(address[1]) if isinstance(address[1], int) else None
    if isinstance(address, str):
        # Unix socket path
        return None, None
    return str(address), None


def _check_and_record(sock_family: int, address: Any) -> None:
    global _OUTBOUND_COUNT
    if sock_family == getattr(socket, "AF_UNIX", -1):
        return
    host, port = _extract_host_port(address)
    if host is None or is_local_host(host):
        return
    with _LOCK:
        _OUTBOUND_COUNT += 1
        _BLOCKED_ATTEMPTS.append({
            "host": host,
            "port": port,
            "ts_utc": datetime.now(timezone.utc).isoformat(),
        })
    raise OfflineNetworkError(
        f"OFFLINE_GUARD: Blocked outbound socket connection to non-local address ({host}:{port})"
    )


def _guarded_connect(self: socket.socket, address: Any) -> Any:
    _check_and_record(self.family, address)
    return _ORIG_CONNECT(self, address)


def _guarded_connect_ex(self: socket.socket, address: Any) -> int:
    _check_and_record(self.family, address)
    return _ORIG_CONNECT_EX(self, address)


def _guarded_create_connection(address: Tuple[str, int], *args: Any, **kwargs: Any) -> socket.socket:
    _check_and_record(socket.AF_INET, address)
    return _ORIG_CREATE_CONNECTION(address, *args, **kwargs)


def install_network_guard() -> None:
    """Install the global socket guard blocking non-local outbound connections."""
    global _GUARD_ACTIVE
    with _LOCK:
        if _GUARD_ACTIVE:
            return
        socket.socket.connect = _guarded_connect  # type: ignore[method-assign]
        socket.socket.connect_ex = _guarded_connect_ex  # type: ignore[method-assign]
        socket.create_connection = _guarded_create_connection  # type: ignore[assignment]
        _GUARD_ACTIVE = True


def uninstall_network_guard() -> None:
    """Restore original socket functions."""
    global _GUARD_ACTIVE
    with _LOCK:
        if not _GUARD_ACTIVE:
            return
        socket.socket.connect = _ORIG_CONNECT  # type: ignore[method-assign]
        socket.socket.connect_ex = _ORIG_CONNECT_EX  # type: ignore[method-assign]
        socket.create_connection = _ORIG_CREATE_CONNECTION  # type: ignore[assignment]
        _GUARD_ACTIVE = False


def reset_guard_stats() -> None:
    """Reset the outbound connection attempt counter and log."""
    global _OUTBOUND_COUNT
    with _LOCK:
        _OUTBOUND_COUNT = 0
        _BLOCKED_ATTEMPTS.clear()


def is_guard_active() -> bool:
    return _GUARD_ACTIVE


def get_outbound_count() -> int:
    with _LOCK:
        return _OUTBOUND_COUNT


def get_blocked_attempts() -> List[Dict[str, Any]]:
    with _LOCK:
        return list(_BLOCKED_ATTEMPTS)


if os.getenv("OFFLINE", "0") == "1":
    install_network_guard()
