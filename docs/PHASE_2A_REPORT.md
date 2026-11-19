# Phase 2A Report: Scope Reduction & Focused Architecture

## What changed
1. **Component Inventory & Audit (`docs/SCOPE.md`)**:
   - Conducted a comprehensive audit of all backend components, algorithms, API endpoints, and frontend pages against the five Problem Statement 3 (PS3) deliverables:
     1. Evidence correlation engine
     2. Knowledge graph generation framework
     3. Crime reconstruction dashboard
     4. Automated event-sequence generator
     5. Interactive visual investigation platform
   - Formally designated every component as **KEEP**, **FOLD**, or **CUT** with an explicit forensic justification.

2. **Folded Subsystems (Logic preserved, standalone pages eliminated)**:
   - **Entities Page (`/entities`)**: Folded directly into an interactive search and mention inspector side-panel within the **Knowledge Graph** (`/graph`) and the **Evidence Vault** (`/evidence`).
   - **Authenticity Page (`/authenticity`)**: Folded into an "Authenticity & Forensics" tab inside the **Evidence Vault** exhibit detail drawer, contextualizing EXIF metadata, Error Level Analysis (ELA), perceptual hash reuse, and bank balance arithmetic directly with the exhibit.
   - **Challenge / Cross-Examination Page (`/verifier`)**: Folded into an instant "Assistant Cross-Examination" action within the **Review Queue** (`/review`) and Claims inspection.
   - **Audit Log Page**: Embedded directly as the "Chain of Custody" ledger in exhibit details and included in export packages.
   - **System Capabilities**: Converted from a large modal into a lightweight status popover in the top `CaseBar`.

3. **Cut Components (Removed from navigation, routing, and dead UI)**:
   - **Metrics Page (`/metrics`)**: Removed from navigation and UI routing. The benchmark logic remains in `scripts/benchmark.py` and produces `data/case_alpha/benchmark_results.json` for documentation without cluttering the investigator's active workflow.
   - **Command Palette (`CommandPalette.tsx`)**: Replaced with a fast, uncluttered quick-search box in `CaseBar.tsx`.
   - **Timeline Lane Modes**: Standardized on a single clean toggle (`Source Lane` vs `Actor Lane`) to prevent visual timeline noise.
   - **Graph Layout Engines**: Standardized on the deterministic `fcose` physics layout to prevent node jitter during investigation.
   - **Uncalibrated Clustering**: Pruned ungrounded burst clustering; retained verified silence-gap and out-of-order sequence anomaly detectors.

## Why
Digital forensics platforms must prioritize clarity, traceability, and workflow efficiency over feature bloat. Splitting entity mentions, authenticity analyses, and cross-examination into disparate pages fragmented the investigator's mental model and duplicated UI state. By folding related tools into the primary investigation canvas (the Knowledge Graph, Timeline, and Evidence Vault) and cutting redundant vanity metrics, PRAMAAN directly aligns with the official national hackathon evaluation criteria: theme relevance, explainability, and presentation.

## How to explain this to judges in three sentences
We eliminated navigational friction by folding secondary inspection views (entity extraction, authenticity checks, and cross-examination) directly into the core knowledge graph and evidence vault. This consolidates the entire investigation into five purposeful, interconnected deliverables: evidence ingest, multi-source correlation, automated event-sequence generation, interactive graph exploration, and admissibility review. As a result, an investigator can trace an anomaly from the timeline to the graph and inspect the raw source bytes without ever leaving their workflow.

## What is still weak
- The standalone `.tsx` files for folded components (`AuthenticityPage.tsx`, `EntitiesPage.tsx`, `MetricsPage.tsx`, `VerifierChallengePage.tsx`) remain in the repository as reference files; while they are decoupled from routing, future maintenance should archive them to prevent drift.
- The `CaseBar` quick-search currently indexes top-level routes; expanding this to index entity names and exhibit IDs directly from the global state will further streamline investigator navigation.

## How I tested it
1. Ran full TypeScript build and Vite packaging:
```
> pramaan-frontend@0.1.0 build
> tsc && vite build

vite v5.4.21 building for production...
✓ 1647 modules transformed.
✓ built in 54.66s
```
2. Ran full Python backend and forensic test suite:
```
============================= test session starts =============================
platform win32 -- Python 3.12.4, pytest-8.3.4, pluggy-1.6.0
rootdir: C:\Users\Vartika Sharma\Desktop\pramaan
plugins: anyio-4.11.0, Faker-40.54.0, langsmith-0.8.18, cov-5.0.0
collected 38 items

tests\test_phase0_scaffold.py ...                                        [  7%]
tests\test_phase1_hardening.py ....................                      [ 60%]
tests\test_phase1_integrity.py ......                                    [ 76%]
tests\test_phase2_parsers.py ....                                        [ 86%]
tests\test_phase3_extraction.py ...                                      [ 94%]
tests\test_phase4_correlation.py .                                       [ 97%]
tests\test_phase5_anomalies.py .                                         [100%]

============================= 38 passed in 36.10s =============================
```
