# LEAP Paper 1 research artifact

This artifact accompanies *LEAP: A Literate-Programming Architecture for Reconstructing Traceable KPI Knowledge from Enterprise Codebases* by Meshaal Obaid Mouawad and Bryan A. Jones. It preserves a source-linked KPI knowledge implementation, the manuscript and method supplement, bounded verification records, and generated Bluebook examples.

## Read the paper

- [Final manuscript](manuscript/LEAP_JSS_Paper1_Final.pdf) and [editable source](manuscript/LEAP_JSS_Paper1_Final.tex)
- [Method Supplement S1](supplement/LEAP_JSS_Method_Supplement.pdf) and [editable source](supplement/LEAP_JSS_Method_Supplement.tex)
- [Six manuscript figures](manuscript/figs/)

The PDF files match the author-approved submission files in the local master. The public manuscript source differs from the master source only in its non-scientific opening comment, which removes an internal version label; the document body is unchanged.

Administrative privacy redaction of a local workstation path embedded in a dashboard screenshot. No scientific values, interface evidence, or manuscript claims were changed. The pre-redaction PDF and figure are retained only in the private author archive.

## Artifact map

| Research question | Inspect |
|---|---|
| RQ1: source-linked KPI knowledge construction | [Software](software/LEAP/), [generated dossier](software/LEAP/docs/_build/ethylene_production_yield.html), [S1 method specification](supplement/LEAP_JSS_Method_Supplement.pdf) |
| RQ2: bounded source-to-record, annotation, publication, and review behavior | [Application tests](software/LEAP/test_app.py), [38 prepared-record fixtures and harness](software/LEAP/data/validation/), [QA-002 and QA-003](evidence/qa/), [MATE and ISO traceability](evidence/traceability/) |
| RQ3: archived execution characteristics | [RR-004, RR-005, and RR-006 summaries](evidence/runtime/) |

The 38 curated scenarios construct prepared KPI records and check downstream status, review routing, signal text, and rule/alarm metadata. They do **not** test repository discovery, extraction precision/recall, or formula equality. Repository-discovery checks, prepared-record scenarios, and MATE tests are distinct evidence layers. The [historical fixture audit](evidence/traceability/HISTORICAL_FIXTURE_VALIDATION_AUDIT.md) documents the historical acceptance result and its limits.

QA-004 is supplied only as an [author-reported summary](evidence/qa/QA-004_SUMMARY_ONLY.md). Its original raw execution directory is not present here. Some historical raw runtime logs contain private workstation paths and remain in the author's local master archive; the public artifact includes their processed summaries, not redacted files mislabeled as originals.

## Run the software and checks

Use Python 3.10 or newer. From `software/LEAP/`:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
python data/validation/test_scenario_fixtures.py
LEAP_ENABLE_AI=0 python run_generation.py sample_project
python data/validation/verify_generated_bluebook.py
```

The generated static Bluebook is in `software/LEAP/docs/_build/`. See [reproducibility notes](reproducibility/README.md) for snapshot identity and verification boundaries.

## Identity and citation

The frozen software was derived from commit `f3b7b1d7af61fb5a606ae769df1102775faf269b` with the bounded, documented JSS changes described in [snapshot notes](reproducibility/SOFTWARE_SNAPSHOT.md). This research artifact is a curated redistribution: release-only changes correct MIT packaging metadata, omit private/internal files, and replace uncertain vendor/platform graphical marks with text labels. The algorithms, tests, fixtures, and scientific evidence are unchanged; the publication software tree is not byte-identical to the private historical snapshot. `SHA256SUMS.txt` binds the included files. See [CITATION.cff](CITATION.cff), [third-party notices](THIRD_PARTY_NOTICES.md), and the [clean artifact repository](https://github.com/Meshaal-Mouawad/LEAP-JSS-Paper1-Artifact). That repository remains private pending author approval of the public switch; no archive DOI or journal publication identifier has been assigned. The previous Git history is retained separately in a private provenance archive and is not part of this publication history.
