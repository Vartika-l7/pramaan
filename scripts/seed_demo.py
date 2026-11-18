"""One-shot demonstration seeder for PRAMAAN.

Ingests all synthetic exhibits from data/case_alpha/ and runs the
entire correlation and anomaly detection pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.app.db import init_db
from backend.app.ingest.service import ingest_file
from backend.app.api.analyze import execute_full_pipeline

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "case_alpha"


def seed(case_id: str = "PRM-2026-0042"):
    print(f"Seeding demo case {case_id}...")
    conn = init_db(case_id)

    files = [
        ("whatsapp_group_alpha_wealth.txt", "whatsapp"),
        ("whatsapp_chat_meera_vikram.txt", "whatsapp"),
        ("bank_statement_meera.pdf", "bank_pdf"),
        ("bank_statement_mule_A.pdf", "bank_pdf"),
        ("bank_statement_mule_B.csv", "bank_csv"),
        ("call_log_device1.csv", "calllog"),
        ("call_log_device2.csv", "calllog"),
        ("screenshot_payment_genuine.png", "image"),
        ("screenshot_withdrawal_edited.jpg", "image"),
        ("screenshot_reused_a.png", "image"),
        ("screenshot_reused_b.jpg", "image"),
    ]

    for fname, stype in files:
        fpath = DATA_DIR / fname
        if fpath.exists():
            with open(fpath, "rb") as f:
                ingest_file(conn, f, filename=fname, source_type=stype)
            print(f"  [+] Ingested {fname}")

    conn.close()

    print("Running full analysis pipeline...")
    res = execute_full_pipeline(case_id)
    print("Seeding complete! Summary:", res)


if __name__ == "__main__":
    seed()

