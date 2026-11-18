"""Acceptance test for Phase 0: Repo Scaffold & Synthetic Dataset."""

import json
from pathlib import Path
import pytest

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "case_alpha"
GROUND_TRUTH_FILE = DATA_DIR / "ground_truth.json"


def test_ground_truth_exists_and_valid():
    assert GROUND_TRUTH_FILE.exists(), f"ground_truth.json not found at {GROUND_TRUTH_FILE}"
    with open(GROUND_TRUTH_FILE, "r", encoding="utf-8") as f:
        gt = json.load(f)
        
    assert gt["case_id"] == "PRM-2026-0042"
    assert "Synthetic case" in gt["synthetic_notice"]
    assert len(gt["planted_facts"]) == 10
    
    fact_ids = [f["id"] for f in gt["planted_facts"]]
    for i in range(1, 11):
        expected_id = f"GT-{i:02d}"
        assert expected_id in fact_ids, f"Missing planted fact {expected_id}"


def test_synthetic_files_exist():
    expected_files = [
        "whatsapp_group_alpha_wealth.txt",
        "whatsapp_chat_meera_vikram.txt",
        "bank_statement_meera.pdf",
        "bank_statement_mule_A.pdf",
        "bank_statement_mule_B.csv",
        "call_log_device1.csv",
        "call_log_device2.csv",
        "screenshot_payment_genuine.png",
        "screenshot_withdrawal_edited.jpg",
        "screenshot_reused_a.png",
        "screenshot_reused_b.jpg",
        "ground_truth.json",
    ]
    for filename in expected_files:
        file_path = DATA_DIR / filename
        assert file_path.exists(), f"Missing synthetic file {filename}"
        assert file_path.stat().st_size > 0, f"File {filename} is empty"


def test_chat_files_content():
    group_chat = (DATA_DIR / "whatsapp_group_alpha_wealth.txt").read_text(encoding="utf-8")
    assert "vikram.alpha@okaxis" in group_chat
    assert "+91 90000 10001" in group_chat
    # Check for Devanagari lines
    assert "विक्रम" in group_chat
    # Check for Hinglish
    assert "profit pakka hai" in group_chat or "safe" in group_chat

    one_to_one = (DATA_DIR / "whatsapp_chat_meera_vikram.txt").read_text(encoding="utf-8")
    assert "50,000" in one_to_one
    assert "1,50,000" in one_to_one
    assert "3,00,000" in one_to_one

