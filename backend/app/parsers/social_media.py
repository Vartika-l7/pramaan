"""Social Media Parsers: Telegram JSON export and Generic Social Media JSON export (B1)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport, SkippedUnit, ParseErrorUnit
from backend.app.parsers.time_utils import normalise_to_utc


def _flatten_telegram_text(text_field: Any) -> str:
    """Telegram Desktop exports 'text' as either a string or a list of strings/entity dicts."""
    if isinstance(text_field, str):
        return text_field
    if isinstance(text_field, list):
        parts: List[str] = []
        for item in text_field:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return str(text_field or "")


class TelegramJSONParser(BaseParser):
    """Parser for Telegram Desktop JSON exports (result.json)."""

    @property
    def source_type(self) -> str:
        return "social_telegram"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        if not filename.lower().endswith(".json"):
            return False
        try:
            data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
            return isinstance(data, dict) and isinstance(data.get("messages"), list)
        except Exception:
            return False

    def parse(
        self,
        file_path: Path,
        evidence_id: str,
        filename: str,
        default_tz: str = "Asia/Kolkata",
    ) -> List[ParsedEvent]:
        events, _ = self.parse_with_report(file_path, evidence_id, filename, default_tz)
        return events

    def parse_with_report(
        self,
        file_path: Path,
        evidence_id: str,
        filename: str,
        default_tz: str = "Asia/Kolkata",
    ) -> Tuple[List[ParsedEvent], ParseReport]:
        data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
        if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
            raise ValueError("Invalid Telegram JSON export: missing 'messages' list.")

        chat_name = data.get("name", filename)
        messages = data["messages"]
        events: List[ParsedEvent] = []
        skipped: List[SkippedUnit] = []
        errors: List[ParseErrorUnit] = []

        for idx, msg in enumerate(messages):
            if not isinstance(msg, dict):
                errors.append(ParseErrorUnit(idx, str(msg)[:200], "Message entry is not a JSON object"))
                continue

            ts_raw = msg.get("date") or msg.get("date_unixtime")
            if not ts_raw:
                skipped.append(SkippedUnit(idx, json.dumps(msg)[:200], "missing_timestamp"))
                continue

            try:
                if str(ts_raw).isdigit():
                    dt = datetime.fromtimestamp(int(ts_raw), tz=timezone.utc)
                    ts_utc = dt.isoformat()
                    ts_orig = str(ts_raw)
                else:
                    ts_orig = str(ts_raw)
                    ts_utc, _ = normalise_to_utc(ts_orig, default_tz=default_tz)
            except Exception as exc:
                errors.append(ParseErrorUnit(idx, json.dumps(msg)[:200], f"Invalid timestamp: {exc}"))
                continue

            text_str = _flatten_telegram_text(msg.get("text", "")).strip()
            media_ref = msg.get("photo") or msg.get("file") or msg.get("media_type")
            msg_type = msg.get("type", "message")
            actor = msg.get("from") or msg.get("actor") or "Unknown"

            if not text_str and not media_ref and msg_type == "service":
                text_str = f"[Service: {msg.get('action', 'event')}]"
                kind = "system"
            elif media_ref and not text_str:
                text_str = f"[Media: {media_ref}]"
                kind = "media"
            else:
                kind = "system" if msg_type == "service" else "message"

            events.append(
                ParsedEvent(
                    evidence_id=evidence_id,
                    source_type=self.source_type,
                    ts_utc=ts_utc,
                    ts_original=ts_orig,
                    tz_assumed=default_tz,
                    actor=str(actor),
                    counterparty=str(chat_name),
                    kind=kind,
                    text=text_str,
                    ref={
                        "file": filename,
                        "message_index": idx,
                        "telegram_id": msg.get("id"),
                        "chat_name": chat_name,
                        "media_ref": media_ref,
                    },
                )
            )

        report = ParseReport(
            total_units=len(messages),
            parsed_events=len(events),
            skipped_units=skipped,
            errors=errors,
            unit_name="messages",
        )
        return events, report


class GenericSocialJSONParser(BaseParser):
    """Parser for generic social media JSON exports (posts and direct messages)."""

    @property
    def source_type(self) -> str:
        return "social_generic"

    def _extract_items(self, data: Any) -> Optional[List[Tuple[str, Dict[str, Any]]]]:
        if isinstance(data, list):
            if data and all(isinstance(x, dict) and "timestamp" in x and ("author" in x or "user" in x) for x in data[:5]):
                return [("post", x) for x in data]
            return None
        if isinstance(data, dict):
            items: List[Tuple[str, Dict[str, Any]]] = []
            found = False
            for key, default_kind in [("posts", "post"), ("direct_messages", "dm"), ("messages", "dm"), ("items", "post")]:
                if isinstance(data.get(key), list):
                    found = True
                    for x in data[key]:
                        if isinstance(x, dict):
                            items.append((default_kind, x))
            if found and items:
                return items
        return None

    def can_parse(self, file_path: Path, filename: str) -> bool:
        if not filename.lower().endswith(".json"):
            return False
        try:
            data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
            if isinstance(data, dict) and "messages" in data and "name" in data and any(
                isinstance(m, dict) and ("date" in m or "date_unixtime" in m) for m in data.get("messages", [])[:3]
            ):
                return False  # Telegram format takes precedence
            if isinstance(data, dict) and isinstance(data.get("locations"), list):
                return False  # Cloud location history takes precedence
            return self._extract_items(data) is not None
        except Exception:
            return False

    def parse(
        self,
        file_path: Path,
        evidence_id: str,
        filename: str,
        default_tz: str = "Asia/Kolkata",
    ) -> List[ParsedEvent]:
        events, _ = self.parse_with_report(file_path, evidence_id, filename, default_tz)
        return events

    def parse_with_report(
        self,
        file_path: Path,
        evidence_id: str,
        filename: str,
        default_tz: str = "Asia/Kolkata",
    ) -> Tuple[List[ParsedEvent], ParseReport]:
        data = json.loads(file_path.read_text(encoding="utf-8", errors="replace"))
        items = self._extract_items(data)
        if items is None:
            raise ValueError("Invalid generic social media JSON: expected list or {posts, direct_messages}.")

        events: List[ParsedEvent] = []
        skipped: List[SkippedUnit] = []
        errors: List[ParseErrorUnit] = []

        for idx, (default_kind, item) in enumerate(items):
            ts_raw = item.get("timestamp")
            author = item.get("author") or item.get("user")
            if not ts_raw or not author:
                errors.append(ParseErrorUnit(idx, json.dumps(item)[:200], "Missing required 'timestamp' or 'author'"))
                continue

            try:
                ts_utc, _ = normalise_to_utc(str(ts_raw), default_tz=default_tz)
            except Exception as exc:
                errors.append(ParseErrorUnit(idx, json.dumps(item)[:200], f"Invalid timestamp: {exc}"))
                continue

            text_val = str(item.get("text") or "").strip()
            media_refs = item.get("media_references") or item.get("media") or []
            if not text_val and not media_refs:
                skipped.append(SkippedUnit(idx, json.dumps(item)[:200], "empty_post_or_message"))
                continue

            kind = str(item.get("kind") or default_kind)
            recipient = item.get("recipient") or item.get("to")
            events.append(
                ParsedEvent(
                    evidence_id=evidence_id,
                    source_type=self.source_type,
                    ts_utc=ts_utc,
                    ts_original=str(ts_raw),
                    tz_assumed=default_tz,
                    actor=str(author),
                    counterparty=str(recipient) if recipient else None,
                    kind=kind,
                    text=text_val or f"[Media: {media_refs}]",
                    ref={
                        "file": filename,
                        "item_index": idx,
                        "platform": item.get("platform", "social_media"),
                        "media_references": media_refs,
                    },
                )
            )

        report = ParseReport(
            total_units=len(items),
            parsed_events=len(events),
            skipped_units=skipped,
            errors=errors,
            unit_name="items",
        )
        return events, report
