# PRAMAAN Automated Event-Sequence & Crime Scene Reconstruction (`SEQUENCE.md`)

## 1. Automated Event-Sequence Generator
Implemented deterministically in `backend/app/sequence/generator.py` (no AI required):
- Queries all unified `events` ordered by `ts_utc ASC, id ASC`.
- Segments events into numbered episodes (`EP-001`, `EP-002`, ...) whenever:
  - The gap between consecutive events exceeds `EPISODE_GAP_MINUTES` (default `60` minutes), OR
  - The gap exceeds `EPISODE_GAP_MINUTES / 3` AND the event kind group changes AND there is no actor overlap.
- Builds deterministic template titles from the episode's own data (e.g., payment totals, communication participants, network/cloud activity, or physical/media anchors).
- Each step preserves `ts_utc` (corrected), `ts_original`, `clock_offset_seconds`, `offset_source`, `place`, `actors`, `devices`, `source_chip`, and `anomaly_flags`.
- Endpoints:
  - `POST /api/sequence/generate`
  - `GET /api/sequence`
  - `GET /api/sequence/export?format=json|markdown`

## 2. Digital Crime Scene Reconstruction
Implemented deterministically in `backend/app/scene/reconstructor.py`:
- Accepts a time window (`start_ts`, `end_ts`) or `episode_id`.
- `GET /api/scene` returns `locations`, `presence` (each with `source_event_id`, `exhibit_id`, `accuracy_m`), `events`, `exhibits`, and `anomalies`.
- **Zero Guessing Rule**: Any actor active in the window without a spatial observation is explicitly listed with `place_name = "not established"` and `status = "not established"`.
- `GET /api/scene/replay` returns an ordered step-by-step replay for interactive stepping in the UI.
