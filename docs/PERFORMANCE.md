# PRAMAAN Performance Measurements (`docs/PERFORMANCE.md`)

> **Measurement Label:** `synthetic dataset, this machine`
> All figures below were computed directly by [`scripts/benchmark.py`](../scripts/benchmark.py) and [`scripts/eval_assistant.py`](../scripts/eval_assistant.py) against the synthetic dataset (`data/case_alpha`, Case `PRM-2026-0042`). No numbers are estimated or extrapolated.

---

## Test Machine Specifications
- **Processor:** Apple M4 (10 CPU cores)
- **Memory:** 16 GB RAM (`17,179,869,184` bytes)
- **Operating System:** macOS 15.6 (`arm64`, build `24G84`)
- **Python Runtime:** Python 3.12.12
- **Node.js Runtime (for frontend build):** v24.15.0

---

## Measured Pipeline Throughput & Latency (`synthetic dataset, this machine`)

| Metric | Measured Value | Scope / Notes |
| :--- | :--- | :--- |
| **SHA-256 Hash Throughput** | **1,066.5 MB/s** (**0.96 s/GB**) | Measured over 100 MB (10 × 10 MB streaming chunks) via `hash_bytes()` |
| **Parse Throughput (WhatsApp)** | **709.2 messages/sec** | 760 total events across 20 files parsed in `0.995s` |
| **Parse Throughput (All Sources)** | **763.5 events/sec** | All 7 source families (`whatsapp`, `social_telegram`, `calllog`, `bank_pdf`, `bank_csv`, `cloud_location`, `cloud_activity`, `email`, `network_log`, `cctv_index`, `cctv_video`, `image`) |
| **Time to First Graph** | **1.252 s** | Cold `:memory:` DB from ingest start through entity extraction, anomalies, all 10 correlators, and `get_cytoscape_graph()` (`170` nodes, `139` edges) |
| **Full Analysis Time (Demo Case)** | **1.402 s** | End-to-end: ingest + parse (20 files) + extract + timeline + spatial + correlate + funnel + image ELA/EXIF + bank math + sequence (`16` episodes) + scene + deterministic claim verification |
| **HTTP Demo Run (Live Server)** | **0.14 s** upload · **1.83 s** `/api/analyze` · **0.47 s** `/api/report/build` | Measured over local HTTP against `uvicorn` (`OFFLINE=1`) |

---

## Accuracy & Recall (`synthetic dataset, this machine`)

| Metric | Measured Value | Notes |
| :--- | :--- | :--- |
| **Entity Extraction (Precision / Recall / F1)** | **100.0% / 100.0% / 100.0%** | Against the 10 expected planted entities in `ground_truth.json` (naive regex baseline F1: `75.0%`, `+25.0%`) |
| **Planted Ground-Truth Fact Recall** | **15 / 15 (100.0%)** | `GT-01` through `GT-15` detected deterministically |
| **Claim Verifier (Deterministic Rules V1–V5)** | **3 kept, 1 removed** | Deliberately unsourced claim removed by Rule V4 |
| **Assistant Eval (30 questions, deterministic mode)** | `citation_precision=0.682`, `keyword_recall=0.500`, `unanswerable_refusal_rate=1.000`, `verifier_removed_share=0.0` | Measured by `scripts/eval_assistant.py` on `tests/assistant_eval.json` (22 answerable, 8 unanswerable) |
| **Backend Statement Coverage** | **62.0%** | Measured by `scripts/run_all_checks.py` (`docs/coverage.txt`) |

Raw JSON outputs are persisted in:
- [`data/case_alpha/benchmark_results.json`](../data/case_alpha/benchmark_results.json)
- [`data/case_alpha/assistant_eval_results.json`](../data/case_alpha/assistant_eval_results.json)
- [`docs/coverage.txt`](coverage.txt)
