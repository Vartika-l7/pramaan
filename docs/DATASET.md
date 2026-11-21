# PRAMAAN Synthetic Dataset & Ground Truth (`docs/DATASET.md`)

> **Fictional & Synthetic Notice:** Case `PRM-2026-0042` (*Alpha Wealth Club Investment Fraud*) in `data/case_alpha/` is a **100% synthetic dataset** generated deterministically by [`scripts/make_dataset.py`](../scripts/make_dataset.py). All persons, organizations, phone numbers (`+91 90000 10001..10004`), bank account numbers (`912345678901..903`), UPI IDs (`vikram.alpha@okaxis`), email domains (`example.com`), and IPv4 addresses (`203.0.113.0/24` TEST-NET-3) are completely fictional.

---

## 1. Evidence Files Across All 7 Problem Statement Source Families

| Exhibit File | Source Family | Parser (`backend/app/parsers/`) | Purpose in Scenario |
| :--- | :--- | :--- | :--- |
| `call_log_device1.csv` | Mobile | `CallLogParser` | CDR for device `D1`; Noida towers moving to Jaipur |
| `call_log_device2.csv` | Mobile | `CallLogParser` | Support desk CDR recording calls from shared device `D1` |
| `whatsapp_group_alpha_wealth.txt` | Social Media | `WhatsAppParser` | ~600 Hinglish + Devanagari messages; night-3 6h 14m gap & out-of-order message |
| `whatsapp_chat_meera_vikram.txt` | Social Media | `WhatsAppParser` | 1:1 solicitation instructing Meera to transfer INR 50k, 1.5L, 3L to `vikram.alpha@okaxis` |
| `telegram_alpha_export.json` | Social Media | `TelegramJSONParser` | Telegram VIP channel export referencing `vikram.alpha@okaxis` |
| `cctv_camera_registry.csv` | CCTV | `CCTVCameraIndexParser` | `CAM-NOI-ATM-01` at Noida Sector 62 ATM (`+252s` / `+4m12s` clock offset) |
| `cam_noi_atm_01_clip.mp4` | CCTV | `CCTVVideoParser` | Synthetic CCTV clip exhibit anchored by hash & metadata (no video analytics) |
| `screenshot_payment_genuine.png` | Media | `ImageParser` | Genuine UPI payment screenshot (INR 50,000) |
| `screenshot_withdrawal_edited.jpg` | Media | `ImageParser` | Edited screenshot (`PixelMod Editor Pro v2.4`, modified > created, ELA hotspot) |
| `screenshot_withdrawal_edited.png` | Media | `ImageParser` | PNG companion of edited withdrawal graphic |
| `screenshot_reused_a.png` | Media | `ImageParser` | Promo certificate image (PNG) |
| `screenshot_reused_b.jpg` | Media | `ImageParser` | Re-compressed JPEG copy of same promo certificate (pHash match) |
| `cloud_location_history.json` | Cloud | `CloudLocationHistoryParser` | Device `D1` GPS observation in Jaipur at `14:00 IST` (20 min before Noida ATM) |
| `cloud_activity_log.csv` | Cloud | `CloudActivityCSVParser` | Cloud logins for `vikram.sharma@example.com` and `riya.support@example.com` on IP `203.0.113.45` & `D1` |
| `bank_statement_meera.pdf` | Financial | `BankPDFParser` | Victim Meera Iyer's HDFC statement showing 3 UPI debits to `vikram.alpha@okaxis` |
| `bank_statement_mule_A.pdf` | Financial | `BankPDFParser` | Mule A (Deepak Rawat) PNB statement: funnel pattern + broken running balance on row 8/10 |
| `bank_statement_mule_B.csv` | Financial | `BankCSVParser` | Mule B (Sunita Verma) CSV statement receiving IMPS forwards from Mule A |
| `email_support.eml` | Email | `EmailParser` | Support email with `X-Originating-IP` / `Received` IP `203.0.113.45` |
| `mailbox_investigator.mbox` | Email | `EmailParser` | Two-message `.mbox` including deliberate 72h `Date` vs `Received` header drift |
| `network_portal_logs.csv` | Network | `NetworkLogParser` | Portal logs from `203.0.113.45` including `ADMIN_PORTAL_LOGIN` at `01:30 IST` inside chat gap |

