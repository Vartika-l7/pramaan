# PRAMAAN Evidence Correlation Engine (`CORRELATION.md`)

## 1. Pluggable Correlator Architecture
Correlation is implemented as a registry of `BaseCorrelator` plugins (`DEFAULT_CORRELATORS` in `backend/app/correlate/edges.py`). Each correlator queries SQLite and emits `CorrelationEdge` objects with:
- Deterministic `id` (`sha256(src|dst|edge_type|basis)[:16]`)
- `basis`: `exact_identifier`, `time_window`, `spatial`, or `inferred`
- `reason_text`: human-readable explanation
- `event_ids`: supporting event IDs
- `strength`: deterministic score in `[0.0, 1.0]`
- `tier`: `LEAD` (until human-approved)

## 2. Deterministic Strength Formulas
| Correlator | Edge Type | Formula |
| :--- | :--- | :--- |
| `SharedIdentifierCorrelator` | `SAME_IDENTIFIER` | `1.0` (exact normalised string match across distinct exhibits) |
| `SameDeviceCorrelator` | `SAME_DEVICE`, `USED_DEVICE` | `0.95` (exact `device_id` match) |
| `MoneyTransferCorrelator` | `TRANSFERRED_TO` | `0.90` (explicit transfer narration & amount > 0) |
| `CommunicationCorrelator` | `COMMUNICATED_WITH`, `SENT_EMAIL` | `min(0.95, 0.65 + 0.05 * event_count)` |
| `TimeWindowCorrelator` | `TEMPORAL_CO_OCCURRENCE` | `0.88` for activity inside `ANOMALY_CHAT_GAP`; `max(0.5, 1.0 - dt_min / (2 * W))` for cross-source proximity within `W = TIME_WINDOW_CORRELATION_MINUTES` |
| `SpatialCorrelator` | `CO_LOCATED`, `TRAVELLED` | `0.85` for `CO_LOCATED`; `0.80` for `TRAVELLED` |
| `SameMediaCorrelator` | `SAME_MEDIA` | `1.0 - (hamming_distance / 64.0)` |
| `FuzzyNameCorrelator` | `SAME_PERSON_FUZZY` | `SequenceMatcher(norm(a), norm(b)).ratio()` after Devanagari transliteration & honorific stripping (`>= FUZZY_NAME_THRESHOLD`) |
| `EmailNetworkIPCorrelator` | `SHARED_IP_CROSS_SOURCE` | `0.95` (exact IP match between email `Received`/`X-Originating-IP` and network log) |
| `LoginFromIPCorrelator` | `LOGIN_FROM_IP` | `min(0.98, 0.80 + 0.04 * event_count)` |
| `detect_mule_funnel_pattern` | `PATTERN_FUNNEL` | `0.95` (credit followed by debits `>= MULE_FORWARD_RATIO_MIN` within `MULE_FUNNEL_WINDOW_HOURS`) |
