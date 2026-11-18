"""Linguistic script detection and transliteration helper for Hinglish and Devanagari."""

from __future__ import annotations

import re
from typing import Dict, Any
from indic_transliteration import sanscript
from indic_transliteration.sanscript import SchemeMap, SCHEMES, transliterate

try:
    import langdetect
except ImportError:
    langdetect = None

RE_DEVANAGARI = re.compile(r"[\u0900-\u097F]")
RE_LATIN = re.compile(r"[A-Za-z]")


def detect_script(text: str) -> str:
    """Classify the dominant script of the text: DEVANAGARI, LATIN, or MIXED."""
    if not text:
        return "UNKNOWN"
    dev_count = len(RE_DEVANAGARI.findall(text))
    lat_count = len(RE_LATIN.findall(text))

    if dev_count > 0 and lat_count > 0:
        return "MIXED"
    if dev_count > 0:
        return "DEVANAGARI"
    if lat_count > 0:
        return "LATIN"
    return "OTHER"


def detect_language(text: str) -> str:
    """Detect natural language (hi, en, or hinglish)."""
    if not text or len(text.strip()) < 3:
        return "unknown"
    script = detect_script(text)
    if script == "DEVANAGARI":
        return "hi"
    if script == "MIXED":
        return "hinglish"

    # Latin text can be English or Hinglish
    if langdetect:
        try:
            detected = langdetect.detect(text)
            if detected == "en":
                # Check for common Hinglish marker words
                hinglish_markers = {"hai", "nahi", "karo", "karna", "pakka", "dum", "bhi", "aaj", "payout", "bhai", "sirji"}
                words = set(re.findall(r"\b[a-z]{3,}\b", text.lower()))
                if words & hinglish_markers:
                    return "hinglish"
                return "en"
            return detected
        except Exception:
            return "en"
    return "en"


def transliterate_devanagari_to_latin(text: str) -> str:
    """Transliterate Devanagari text to Latin (ITRANS) for search and entity resolution matching."""
    if not text or not RE_DEVANAGARI.search(text):
        return text
    try:
        converted = transliterate(text, sanscript.DEVANAGARI, sanscript.ITRANS)
        # Clean up ITRANS phonetic markers for closer English matching
        cleaned = converted.lower().replace("aa", "a").replace("ii", "i").replace("uu", "u")
        # Remove terminal virama / schwa artifacts if needed
        cleaned = re.sub(r"[~^]", "", cleaned)
        return cleaned.strip()
    except Exception:
        return text

