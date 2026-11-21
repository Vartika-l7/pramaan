# PRAMAAN Temporal & Spatial Relationships (`SPATIAL_TEMPORAL.md`)

## 1. Time Normalisation & Reversible Clock Offsets
- Every parsed event records `ts_original` (raw string from source), `tz_assumed` (default `Asia/Kolkata`), `clock_offset_seconds`, `offset_source`, and `ts_utc` (normalised UTC ISO-8601).
- Clock offset formula (`backend/app/parsers/time_utils.py`):
  `corrected_utc = original_utc + timedelta(seconds=clock_offset_seconds)`
- Reversibility: `original_utc = corrected_utc - timedelta(seconds=clock_offset_seconds)`.
- Whenever a non-zero clock offset is applied during parsing, `CLOCK_OFFSET_RECORDED` is appended to the hash-chained `custody_log`.
- Both original and corrected timestamps are preserved and exposed in APIs and UI.

## 2. Offline Spatial Model (`locations` & `observations`)
PRAMAAN operates **100% offline** with zero online geocoding or IP geolocation APIs:
1. **Cell-Tower Registry** (`data/case_alpha/tower_registry.csv`): Resolves `cell_tower_id` to `(lat, lon, accuracy_m)`. *Note: Real-world deployments require official telecom operator tower dumps.*
2. **Cloud Location History**: Uses `(lat, lon, accuracy_m)` directly from JSON exports.
3. **CCTV Camera Registry**: Uses `(lat, lon)` and clip start/end times from `cctv_camera_registry.csv`. *(CCTV support covers integrity, provenance, time-and-place anchoring, and correlation — no video analytics.)*
4. **Bundled Indian Cities Gazetteer** (`backend/app/spatial/indian_cities_gazetteer.csv`): Resolves city mentions in chat text with city-level accuracy radius.
5. **IP Geolocation**: Returns `"location unknown"` unless an offline GeoIP database file is configured via `GEOIP_DB_PATH`.

## 3. Haversine Distance & Derived Relationships
- Great-circle distance is computed in `backend/app/spatial/geo.py:haversine_km` using mean Earth radius `6371.0088 km`.
- **Configurable Thresholds** (`backend/app/config.py`):
  - `COLOCATION_RADIUS_METERS = 500.0` (widened by `acc1 + acc2` of the two observations)
  - `COLOCATION_WINDOW_MINUTES = 30`
  - `IMPOSSIBLE_TRAVEL_SPEED_KMH = 200.0`
- **`CO_LOCATED`**: Two distinct entities/devices within `COLOCATION_RADIUS_METERS + acc1 + acc2` and `COLOCATION_WINDOW_MINUTES`.
- **`TRAVELLED`**: Consecutive observations of the same entity/device separated by more than the combined accuracy radius.
- **`IMPOSSIBLE_TRAVEL`**: High-severity anomaly emitted when `distance_km / elapsed_hours > IMPOSSIBLE_TRAVEL_SPEED_KMH`.
