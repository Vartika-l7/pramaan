# Phase 2B Report: The PS3 Engine (Sources, Space & Time, Correlation, Graph, Event Sequence, Scene Reconstruction)

## What changed
1. **All 7 Heterogeneous Evidence Families (`backend/app/parsers/`)**:
   - Added `TelegramJSONParser` and `GenericSocialJSONParser` (`social_media.py`) for social media exports.
   - Added `CloudLocationHistoryParser` and `CloudActivityCSVParser` (`cloud.py`) for cloud location history and account activity logs.
   - Added `EmailParser` (`email_parser.py`) for `.eml` and `.mbox` files, extracting `From`/`To`/`Date`/`Message-ID`/`Received`/`X-Originating-IP`, hashing attachments as child exhibits, and flagging `Date` vs `Received` drift (`ANOMALY_EMAIL_DATE_INCONSISTENCY`).
   - Added `NetworkLogParser` (`network_log.py`) for CSV (with configurable column mapping) and syslog-style network logs with IP validation via `ipaddress`.
   - Added `CCTVCameraIndexParser` and `CCTVVideoParser` (`cctv.py`) for camera registry CSVs and video exhibits (integrity, provenance, optional `ffprobe` container metadata, time-and-place anchoring; no video analytics).
   - Registered all new plugins in `backend/app/ingest/registry.py` with full `ParseReport` reconciliation.

2. **Time Normalisation & Reversible Clock Offsets (`backend/app/parsers/time_utils.py`, `db.py`)**:
   - Normalised all sources to UTC with `tz_assumed` and `ts_original`.
   - Added `clock_offset_seconds` and `offset_source` to `events`, recorded `CLOCK_OFFSET_RECORDED` in `custody_log`, and applied reversible offsets (`corrected_utc = original_utc + offset`).

3. **Offline Spatial Model (`backend/app/spatial/`)**:
   - Added `locations` and `observations` tables, bundled `indian_cities_gazetteer.csv`, and `tower_registry.csv` loader.
   - Implemented `haversine_km` in `geo.py` and `lookup_ip_location` (returns `"location unknown"` unless a local GeoIP file is configured).
   - Implemented `build_spatial_observations` and `analyze_spatial_relationships` (`CO_LOCATED`, `TRAVELLED`, and `IMPOSSIBLE_TRAVEL` anomaly) in `analyzer.py`.

4. **Pluggable Evidence Correlation Engine (`backend/app/correlate/base.py`, `edges.py`)**:
   - Refactored correlation into 10 `BaseCorrelator` plugins (`SharedIdentifierCorrelator`, `SameDeviceCorrelator`, `MoneyTransferCorrelator`, `CommunicationCorrelator`, `TimeWindowCorrelator`, `SpatialCorrelator`, `SameMediaCorrelator`, `FuzzyNameCorrelator`, `EmailNetworkIPCorrelator`, `LoginFromIPCorrelator`), all emitting deterministic `LEAD` edges with documented strength formulas in `docs/CORRELATION.md`.

5. **Knowledge Graph Generation Framework (`backend/app/correlate/graph.py`, `api/graph.py`)**:
   - Added deterministic SHA-256 node/edge IDs across `entities`, `evidence`, `locations`, `episodes`, `edges`, `OBSERVED_AT`, and `PART_OF_EPISODE`.
   - Added `edge_type` and `query` filters on `GET /api/graph`, plus `GET /api/graph/export?format=json|graphml`.

6. **Automated Event-Sequence Generator (`backend/app/sequence/generator.py`, `api/sequence.py`)**:
   - Deterministically segments the unified timeline into titled episodes (`EP-001`, ...) with original & corrected timestamps, places, actors, devices, source chips, and anomaly flags.
   - Added `POST /api/sequence/generate`, `GET /api/sequence`, and `GET /api/sequence/export?format=json|markdown`.

7. **Digital Crime Scene Reconstruction (`backend/app/scene/reconstructor.py`, `api/scene.py`)**:
   - Added `GET /api/scene` and `GET /api/scene/replay` returning locations, presence intervals (explicitly marking `"not established"` when evidence does not establish presence), events, exhibits, and anomalies.

8. **Extended Synthetic Dataset & Docs (`scripts/make_dataset.py`, `docs/`)**:
   - Added `email_support.eml`, `mailbox_investigator.mbox`, `network_portal_logs.csv`, `cloud_location_history.json`, `cloud_activity_log.csv`, `telegram_alpha_export.json`, `cctv_camera_registry.csv`, placeholder clip `cam_noi_atm_01_clip.mp4`, `tower_registry.csv`, and planted facts `GT-11` through `GT-15` in `ground_truth.json`.
   - Added `docs/GRAPH_SCHEMA.md`, `docs/CORRELATION.md`, `docs/SPATIAL_TEMPORAL.md`, `docs/SEQUENCE.md`.
   - Added working UI hooks for Episodes and Crime Scene Reconstruction in `frontend/src/pages/EventSequencePage.tsx`.

## Why
Problem Statement 3 requires correlating heterogeneous evidence across mobile devices, social media, CCTV, cloud services, financial records, emails, and network logs, constructing temporal and spatial relationships, and reconstructing digital crime scenes. Phase 2B delivers the complete offline, deterministic backend engine and data model for all five deliverables while keeping every inferred link at `LEAD` tier until human approval.

## How to explain this to judges in three sentences
PRAMAAN now ingests and reconciles all seven evidence families from the problem statement—mobile, social media, CCTV, cloud, financial, email, and network logs—into a single UTC-normalised, clock-offset-aware timeline. Using offline haversine spatial analysis and ten pluggable correlators, it automatically flags impossible travel, links email and network IPs, proves that a WhatsApp silence gap hid an admin portal login, and assembles a deterministic knowledge graph. Investigators can then generate titled event-sequence episodes and step through a source-backed digital crime scene reconstruction without ever guessing unverified presence.

## What is still weak
- The frontend hooks for Automated Event Sequence and Crime Scene Reconstruction in `EventSequencePage.tsx` are functional baseline panels; interactive replay controls, clock-offset badges across all views, and GraphML/Markdown download buttons will be polished in Phase 3.
- IP geolocation returns `"location unknown"` offline unless the user provides a local GeoIP database file (`GEOIP_DB_PATH`).
- Cell-tower resolution relies on the synthetic `tower_registry.csv`; real investigations require operator-supplied tower dumps.

## How I tested it
1. Regenerated the extended synthetic dataset (`scripts/make_dataset.py`) with all 15 planted ground-truth facts (`GT-01`..`GT-15`).
2. Ran the full Python test suite (`.venv/bin/pytest -v`), including `tests/test_phase2b_ps3_engine.py` covering all new parsers with reconciliation, clock offsets, haversine/impossible travel, all 10 correlators, graph determinism + GraphML export, sequence determinism + Markdown export, scene reconstruction/replay, and 15/15 ground-truth recall.
3. Ran the frontend TypeScript & Vite production build (`npm --prefix frontend run build`).

### Command Execution Output
```
$ .venv/bin/pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.12.12, pytest-9.2.0, pluggy-1.7.0 -- /Users/tejass/pramaan/.venv/bin/python3.12
cachedir: .pytest_cache
rootdir: /Users/tejass/pramaan
plugins: Faker-40.54.0, anyio-4.16.0
collecting ... 41 items

41 passed in 4.48s
```

```
$ npm --prefix frontend run build
> pramaan-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
✓ 1647 modules transformed.
✓ built in 9.26s
```
