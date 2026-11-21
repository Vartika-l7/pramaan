# PRAMAAN Knowledge Graph Generation Framework (`GRAPH_SCHEMA.md`)

## 1. Deterministic Identifiers
Every node and edge ID is derived deterministically from its canonical attributes using SHA-256 (`deterministic_id(prefix, *parts)` in `backend/app/correlate/base.py`), ensuring identical inputs always produce identical node and edge IDs across runs.

## 2. Node Types
| Node Type | Description | Source |
| :--- | :--- | :--- |
| `PERSON` | Suspects, victims, operatives, and chat participants | Entity extraction & actor fields |
| `PHONE` | Normalised phone numbers (E.164 / Indian mobile) | Entity extraction & CDRs |
| `UPI` | Virtual Payment Addresses (e.g. `vikram.alpha@okaxis`) | Entity extraction |
| `ACCOUNT` | Bank account numbers | Financial parsers & extraction |
| `DEVICE` | Hardware / handset identifiers (e.g. `D1`) | CDRs, cloud logs, location history |
| `IP` | IPv4/IPv6 addresses | Email headers, network logs, cloud activity |
| `EMAIL_ADDRESS` | Email addresses | `.eml`/`.mbox` headers & extraction |
| `URL` | Web domains and portal URLs | Chat & email bodies |
| `LOCATION` | Physical places, cell towers, CCTV cameras, cities | `locations` table |
| `EPISODE` | Segmented event-sequence episodes (`EP-001`, ...) | `episodes` table |
| `EXHIBIT` | Ingested raw evidence exhibits (`EX-001`, ...) | `evidence` table |

## 3. Edge Types & Tiers
All correlation edges default to `tier = LEAD` until promoted to `APPROVED` by a human reviewer. Code-level structural links (`OBSERVED_AT`, `PART_OF_EPISODE`) carry `tier = VERIFIED BY CODE`.

| Edge Type | Basis | Description |
| :--- | :--- | :--- |
| `SAME_IDENTIFIER` | `exact_identifier` | Exact identifier shared across two or more exhibits |
| `SAME_DEVICE` | `exact_identifier` | Multiple personas/numbers/accounts sharing one device ID |
| `USED_DEVICE` | `exact_identifier` | Actor/account linked to a specific device ID |
| `TRANSFERRED_TO` | `exact_identifier` | Financial transfer between accounts |
| `COMMUNICATED_WITH` | `exact_identifier` | Direct calls or DMs between actors |
| `SENT_EMAIL` | `exact_identifier` | Email sent from sender to recipient |
| `TEMPORAL_CO_OCCURRENCE` | `time_window` | Cross-source events within `TIME_WINDOW_CORRELATION_MINUTES` or activity inside a chat silence gap |
| `CO_LOCATED` | `spatial` | Entities/devices within `COLOCATION_RADIUS_METERS + acc1 + acc2` and `COLOCATION_WINDOW_MINUTES` |
| `TRAVELLED` | `spatial` | Movement of an entity/device between consecutive spatial observations |
| `SAME_MEDIA` | `inferred` | Perceptual hash (pHash) match within `PHASH_MAX_DISTANCE` |
| `SAME_PERSON_FUZZY` | `inferred` | Fuzzy/transliterated name similarity >= `FUZZY_NAME_THRESHOLD` |
| `SHARED_IP_CROSS_SOURCE` | `exact_identifier` | Email header IP matching a network log IP |
| `LOGIN_FROM_IP` | `exact_identifier` | Account/user login or connection from an IP address |
| `PATTERN_FUNNEL` | `inferred` | Mule funnel forwarding pattern |
| `OBSERVED_AT` | `spatial` | Entity/device observed at a `LOCATION` |
| `PART_OF_EPISODE` | `time_window` | Actor participation in an `EPISODE` |

## 4. API & Exports
- `GET /api/graph` — supports `type`, `tier`, `min_strength`, `edge_type`, and `query` (1-hop neighbourhood search).
- `GET /api/graph/export?format=json` — Cytoscape JSON export.
- `GET /api/graph/export?format=graphml` — Valid GraphML XML export.
