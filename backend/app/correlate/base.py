"""Pluggable Correlator base classes and deterministic ID helpers (B4)."""

from __future__ import annotations

import hashlib
import sqlite3
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List


def deterministic_id(prefix: str, *parts: str) -> str:
    """Compute a deterministic 16-char hex ID prefixed by `prefix_`."""
    raw = "|".join(str(p) for p in parts)
    return f"{prefix}_{hashlib.sha256(raw.encode('utf-8')).hexdigest()[:16]}"


@dataclass
class CorrelationEdge:
    """Structured correlation edge emitted by a Correlator plugin."""
    src: str
    dst: str
    edge_type: str
    basis: str  # exact_identifier | time_window | spatial | inferred
    reason_text: str
    strength: float
    event_ids: List[str] = field(default_factory=list)
    tier: str = "LEAD"
    status: str = "LEAD"

    @property
    def id(self) -> str:
        return deterministic_id("edge", self.src, self.dst, self.edge_type, self.basis)


class BaseCorrelator(ABC):
    """Abstract base class for pluggable forensic correlators."""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    def correlate(self, conn: sqlite3.Connection) -> List[CorrelationEdge]:
        pass
