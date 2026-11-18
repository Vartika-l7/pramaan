"""BaseParser abstraction for forensic evidence ingestion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ParsedEvent:
    """Normalised forensic event structure across all parsed evidence sources."""
    evidence_id: str
    source_type: str
    ts_utc: str
    ts_original: str
    tz_assumed: str
    kind: str  # message, call, credit, debit, media, system
    ref: Dict[str, Any]  # line/row/page, byte offsets, file name
    actor: Optional[str] = None
    counterparty: Optional[str] = None
    text: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    location_id: Optional[str] = None


class BaseParser(ABC):
    """Abstract base class for all evidence parsers."""

    @abstractmethod
    def can_parse(self, file_path: Path, filename: str) -> bool:
        """Return True if this parser supports the given file format and content."""
        pass

    @abstractmethod
    def parse(
        self,
        file_path: Path,
        evidence_id: str,
        filename: str,
        default_tz: str = "Asia/Kolkata",
    ) -> List[ParsedEvent]:
        """Parse raw evidence into a list of unified forensic events with source references."""
        pass

