"""Deterministic pattern extraction & validation for PRAMAAN."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import List, Optional
import phonenumbers

KNOWN_UPI_HANDLES = {
    "okaxis", "okhdfcbank", "oksbi", "okicici", "paytm",
    "apl", "ybl", "ibl", "axl", "barodampay", "fbl", "idfcbank", "fakeaxis",
}

# Regex definitions
RE_UPI = re.compile(r"\b([a-zA-Z0-9.\-_]{2,64}@([a-zA-Z]{2,64}))\b", re.IGNORECASE)
RE_IFSC = re.compile(r"\b([A-Z]{4}0[A-Z0-9]{6})\b")
RE_URL = re.compile(r"\b(https?://[a-zA-Z0-9.\-_]+(?:\.[a-zA-Z]{2,})+(?:/[^\s]*)?)\b", re.IGNORECASE)
RE_ACCOUNT = re.compile(r"(?:A/C|A/c|Account|Acc|A/c No\.?|Account No\.?)\s*(?:[:\-#]?\s*)(\d{9,18})\b", re.IGNORECASE)
RE_DEVICE = re.compile(r"\b(D[1-9]|DEV-[A-Za-z0-9]+)\b")
RE_INDIAN_PHONE = re.compile(r"(?:\+91[\-\s]?)?[6-9]\d{4}[\-\s]?\d{5}\b")


@dataclass
class ExtractedEntityMatch:
    type: str  # PHONE, UPI, IFSC, ACCOUNT, DEVICE, URL
    value_raw: str
    value_norm: str
    char_start: int
    char_end: int
    extractor: str = "regex_validator"


def extract_upi_vpas(text: str) -> List[ExtractedEntityMatch]:
    matches = []
    for m in RE_UPI.finditer(text):
        full_vpa = m.group(1).lower()
        handle = m.group(2).lower()
        # Accept if handle suffix matches known UPI provider or standard bank pattern
        if handle in KNOWN_UPI_HANDLES or len(handle) >= 3:
            matches.append(
                ExtractedEntityMatch(
                    type="UPI",
                    value_raw=m.group(1),
                    value_norm=full_vpa,
                    char_start=m.start(1),
                    char_end=m.end(1),
                    extractor="re_upi_vpa",
                )
            )
    return matches


def extract_phones(text: str) -> List[ExtractedEntityMatch]:
    matches = []
    for m in RE_INDIAN_PHONE.finditer(text):
        raw = m.group(0)
        try:
            parsed = phonenumbers.parse(raw, "IN")
            if phonenumbers.is_valid_number(parsed):
                e164 = phonenumbers.format_number(parsed, phonenumbers.PhoneNumberFormat.E164)
                matches.append(
                    ExtractedEntityMatch(
                        type="PHONE",
                        value_raw=raw,
                        value_norm=e164,
                        char_start=m.start(0),
                        char_end=m.end(0),
                        extractor="phonenumbers_e164",
                    )
                )
        except Exception:
            pass
    return matches


def extract_ifsc_codes(text: str) -> List[ExtractedEntityMatch]:
    matches = []
    for m in RE_IFSC.finditer(text):
        matches.append(
            ExtractedEntityMatch(
                type="IFSC",
                value_raw=m.group(1),
                value_norm=m.group(1).upper(),
                char_start=m.start(1),
                char_end=m.end(1),
                extractor="re_ifsc",
            )
        )
    return matches


def extract_accounts(text: str) -> List[ExtractedEntityMatch]:
    matches = []
    for m in RE_ACCOUNT.finditer(text):
        acc = m.group(1)
        matches.append(
            ExtractedEntityMatch(
                type="ACCOUNT",
                value_raw=acc,
                value_norm=acc,
                char_start=m.start(1),
                char_end=m.end(1),
                extractor="re_bank_account",
            )
        )
    return matches


def extract_urls(text: str) -> List[ExtractedEntityMatch]:
    matches = []
    for m in RE_URL.finditer(text):
        url = m.group(1)
        matches.append(
            ExtractedEntityMatch(
                type="URL",
                value_raw=url,
                value_norm=url.lower(),
                char_start=m.start(1),
                char_end=m.end(1),
                extractor="re_url",
            )
        )
    return matches


def extract_devices(text: str) -> List[ExtractedEntityMatch]:
    matches = []
    for m in RE_DEVICE.finditer(text):
        dev = m.group(1)
        matches.append(
            ExtractedEntityMatch(
                type="DEVICE",
                value_raw=dev,
                value_norm=dev.upper(),
                char_start=m.start(1),
                char_end=m.end(1),
                extractor="re_device_id",
            )
        )
    return matches


def extract_all_identifiers(text: str) -> List[ExtractedEntityMatch]:
    """Extract all regex-validated identifiers with character offsets."""
    if not text:
        return []
    results = []
    results.extend(extract_upi_vpas(text))
    results.extend(extract_phones(text))
    results.extend(extract_ifsc_codes(text))
    results.extend(extract_accounts(text))
    results.extend(extract_urls(text))
    results.extend(extract_devices(text))
    return results

