# PRAMAAN UI Audit (Before Phase 3)

Visual and structural audit conducted against the running application at `1440x900` and `1280x720` (screenshots saved in `docs/ui/before/`), plus component/CSS inspection.

## 1. Design System & Offline Compliance Defects
1. **External CDN Font Import (`frontend/src/styles/tokens.css:1`)**: Imports `Fraunces` and `DM Sans` from `https://fonts.googleapis.com/...`, violating the strict 100% offline rule and the Phase 3 typography spec (`Source Serif 4`, `IBM Plex Sans`, `IBM Plex Mono` via `@fontsource`).
2. **Wrong Palette & Decorative Colours (`tokens.css`, `tailwind.config.js`)**: Uses `#F4F0E7` ivory, `#315FCE` cobalt, `#F05A3A` tomato, `#D6E36A` lime, `#B9A4D8` lavender, `#E7B75B` ochre instead of the specified paper `#FBF8F3`, panels `#FFFFFF`, hairline borders `#E8D9CC`, ink `#2B1B17`, muted `#7A5C52`, vermilion `#DB4A2B`, code-verified slate teal `#2E5E6E`, lead amber `#C97B1A`, and approved green `#3F7D58`.
3. **Decorative Sparkle Icons**: `Sparkles` icon used in `OverviewPage.tsx`, `KnowledgeGraphPage.tsx`, `ReviewQueuePage.tsx`, and `AssistantPage.tsx`.
4. **Inconsistent Radii & Shadows**: Mix of `rounded-xl`, `rounded-lg`, `rounded-[4px]`, `rounded-[3px]`, `shadow-xl`, `shadow-2xl`, `shadow-sm` instead of consistent 6px radii (`rounded`) and hairline rules.

## 2. Navigation, Chrome & Workspace Separation Defects
5. **Seven Pages Instead of Six**: Left rail lists 7 pages (`Overview`, `Evidence Vault`, `Knowledge Graph`, `Event Sequence`, `Review Queue`, `Case Package`, `Assistant`) under one flat `CORE MODULES` heading. Review Queue and Case Package are disconnected instead of forming the single `Review and Report` gate.
6. **No Two-Workspace Visual Identity**: All pages use cobalt blue `#315FCE`. There is no separation between **Workspace 1: Evidence and Court Package** (slate teal `#2E5E6E`) and **Workspace 2: Investigation** (lead amber `#C97B1A`), and no thin workspace label at the top of each page.
7. **Top `CaseBar` Text Wrapping (`overview_1440x900.png`, `1280x720`)**: `PRM-2026-0042` wraps onto two lines (`PRM-2026-` / `0042`), `SYNTHETIC DOSSIER` wraps onto two lines, `CHAIN INTACT`, `0 exhibits`, `root genesis`, and `Run Pipeline` wrap awkwardly because of missing `whitespace-nowrap` and tight horizontal spacing.

## 3. Page-by-Page Defects
8. **Overview (`OverviewPage.tsx`)**:
   - **Hardcoded / Invented Numbers**: Displays hardcoded `745` events, `59` entities, `25` anomalies, `94.7%` F1 benchmark, `10/10 RECOVERED`, and a hardcoded `Incident Reconstruction Timeline` even when the database has 0 exhibits.
   - **Prohibited Stat Tile Grid**: Uses a 4-column big-number stat grid (`01 / EVENTS`, `02 / ENTITIES`, `03 / ANOMALIES`, `04 / BENCHMARK`) instead of two side-by-side workspace panels with one button each and a short "Next steps" list.
9. **Evidence (`EvidenceVaultPage.tsx`)**:
   - Missing source-family filter (mobile, social media, CCTV, cloud, financial, email, network).
   - Missing `Parse report` and `Mentions` tabs in the detail drawer (only `custody` and `authenticity` exist).
   - Missing inline "Re-hash in browser" action on exhibit detail/rows.
   - Oversized empty dropzone dominates the top of the page.
10. **Review and Report (`ReviewQueuePage.tsx` + `CasePackagePage.tsx`)**:
    - Split across two separate routes (`/review` and `/package`).
    - Review queue lacks keyboard shortcuts (`A/R/E/J/K`), progress indicator, and bulk approve for groups.
    - Case Package uses a **hardcoded** `runVerifierDemo()` string instead of running the real standalone `verifier.py` or displaying real saved trust/benchmark results.
    - Missing live preview of the court report (approved items only, findings table with exhibit ID & hash, event sequence, Section 63 draft certificate marked "draft, humans must sign", QR code).
11. **Knowledge Graph (`KnowledgeGraphPage.tsx`)**:
    - Missing slim left filter column (node type, tier, strength, time range) and search box; instead has a wide right-hand entities list that obscures the graph at `1280x720`.
    - Missing "Ask about this" action on nodes to jump to Assistant with focus.
    - Missing empty state when 0 nodes exist (renders blank beige canvas).
12. **Reconstruction (`EventSequencePage.tsx`)**:
    - Missing the **Locations** coordinate canvas (plain offline canvas with place names, accuracy circles, movement lines, impossible-travel flags — no map tiles or country/state outlines).
    - Missing the **Scene Replay** control (episode/time-window selector, step/scrub controls synced with timeline, locations, and mini-graph highlight).
    - Missing filters for person, account, device, date, and original vs. corrected clock-offset display.
    - Renders a large blank white box when 0 events are loaded.
13. **Assistant (`AssistantPage.tsx`)**:
    - Missing two-pane layout (conversation on left, dedicated "Evidence" pane on right showing cited exhibit chips, exact quotes, hashes).
    - Uses `Sparkles` icon and `alert()` on promote.
14. **Global Source Viewer & Linked Views**:
    - Missing global `selectedEntityId` / `selectedEventId` / `selectedLocationId` cross-view selection highlighting across Graph, Reconstruction, and Assistant.
    - Hash chips lack standardized `8...4` truncation with tooltip + copy across all tables/cards.
    - Missing skeleton loading states and consistent error states across pages.