### Non-Evidence Reference & Evaluation Files in `data/case_alpha/`
- `tower_registry.csv` — Offline cell-tower lat/lon/accuracy lookup table.
- `ground_truth.json` — Machine-readable ground truth (`GT-01`..`GT-15`).
- `benchmark_results.json` — Measured output from `scripts/benchmark.py`.
- `assistant_eval_results.json` — Measured output from `scripts/eval_assistant.py`.

---

## 2. Planted Ground-Truth Facts (`GT-01` through `GT-15`)

| ID | Fact Name | Expected Detection / Mechanism |
| :--- | :--- | :--- |
| `GT-01` | Cross-Source Identifier Link | `SAME_IDENTIFIER`: `vikram.alpha@okaxis` shared across WhatsApp chats, Telegram, and Mule A bank statement |
| `GT-02` | Mule Funnel Pattern | `PATTERN_FUNNEL`: Mule A forwards ~90% of incoming credits to Mule B & C within 40 minutes |
| `GT-03` | Shared Device Identifier | `SAME_DEVICE`: Device `D1` shared by Vikram (`+91 90000 10001`) and Support Desk (`+91 90000 10002`) |
| `GT-04` | Chat Timeline Gap | `ANOMALY_CHAT_GAP`: 6h 14m (`374m`) silence gap on night 3 (`2026-03-14 23:45` to `2026-03-15 05:59` IST) |
| `GT-05` | Out-of-Order Timestamp | `ANOMALY_OUT_OF_ORDER`: `15/03/2026 14:18` appears after `14:35` in group chat |
| `GT-06` | Edited Screenshot Metadata & ELA | `ANOMALY_IMAGE_EDITED`: `PixelMod Editor Pro v2.4`, modified > created, elevated ELA hotspot |
| `GT-07` | Reused Media Across Conversations | `SAME_MEDIA`: `screenshot_reused_a.png` and `screenshot_reused_b.jpg` match within `pHash <= 2` |
| `GT-08` | Bank Statement Balance Mismatch | `ANOMALY_BALANCE_MISMATCH`: Mule A statement prints `2,20,000.00` vs expected `1,90,000.00` |
| `GT-09` | Fuzzy Name Variant Resolution | `SAME_PERSON_FUZZY`: `Vikram Sharma`, `Vikram Sharma Ji`, and `विक्रम शर्मा` linked as `LEAD` |
| `GT-10` | Spatial Cell Tower Movement | `SPATIAL_THREAD`: Call logs show `D1` moving from `TOW-NOI-042` (Noida) to `TOW-JAI-108` (Jaipur) |
| `GT-11` | Impossible Travel Anomaly | `IMPOSSIBLE_TRAVEL`: `D1` in Jaipur (`14:00 IST`) and Noida Sector 62 ATM (`14:20 IST`, `> 200 km/h`) |
| `GT-12` | Email Header IP Matched to Network Log | `SHARED_IP_CROSS_SOURCE`: IP `203.0.113.45` in `email_support.eml` matches `network_portal_logs.csv` |
| `GT-13` | Portal Login During Chat Silence Gap | `TEMPORAL_CO_OCCURRENCE`: `ADMIN_PORTAL_LOGIN` (`2026-03-15 01:30+05:30`) occurs inside `GT-04` gap |
| `GT-14` | CCTV Clock Offset Alignment | `CLOCK_OFFSET_RECORDED`: `CAM-NOI-ATM-01` applies `+252s` (`+4m12s`) aligning `14:15:48` to `14:20:00 IST` |
| `GT-15` | Two Personas Sharing IP and Device | `LOGIN_FROM_IP` / `SAME_DEVICE`: `vikram.sharma@example.com` and `riya.support@example.com` share IP `203.0.113.45` and `D1` |
