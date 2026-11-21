"""Email Parser for .eml and .mbox files (B1).

Parses From, To, Date, Message-ID, Received chain, X-Originating-IP,
hashes attachments as child exhibits, and flags Date vs Received inconsistencies.
"""

from __future__ import annotations

import email
import email.policy
import email.utils
import hashlib
import mailbox
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from backend.app.config import EMAIL_DATE_RECEIVED_DRIFT_MINUTES
from backend.app.parsers.base import BaseParser, ParsedEvent, ParseReport, SkippedUnit, ParseErrorUnit

IP_RE = re.compile(r"\b(?:(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\.){3}(?:25[0-5]|2[0-4]\d|[01]?\d\d?)\b")


def _parse_email_message(
    msg: email.message.Message,
    msg_index: int,
    evidence_id: str,
    filename: str,
    fmt: str,
    default_tz: str,
) -> ParsedEvent:
    sender = str(msg.get("From", "")).strip()
    recipient = str(msg.get("To", "")).strip()
    subject = str(msg.get("Subject", "")).strip()
    date_raw = str(msg.get("Date", "")).strip()
    message_id = str(msg.get("Message-ID", "")).strip()
    x_orig_ip = str(msg.get("X-Originating-IP", "")).strip("[] ")

    received_headers = [str(h) for h in msg.get_all("Received", [])]
    received_ips: List[str] = []
    received_timestamps: List[datetime] = []

    for rh in received_headers:
        for ip in IP_RE.findall(rh):
            if ip not in received_ips:
                received_ips.append(ip)
        if ";" in rh:
            ts_part = rh.split(";")[-1].strip()
            try:
                dt = email.utils.parsedate_to_datetime(ts_part)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                received_timestamps.append(dt.astimezone(timezone.utc))
            except Exception:
                pass

    if x_orig_ip:
        m = IP_RE.search(x_orig_ip)
        if m:
            x_orig_ip = m.group(0)
            if x_orig_ip not in received_ips:
                received_ips.insert(0, x_orig_ip)

    # Parse Date header
    date_dt: Optional[datetime] = None
    if date_raw:
        try:
            date_dt = email.utils.parsedate_to_datetime(date_raw)
            if date_dt.tzinfo is None:
                date_dt = date_dt.replace(tzinfo=timezone.utc)
            date_dt = date_dt.astimezone(timezone.utc)
        except Exception:
            date_dt = None

    ts_dt = date_dt or (received_timestamps[-1] if received_timestamps else datetime.now(timezone.utc))
    ts_utc = ts_dt.isoformat()

    # Flag Date vs Received-chain inconsistency
    date_inconsistency: Optional[Dict[str, Any]] = None
    if date_dt and received_timestamps:
        earliest_received = min(received_timestamps)
        drift_minutes = abs((date_dt - earliest_received).total_seconds()) / 60.0
        if drift_minutes > EMAIL_DATE_RECEIVED_DRIFT_MINUTES:
            date_inconsistency = {
                "date_header_utc": date_dt.isoformat(),
                "earliest_received_utc": earliest_received.isoformat(),
                "drift_minutes": round(drift_minutes, 1),
                "threshold_minutes": EMAIL_DATE_RECEIVED_DRIFT_MINUTES,
            }

    # Extract body & attachments (hash attachments as child exhibits)
    body_parts: List[str] = []
    attachments: List[Dict[str, Any]] = []
    if msg.is_multipart():
        for part in msg.walk():
            disp = str(part.get("Content-Disposition", "")).lower()
            att_name = part.get_filename()
            if "attachment" in disp or att_name:
                payload = part.get_payload(decode=True) or b""
                att_sha256 = hashlib.sha256(payload).hexdigest()
                attachments.append({
                    "filename": att_name or f"attachment_{len(attachments)+1}.bin",
                    "content_type": part.get_content_type(),
                    "size_bytes": len(payload),
                    "sha256": att_sha256,
                })
            elif part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    body_parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
    else:
        payload = msg.get_payload(decode=True)
        if payload:
            body_parts.append(payload.decode(msg.get_content_charset() or "utf-8", errors="replace"))

    body_text = " ".join(p.strip() for p in body_parts if p.strip())
    summary_text = f"Email [{subject}] from {sender} to {recipient}: {body_text[:400]}"

    return ParsedEvent(
        evidence_id=evidence_id,
        source_type="email",
        ts_utc=ts_utc,
        ts_original=date_raw or ts_utc,
        tz_assumed=default_tz,
        actor=sender or None,
        counterparty=recipient or None,
        kind="email",
        text=summary_text,
        ref={
            "file": filename,
            "format": fmt,
            "message_index": msg_index,
            "message_id": message_id,
            "subject": subject,
            "from": sender,
            "to": recipient,
            "x_originating_ip": x_orig_ip or None,
            "received_ips": received_ips,
            "received_count": len(received_headers),
            "attachments": attachments,
            "date_received_inconsistency": date_inconsistency,
        },
    )


class EmailParser(BaseParser):
    """Parser for .eml and .mbox email archives."""

    @property
    def source_type(self) -> str:
        return "email"

    def can_parse(self, file_path: Path, filename: str) -> bool:
        return filename.lower().endswith((".eml", ".mbox"))

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
        events: List[ParsedEvent] = []
        skipped: List[SkippedUnit] = []
        errors: List[ParseErrorUnit] = []

        lower = filename.lower()
        if lower.endswith(".eml"):
            raw = file_path.read_bytes()
            total_units = 1
            try:
                msg = email.message_from_bytes(raw, policy=email.policy.compat32)
                if not msg.get("From") and not msg.get("Subject") and not msg.get("Date"):
                    errors.append(ParseErrorUnit(0, raw[:200].decode("utf-8", errors="replace"), "Missing basic email headers"))
                else:
                    events.append(_parse_email_message(msg, 0, evidence_id, filename, "eml", default_tz))
            except Exception as exc:
                errors.append(ParseErrorUnit(0, "", f"EML parse error: {exc}"))
            return events, ParseReport(total_units=total_units, parsed_events=len(events), skipped_units=skipped, errors=errors, unit_name="emails")

        # .mbox
        mbox = mailbox.mbox(str(file_path))
        try:
            keys = list(mbox.keys())
            for idx, key in enumerate(keys):
                try:
                    msg = mbox[key]
                    events.append(_parse_email_message(msg, idx, evidence_id, filename, "mbox", default_tz))
                except Exception as exc:
                    errors.append(ParseErrorUnit(idx, f"mbox_key={key}", f"MBOX message parse error: {exc}"))
        finally:
            mbox.close()

        return events, ParseReport(
            total_units=len(events) + len(skipped) + len(errors),
            parsed_events=len(events),
            skipped_units=skipped,
            errors=errors,
            unit_name="emails",
        )
