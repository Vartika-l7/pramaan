"""Offline geographic calculations and reference loaders (B3)."""

from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Dict, List, Optional, Any

from backend.app.config import TOWER_REGISTRY_PATH, GAZETTEER_PATH, GEOIP_DB_PATH

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance in kilometres between two WGS84 coordinates."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)

    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_KM * c


def load_tower_registry(path: Optional[Path] = None) -> Dict[str, Dict[str, Any]]:
    """Load cell-tower coordinates from CSV (synthetic/operator registry)."""
    target = path or TOWER_REGISTRY_PATH
    towers: Dict[str, Dict[str, Any]] = {}
    if not target.exists():
        return towers
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            tid = (row.get("tower_id") or "").strip()
            if not tid:
                continue
            try:
                towers[tid] = {
                    "tower_id": tid,
                    "location_name": (row.get("location_name") or tid).strip(),
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "accuracy_m": float(row.get("accuracy_m") or 500.0),
                }
            except Exception:
                continue
    return towers


def load_gazetteer(path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Load bundled offline gazetteer of Indian cities."""
    target = path or GAZETTEER_PATH
    cities: List[Dict[str, Any]] = []
    if not target.exists():
        return cities
    with open(target, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            city = (row.get("city") or "").strip()
            if not city:
                continue
            try:
                cities.append({
                    "city": city,
                    "state": (row.get("state") or "").strip(),
                    "lat": float(row["lat"]),
                    "lon": float(row["lon"]),
                    "accuracy_m": float(row.get("accuracy_m") or 10000.0),
                })
            except Exception:
                continue
    return cities


def lookup_ip_location(ip_addr: str) -> Dict[str, Any]:
    """Offline IP geolocation stub: returns 'location unknown' unless a local GeoIP DB is configured."""
    if GEOIP_DB_PATH and Path(GEOIP_DB_PATH).exists():
        # Hook for optional user-provided offline GeoIP file
        return {
            "ip": ip_addr,
            "place_name": "local_geoip_configured",
            "lat": None,
            "lon": None,
            "accuracy_m": None,
        }
    return {
        "ip": ip_addr,
        "place_name": "location unknown",
        "lat": None,
        "lon": None,
        "accuracy_m": None,
    }
