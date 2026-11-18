"""Geographic gazetteer and cell tower location extraction for PRAMAAN."""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Tuple
from backend.app.extract.patterns import ExtractedEntityMatch

KNOWN_LOCATIONS = {
    "noida sector 62": {"lat": 28.628, "lon": 77.365, "kind": "cell_tower_area", "tower": "TOW-NOI-042"},
    "noida sector 18": {"lat": 28.570, "lon": 77.320, "kind": "cell_tower_area", "tower": "TOW-NOI-045"},
    "jaipur malviya nagar": {"lat": 26.853, "lon": 75.805, "kind": "cell_tower_area", "tower": "TOW-JAI-108"},
    "jaipur c-scheme": {"lat": 26.908, "lon": 75.800, "kind": "cell_tower_area", "tower": "TOW-JAI-112"},
    "delhi connaught place": {"lat": 28.631, "lon": 77.219, "kind": "cell_tower_area", "tower": "TOW-DEL-009"},
    "pune": {"lat": 18.5204, "lon": 73.8567, "kind": "city"},
    "nagpur": {"lat": 21.1458, "lon": 79.0882, "kind": "city"},
    "delhi": {"lat": 28.6139, "lon": 77.2090, "kind": "city"},
    "jaipur": {"lat": 26.9124, "lon": 75.7873, "kind": "city"},
    "noida": {"lat": 28.5355, "lon": 77.3910, "kind": "city"},
}


def extract_locations(text: str) -> List[ExtractedEntityMatch]:
    """Extract location mentions and tower references from text."""
    if not text:
        return []
    matches = []
    lower = text.lower()

    for loc_name, meta in KNOWN_LOCATIONS.items():
        pattern = r"\b" + re.escape(loc_name) + r"\b"
        for m in re.finditer(pattern, lower):
            matches.append(
                ExtractedEntityMatch(
                    type="LOCATION",
                    value_raw=text[m.start():m.end()],
                    value_norm=loc_name.title(),
                    char_start=m.start(),
                    char_end=m.end(),
                    extractor="location_gazetteer",
                )
            )

    return matches

