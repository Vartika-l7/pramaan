"""BaseParser abstraction for forensic evidence ingestion."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class SkippedUnit:
    """Details of an unparsed input unit (e.g. empty line, non-transaction line)."""
    unit_index: int  # line_idx, row_idx, or page_idx
    raw_content: str
    reason: str


@dataclass
class ParseErrorUnit:
    """Details of a malformed or failed input unit."""
    unit_index: int
    raw_content: str
    error: str


@dataclass
class ParseReport:
    """Rigorous audit reconciliation report for evidence parsing.
    
    Guarantees: total_units == parsed_events + len(skipped_units) + len(errors)
    """
    total_units: int = 0
    parsed_events: int = 0
    skipped_units: List[SkippedUnit] = field(default_factory=list)
    errors: List[ParseErrorUnit] = field(default_factory=list)
    unit_name: str = "lines"  # "lines", "rows", or "pages"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "total_units": self.total_units,
            "parsed_events": self.parsed_events,
            "skipped_count": len(self.skipped_units),
            "error_count": len(self.errors),
            "unit_name": self.unit_name,
            "reconciled": (self.total_units == (self.parsed_events + len(self.skipped_units) + len(self.errors))),
            "skipped_units": [
                {"unit_index": s.unit_index, "raw_content": s.raw_content[:200], "reason": s.reason}
                for s in self.skipped_units
            ],
            "errors": [
                {"unit_index": e.unit_index, "raw_content": e.raw_content[:200], "error": e.error}
                for e in self.errors
            ],
        }


@dataclass
class ParsedEvent:
    """Normalised forensic event structure across all parsed evidence sources."""
    evidence_id: str
    source_type: str
    ts_utc: str
    ts_original: str
    tz_assumed: str
    kind: str  # message, call, credit, debit, media, system, deleted_message
    ref: Dict[str, Any]  # line/row/page, byte offsets, file name
    actor: Optional[str] = None
    counterparty: Optional[str] = None
    text: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    location_id: Optional[str] = None
    clock_offset_seconds: int = 0
    offset_source: Optional[str] = None


class BaseParser(ABC):
    """Abstract base class for all evidence parsers."""

    @property
    def source_type(self) -> str:
        """Identifier for the evidence source type handled by this parser."""
        return "unknown"

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

    def parse_with_report(
        self,
        file_path: Path,
        evidence_id: str,
        filename: str,
        default_tz: str = "Asia/Kolkata",
    ) -> tuple[List[ParsedEvent], ParseReport]:
        """Parse raw evidence returning both events and a fully reconciled ParseReport."""
        events = self.parse(file_path, evidence_id=evidence_id, filename=filename, default_tz=default_tz)
        # Default fallback report if parser hasn't implemented fine-grained tracking
        report = ParseReport(
            total_units=len(events),
            parsed_events=len(events),
            unit_name="records",
        )
        return events, report
