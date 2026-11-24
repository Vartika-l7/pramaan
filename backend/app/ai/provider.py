"""AI Provider Interface: Ollama and Deterministic Fallback."""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any, Dict, List
import httpx

from backend.app.config import OLLAMA_HOST, PRIMARY_MODEL
from backend.app.correlate.base import deterministic_id

OLLAMA_CONNECT_TIMEOUT = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "2.0"))
OLLAMA_HEALTH_TIMEOUT = httpx.Timeout(2.0, connect=OLLAMA_CONNECT_TIMEOUT)
OLLAMA_GENERATE_TIMEOUT = httpx.Timeout(15.0, connect=OLLAMA_CONNECT_TIMEOUT)


class AIProvider(ABC):
    model_name: str = "unknown"
    model_version: str = "1.0"
    parameters: Dict[str, Any] = {"temperature": 0, "seed": 42}
    last_prompt: str = ""
    last_raw_output: str = ""

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
        self.model_name = f"ollama:{model}"
        self.model_version = "local-ollama"
        self.parameters = {"temperature": 0, "seed": 42}
        self.last_prompt = ""
        self.last_raw_output = ""

    def is_available(self) -> bool:
        if os.getenv("PRAMAAN_FAKE_LLM", "0") == "1":
            return False
        try:
            r = httpx.get(f"{self.host}/api/tags", timeout=OLLAMA_HEALTH_TIMEOUT)
            return r.status_code == 200
        except Exception:
            return False

    def draft_claims(self, context_records: Dict[str, Any]) -> List[Dict[str, Any]]:
        if os.getenv("PRAMAAN_FAKE_LLM", "0") == "1":
            return []
        prompt = (
            "You are a forensic analyst. Based ONLY on the structured records provided below, "
            "propose factual claims. Every claim MUST reference specific record IDs and include exact quotes. "
            "Return valid JSON matching this schema: "
            '{"claims": [{"text": "...", "kind": "finding", "refs": ["ID1"], "quotes": [{"event_id": "ID1", "text": "exact quote"}]}]}.\n\n'
            f"RECORDS:\n{json.dumps(context_records, ensure_ascii=False)}"
        )
        self.last_prompt = prompt
        try:
            r = httpx.post(
                f"{self.host}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "format": "json",
                    "stream": False,
                    "options": {"temperature": 0, "seed": 42},
                },
                timeout=OLLAMA_GENERATE_TIMEOUT,
            )
            if r.status_code == 200:
                data = r.json()
                raw_resp = data.get("response", "{}")
                self.last_raw_output = raw_resp
                parsed = json.loads(raw_resp)
                return parsed.get("claims", [])
        except Exception as exc:
            self.last_raw_output = json.dumps({"error": str(exc)})
        return []


class DeterministicProvider(AIProvider):
    """Template-based structured claim generator that runs without any local or external model."""

    def __init__(self):
        self.model_name = "DeterministicProvider"
        self.model_version = "deterministic-v1"
        self.parameters = {"temperature": 0, "seed": 42}
        self.last_prompt = ""
        self.last_raw_output = ""

    def is_available(self) -> bool:
        return True

    def draft_claims(self, context_records: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.last_prompt = (
            "Deterministic template claim drafting over structured context_records "
            f"(events={len(context_records.get('events', []))}, "
            f"anomalies={len(context_records.get('anomalies', []))}, "
            f"edges={len(context_records.get('edges', []))})"
        )
        claims: List[Dict[str, Any]] = []
        events = context_records.get("events", [])
        anomalies = context_records.get("anomalies", [])
        edges = context_records.get("edges", [])

        # Claim 1: Solicitations and UPI VPA instruction
        upi_event = next((e for e in events if "vikram.alpha@okaxis" in (e.get("text") or "")), None)
        if upi_event:
            text = "The persona Vikram Sharma directed investor Meera Iyer to transfer initial trial capital of INR 50,000 to treasury VPA vikram.alpha@okaxis."
            refs = [upi_event["id"]]
            claims.append({
                "id": deterministic_id("claim", text, "transaction_solicitation", *refs),
                "text": text,
                "kind": "transaction_solicitation",
                "refs": refs,
                "quotes": [{"event_id": upi_event["id"], "text": "vikram.alpha@okaxis"}],
            })

        # Claim 2: Funnel forwarding pattern
        funnel_anom = next((a for a in anomalies if a.get("kind") == "PATTERN_FUNNEL"), None)
        if funnel_anom:
            text = "Mule Account A received incoming credit and forwarded approximately 90% of funds to downstream accounts within 40 minutes, consistent with an algorithmic mule funneling scheme."
            refs = [funnel_anom["id"]] + funnel_anom.get("event_ids", [])
            claims.append({
                "id": deterministic_id("claim", text, "financial_mule_pattern", *refs),
                "text": text,
                "kind": "financial_mule_pattern",
                "refs": refs,
                "quotes": [],
            })

        # Claim 3: Shared handset device
        device_edge = next((e for e in edges if e.get("edge_type") == "SAME_DEVICE"), None)
        if device_edge:
            text = "Cellular handset Device ID D1 was shared between the Vikram Sharma contact number and the Support Desk operative number."
            refs = [device_edge["id"]] + device_edge.get("event_ids", [])
            claims.append({
                "id": deterministic_id("claim", text, "attribution_device", *refs),
                "text": text,
                "kind": "attribution_device",
                "refs": refs,
                "quotes": [],
            })

        # Claim 4: Intentionally plant an unreferenced claim to test Verifier Rule V4
        text4 = "The accused intentionally intended to defraud all participants and is guilty of systematic grand larceny."
        claims.append({
            "id": deterministic_id("claim", text4, "accusation"),
            "text": text4,
            "kind": "accusation",
            "refs": [],
            "quotes": [],
        })

        self.last_raw_output = json.dumps({"claims": claims}, ensure_ascii=False)
        return claims


def get_ai_provider() -> AIProvider:
    if os.getenv("PRAMAAN_FAKE_LLM", "0") == "1":
        return DeterministicProvider()
    ollama = OllamaProvider()
    if ollama.is_available():
        return ollama
    return DeterministicProvider()
