"""Time normalisation and reversible clock-offset helpers for PRAMAAN (B2)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo
import dateutil.parser


def normalise_to_utc(
    ts_raw: str,
    default_tz: str = "Asia/Kolkata",
    clock_offset_seconds: int = 0,
) -> Tuple[str, str]:
    """Parse a timestamp string, normalize to UTC, and apply a reversible clock offset.

    Formula:
        corrected_utc = original_utc + timedelta(seconds=clock_offset_seconds)

    Returns:
        (corrected_ts_utc_iso, original_ts_utc_iso)
    """
    dt = dateutil.parser.parse(ts_raw)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=ZoneInfo(default_tz))
    original_utc = dt.astimezone(timezone.utc)
    corrected_utc = original_utc + timedelta(seconds=int(clock_offset_seconds or 0))
    return corrected_utc.isoformat(), original_utc.isoformat()


def reverse_clock_offset(corrected_ts_utc: str, clock_offset_seconds: int = 0) -> str:
    """Recover the original UTC timestamp from a corrected UTC timestamp."""
    dt = dateutil.parser.parse(corrected_ts_utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    original_utc = dt - timedelta(seconds=int(clock_offset_seconds or 0))
    return original_utc.isoformat()
