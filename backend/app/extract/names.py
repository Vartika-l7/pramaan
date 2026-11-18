"""Named Entity Recognition for Indian and Indic Personal Names."""

from __future__ import annotations

import re
from typing import List, Set
from backend.app.config import USE_INDIC_NER
from backend.app.extract.patterns import ExtractedEntityMatch
from backend.app.extract.language import transliterate_devanagari_to_latin

# Comprehensive gazetteer of Indian names encountered in casework & synthetic scenarios
KNOWN_FIRST_NAMES = {
    "vikram", "meera", "anil", "deepak", "sunita", "kabir",
    "riya", "rahul", "amit", "sneha", "priya", "karan", "rajesh",
    "pooja", "rohit", "suresh", "ramesh", "anita", "neha", "arun",
}

KNOWN_LAST_NAMES = {
    "sharma", "iyer", "deshmukh", "rawat", "verma", "anand",
    "patel", "kumar", "rao", "singh", "johar", "gupta", "joshi",
}

HONORIFICS = re.compile(r"\b(?:ji|sir|madam|ma'am|mr\.?|ms\.?|mrs\.?|shri|advocate|dr\.?)\b", re.IGNORECASE)

# Devanagari known names
KNOWN_DEVANAGARI_PERSONS = [
    ("विक्रम शर्मा", "Vikram Sharma"),
    ("विक्रम", "Vikram"),
    ("अनिल देशमुख", "Anil Deshmukh"),
    ("मीरा अय्यर", "Meera Iyer"),
]


def clean_person_name(name: str) -> str:
    """Strip honorifics, titles, and whitespace to obtain normalised canonical person name."""
    cleaned = HONORIFICS.sub("", name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    # Title-case for Latin
    if cleaned and cleaned.isascii():
        cleaned = cleaned.title()
    return cleaned


def extract_persons(text: str) -> List[ExtractedEntityMatch]:
    """Rule-based person name extraction with span tracking."""
    if not text:
        return []

    matches: List[ExtractedEntityMatch] = []

    # 1. Match Devanagari persons
    for dev_name, latin_eq in KNOWN_DEVANAGARI_PERSONS:
        for m in re.finditer(re.escape(dev_name), text):
            matches.append(
                ExtractedEntityMatch(
                    type="PERSON",
                    value_raw=m.group(0),
                    value_norm=clean_person_name(latin_eq),
                    char_start=m.start(0),
                    char_end=m.end(0),
                    extractor="gazetteer_devanagari",
                )
            )

    # 2. Match Latin full names and name variants (e.g. Vikram Sharma, Vikram Sharma Ji, Meera Iyer)
    words = list(re.finditer(r"\b[A-Za-z]+(?:\s+[A-Za-z]+){1,3}\b", text))
    for m in words:
        candidate = m.group(0)
        tokens = [t.lower() for t in candidate.split()]
        # Check if contains a known first name or last name
        has_first = any(t in KNOWN_FIRST_NAMES for t in tokens)
        has_last = any(t in KNOWN_LAST_NAMES for t in tokens)

        if has_first or has_last:
            norm = clean_person_name(candidate)
            if len(norm.split()) >= 1 and len(norm) >= 3:
                matches.append(
                    ExtractedEntityMatch(
                        type="PERSON",
                        value_raw=candidate,
                        value_norm=norm,
                        char_start=m.start(0),
                        char_end=m.end(0),
                        extractor="gazetteer_rules",
                    )
                )

    # 3. Optional IndicNER with transformers if enabled via env
    if USE_INDIC_NER:
        try:
            from transformers import pipeline
            ner_pipe = pipeline("ner", model="ai4bharat/IndicNER", aggregation_strategy="simple")
            ner_results = ner_pipe(text)
            for ent in ner_results:
                if ent.get("entity_group") == "PER":
                    matches.append(
                        ExtractedEntityMatch(
                            type="PERSON",
                            value_raw=ent["word"],
                            value_norm=clean_person_name(ent["word"]),
                            char_start=ent["start"],
                            char_end=ent["end"],
                            extractor="indic_ner_transformers",
                        )
                    )
        except Exception:
            pass

    return matches

