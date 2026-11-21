# PRAMAAN REST & SSE API Reference (`docs/API.md`)

Base URL (local): `http://127.0.0.1:8000` (all routes accept optional `?case_id=PRM-2026-0042` unless noted).

---

## Health & System
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Engine health check, offline status, and synthetic dataset notice. |
| `GET` | `/api/system/capabilities` | Live status of optional Ollama, Tesseract OCR, PDF engine, IndicNER, and live `network_use.outbound_connections` counter. |
| `GET` | `/api/audit` | Full append-only `custody_log` and human `reviews` audit records. |
| `GET` | `/api/benchmark/results` | Saved synthetic dataset benchmark (`benchmark_results.json`), assistant eval (`assistant_eval_results.json`), and `docs/coverage.txt` summary. |

## Evidence Ingest & Integrity
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/evidence` | Multipart upload (`file`, optional `source_type`, `case_id`). Streams SHA-256, stores `0o444` under `evidence_store/<sha256>`, records `RECEIVED`, `HASHED`, `TIMEZONE_ASSUMED`. |
| `GET` | `/api/evidence` | List ingested exhibits ordered by `exhibit_id`. |
| `GET` | `/api/evidence/{evidence_id}` | Exhibit metadata, `custody_events`, `parse_report`, and extracted `mentions`. |
| `GET` | `/api/evidence/{evidence_id}/raw-preview` | Safe raw preview (text lines, image stream, PDF page 1 text, or binary metadata). |
| `GET` | `/api/integrity/status` | Cached case integrity status (`intact`, `merkle_root`, `chain_intact`, per-exhibit checks). |
| `POST` | `/api/integrity/verify` | Re-hashes every stored exhibit on disk, walks `custody_log`, recomputes Merkle root, and validates manifest Ed25519 signature. |

## Analysis Pipeline, Events, Entities & Anomalies
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/analyze` | Executes the full pipeline: parse pending exhibits, extract entities, detect timeline/spatial anomalies, run 10 correlators + mule funnel, image ELA/EXIF, bank arithmetic, event sequence, and AI claim draft + Rules V1–V5 verification. |
| `GET` | `/api/analyze/stream` | Server-Sent Events (SSE) progress stream for the full analysis pipeline. |
| `GET` | `/api/events` | Unified chronological events (`from`, `to`, `source`, `actor`, `kind`, `limit`). |
| `GET` | `/api/events/{event_id}/source` | Exact source line/row ±5 context lines, SHA-256, and parent exhibit custody events. |
| `GET` | `/api/entities` | List normalized entities with mention counts (`type`, `q`). |
| `GET` | `/api/entities/{entity_id}` | Entity profile and all character-span mentions across exhibits. |
| `GET` | `/api/anomalies` | List detected anomalies (`severity`, `kind`) with `event_ids` and structured `detail`. |

## Authenticity Forensics
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/authenticity/image/{evidence_id}` | EXIF tags, pHash, dimensions, `heatmap_url`, and `ANOMALY_IMAGE_EDITED` detail. |
| `GET` | `/api/authenticity/image/{evidence_id}/heatmap` | Serves the generated Error Level Analysis (ELA) PNG heatmap. |
| `GET` | `/api/authenticity/statement/{evidence_id}` | Row-by-row bank running balance verification (`PASS`/`FAIL` per transaction row). |

## Knowledge Graph & Correlation
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/graph` | Cytoscape JSON graph (`type`, `tier`, `min_strength`, `edge_type`, `query` 1-hop neighborhood). |
| `GET` | `/api/graph/export` | Export graph as `format=json` (Cytoscape JSON) or `format=graphml` (GraphML XML). |
| `GET` | `/api/graph/edges/{edge_id}` | `"Why this link"` explanation: `basis`, `reason_text`, deterministic `strength`, `tier`, and `supporting_events`. |
| `POST` | `/api/graph/edges/{edge_id}/review` | Human review of a graph edge (`decision`: `APPROVED` \| `REJECTED` \| `LEAD`, `note`, `reviewer`). |

## Event Sequence & Crime Scene Reconstruction
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/sequence/generate` | Deterministically segment unified events into numbered episodes (`gap_minutes`). |
| `GET` | `/api/sequence` | Retrieve generated episodes (`EP-001`…). |
| `GET` | `/api/sequence/export` | Export sequence as `format=json` or `format=markdown`. |
| `GET` | `/api/scene` | Digital crime scene reconstruction for `episode_id` or `start_ts`/`end_ts` (explicitly marks unlocated actors `"not established"`). |
| `GET` | `/api/scene/replay` | Ordered step-by-step replay steps with original vs. clock-offset timestamps, places, and anomalies. |

## Claims, Verifier, Assistant & Review Gate
| Method | Path | Description |
| :--- | :--- | :--- |
| `POST` | `/api/ai/draft` | Draft structured `PROPOSED` claims via active AI provider (`OllamaProvider` or `DeterministicProvider`), logged to `ai_runs` + `custody_log`. |
| `POST` | `/api/verify/claims` | Run deterministic Rules V1–V5 over `PROPOSED` claims (`VERIFIED` vs `REMOVED`). |
| `GET` | `/api/claims` | List claims (`status`) with 4-part `explain` payloads. |
| `POST` | `/api/challenge/run` | Generate cross-examination defence objections (`run_challenger_analysis`). |
| `POST` | `/api/assistant/ask` | Retrieval-first forensic Q&A (`question`, `session_id`, `focus_entity`, `language`), verified by Rules V1–V5 and logged to `ai_runs`. |
| `GET` | `/api/assistant/stream` | SSE streaming variant of `/api/assistant/ask`. |
| `GET` | `/api/assistant/starters` | Case-grounded starter question chips. |
| `GET` | `/api/assistant/leads` | Suggest next investigative leads (`LEAD` tier) with `explain` payloads. |
| `GET` | `/api/assistant/challenge` | Defence cross-examination objections with `explain` payloads. |
| `GET` | `/api/assistant/diary` | Deterministic date-by-date case diary summary (`from_ts`, `to_ts`). |
| `POST` | `/api/assistant/promote` | Verifies an assistant answer against Rules V1–V5 (requires non-empty `refs`) and inserts into the Review Queue. |
| `GET` | `/api/review/queue` | Items awaiting human approval (`VERIFIED` claims and `LEAD` edges) plus approval progress counts. |
| `POST` | `/api/review/{item_id}` | Submit human review decision (`APPROVED`, `REJECTED`, `EDIT`, `LEAD`). |
| `POST` | `/api/review/bulk` | Bulk approve/reject a list of claims or edges. |

## Court Report & Signed Package
| Method | Path | Description |
| :--- | :--- | :--- |
| `GET` | `/api/report/preview` | Live preview of **human-approved** claims/edges, event sequence, Merkle root, Section 63 BSA draft (`DRAFT — HUMANS MUST SIGN`), and QR payload. |
| `POST` | `/api/report/build` | Assemble `report.pdf`, `manifest.json`, `manifest.sig` (Ed25519), `public_key.pem`, `audit_log.json`, `evidence_hashes.csv`, `defence_weakness_report.html`, `verifier.py`, and ZIP. |
| `GET` | `/api/report/download` | Download `case_<id>_package.zip`. |
| `GET` | `/api/report/pdf` | View/download `report.pdf`. |
| `POST` | `/api/report/verify` | Run `verifier/verifier.py --package ...` as a subprocess and return real `PASS`/`FAIL`, `returncode`, and full output. |
