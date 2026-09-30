# LEAP Paper 1 — technical research artifact

Start with `EVIDENCE_INDEX.md`. The separate 20-page manuscript PDF and five-page Supplement S1 are the reading files for this submission.

This archive contains the complete unchanged frozen software directory, the selected technical evidence cited by Paper 1, and editable manuscript/S1 materials. `SELECTION.json` maps every copied file to the verified working package and its checksum. No runtime source, fixture, original log, or numerical result has been rewritten.

## Checks and use

Run `python3 verify_artifact.py` from this directory to verify every packaged file. This check reads hashes; it does not run LEAP or change files.

Software is under `software/LEAP/`. Its frozen dependency list is `requirements.txt`. In an environment with those dependencies, the original commands are:

```sh
cd software/LEAP
LEAP_ENABLE_AI=0 python3 -m pytest -q
LEAP_ENABLE_AI=0 python3 data/validation/test_scenario_fixtures.py
python3 data/validation/verify_generated_bluebook.py
```

The archived test accounting is 19 pytest checks: 18 application-test functions plus one suite-level check over 38 prepared-record fixtures. The standalone harness uses the same 38-fixture family. S1 and the current manuscript define what the tests assert. Historical summaries and source documents retain their original wording and version; their older headlines are not additional current results.

Optional AI-assisted authoring was disabled for the reported verification. No new LEAP execution was performed to curate this archive. This packaging operation does not create a new benchmark or add an independent sample.

## Editorial sources

The unchanged main LaTeX source is `submission/LEAP_JSS_Paper1.tex`; run `sh build.sh` inside `submission/` to compile it. The manuscript PDF is uploaded separately, not duplicated here. The original class/style files and figure PDFs are included. S1 and its exact source locator files remain under `submission/supplement/`.

The source root named JSS_Submtion in S1 corresponds to the root of this archive. The current source filename is listed above and in `CURRENT_AUTHORITY.md`. The Sprint 7 records retain their original identity and are placed at the `reproducibility/sprint7/` paths cited in S1.

This is a technical reviewer package. It does not assign a public repository URL, DOI, new software license, or author-approval status. Original software metadata and its existing licenses remain unchanged.

## Current publication revision

The current manuscript and Supplement S1 list Meshaal Obaid Mouawad as sole author. The manuscript build uses the standard LaTeX `subcaption` package for Figure 6. Current source/PDF identities are recorded in `CURRENT_AUTHORITY.md`. Original software and evidence remain unchanged.
