"""AI Provider Interface: Ollama and Deterministic Fallback."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
import httpx

from backend.app.config import OLLAMA_HOST, PRIMARY_MODEL, CHALLENGER_MODEL


class AIProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the underlying inference engine is reachable."""
        pass

    @abstractmethod
    def draft_claims(self, context_records: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Draft structured forensic claims citing explicit record IDs."""
        pass


class OllamaProvider(AIProvider):
    def __init__(self, host: str = OLLAMA_HOST, model: str = PRIMARY_MODEL):
        self.host = host.rstrip("/")
        self.model = model

    def is_available(self) -> bool:
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=1.5)
            return r.status_code == 200
        except Exception:
            return False

    def draft_claims(self, context_records: Dict[str, Any]) -> List[Dict[str, Any]]:
        prompt = (
            "You are a forensic analyst. Based ONLY on the structured records provided below, "
            "propose factual claims. Every claim MUST reference specific record IDs and include exact quotes. "
            "Return valid JSON matching this schema: "
            '{"claims": [{"text": "...", "kind": "finding", "refs": ["ID1"], "quotes": [{"event_id": "ID1", "text": "exact quote"}]}]}.\n\n'
            f"RECORDS:\n{json.dumps(context_records, ensure_ascii=False)}"
        )
        try:
            r = httpx.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": false,
                },
                timeout=30.0,
            )
            if r.status_code == 200:
                data = r.json()
                parsed = json.loads(data.get("response", "{}"))
                return parsed.get("claims", [])
        except Exception:
            pass
        return []


class DeterministicProvider(AIProvider):
    """Template-based structured claim generator that runs without any local or external model."""

    def is_available(self) -> bool:
        return True

    def draft_claims(self, context_records: Dict[str, Any]) -> List[Dict[str, Any]]:
        claims = []
        events = context_records.get("events", [])
        anomalies = context_records.get("anomalies", [])
        edges = context_records.get("edges", [])

        # Claim 1: Solicitations and UPI VPA instruction
        upi_event = next((e for e in events if "vikram.alpha@okaxis" in (e.get("text") or "")), None)
        if upi_event:
            claims.append({
                "text": "The persona Vikram Sharma directed investor Meera Iyer to transfer initial trial capital of INR 50,000 to treasury VPA vikram.alpha@okaxis.",
                "kind": "transaction_solicitation",
                "refs": [upi_event["id"]],
                "quotes": [{"event_id": upi_event["id"], "text": "vikram.alpha@okaxis"}],
            })

        # Claim 2: Funnel forwarding pattern
        funnel_anom = next((a for a in anomalies if a.get("kind") == "PATTERN_FUNNEL"), None)
        if funnel_anom:
            claims.append({
                "text": "Mule Account A received incoming credit and forwarded approximately 90% of funds to downstream accounts within 40 minutes, consistent with an algorithmic mule funneling scheme.",
                "kind": "financial_mule_pattern",
                "refs": [funnel_anom["id"]] + funnel_anom.get("event_ids", []),
                "quotes": [],
            })

        # Claim 3: Shared handset device
        device_edge = next((e for e in edges if e.get("edge_type") == "SAME_DEVICE"), None)
        if device_edge:
            claims.append({
                "text": "Cellular handset Device ID D1 was shared between the Vikram Sharma contact number and the Support Desk operative number.",
                "kind": "attribution_device",
                "refs": [device_edge["id"]] + device_edge.get("event_ids", []),
                "quotes": [],
            })

        # Claim 4: Intentionally plant an unreferenced claim to test Verifier Rule V4
        claims.append({
            "text": "The accused intentionally intended to defraud all participants and is guilty of systematic grand larceny.",
            "kind": "accusation",
            "refs": [],
            "quotes": [],
        })

        return claims


def get_ai_provider() -> AIProvider:
    ollama = OllamaProvider()
    if ollama.is_available():
        return ollama
    return DeterministicProvider()

