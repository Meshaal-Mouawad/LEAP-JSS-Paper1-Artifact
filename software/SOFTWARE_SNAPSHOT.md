# LEAP JSS Software Snapshot

## Baseline

- Source: committee candidate repository
- Source commit: `f3b7b1d7af61fb5a606ae769df1102775faf269b`
- Source branch: `main`
- Source remote: `https://github.com/Meshaal-Mouawad/AI-Powered_KPI_Extractor_Committee_Candidate_2026_07_17.git`
- Frozen location: `software/LEAP/`
- Snapshot date: 2026-09-20
- Generated-output refresh: 2026-09-21

The source candidate was clean before copying. Git metadata and transient cache
files were excluded from the journal artifact.

## JSS-Only Delta

The frozen JSS copy contains bounded journal-evidence corrections and focused
regression tests:

1. `bluebook_generator/main.py` no longer reports a worker count when optional
   AI enrichment is disabled. AI-enabled output still reports the configured
   number of AI enrichment workers.
2. `test_app.py` verifies both output branches.
3. Existing narrow ISO 22400 conflict detectors now emit their configured rule
   and framework identifiers (`ISO-22400-RE-1`, `ISO-22400-UE-2`) in conflict
   objects; positive and clean controls verify both templates.
4. Focused MATE tests verify explicit LaTeX normalization, canonical formula
   annotations, and generated dossier business/developer lineage mappings.

No extraction promotion, formula calculation, compliance-alarm, or concurrency
behavior was changed. ISO metadata is additive to existing conflict outputs.

The generated navigation, discovery, and search-index files were rebuilt from
this frozen source during the Sprint 5 verification run. The software file
manifest and checksums bind those regenerated outputs; no runtime source or
test file changed during that refresh.

## Verification

- `python -m pytest -q`: 19 passed
- `python data/validation/test_scenario_fixtures.py`: 38 passed
- `LEAP_ENABLE_AI=0 python run_generation.py sample_project`: passed; 28 KPI
  dossiers and 32 pages generated; deterministic worker count absent
- Flask route checks: 6 of 6 returned HTTP 200
- `python data/validation/verify_generated_bluebook.py`: 32 pages checked with
  0 errors and 0 warnings

The authoritative evidence record is
`../evidence/02_runtime/QA-002_Committee_Candidate_Baseline_2026-09-20/` and
`../evidence/02_runtime/QA-003_JSS_MATE_ISO_Traceability_2026-09-20/`.
