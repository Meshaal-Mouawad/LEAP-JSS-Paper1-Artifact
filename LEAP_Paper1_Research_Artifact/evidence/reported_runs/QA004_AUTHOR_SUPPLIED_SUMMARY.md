# QA-004 — author-supplied execution summary

Record type: transcribed execution report supplied by the author in this conversation.
Packaging date: 22 September 2026.
This file is NOT the original QA-004 README, console transcript, environment manifest, or execution receipt.
No test was run to create this record. The original reported values below are retained; their raw bundle has not been transferred into this distribution.

## Reported execution

- Original local directory: `/Users/meshaalmouawad/Downloads/JSS_Submtion/evidence/02_runtime/QA-004_Current_Fixture_Reproducibility_2026-09-21/`
- Command: `python data/validation/test_scenario_fixtures.py`
- Timestamp: `2026-09-21T21:39:43+03:00`
- Result: `38/38 PASS`
- Exit status: `0`
- Harness SHA-256: `64a44430e41e8664912a38ab6fc9555b430a6716f6ccb21ef234a2765e9f69c5`
- Reported fixture-inventory digest: `2e6d2facb6f72a3e4d7bd2956c2bacf66c6a8fec9b6bf4ba0cb39dace8f11b72`
- Reported stdout SHA-256: `dd3324a9a3d2b99ca8ede9fb6264922afc25543ce702886e0685cf1b78557b46`
- Reported stderr SHA-256: `e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`
- The author reported verification of 13 evidence hashes, 309 frozen-software hashes, and 833 workspace hashes. These counts describe the reported local bundle; they were not reverified as a QA-004 bundle here.

The author reported that no LEAP runtime source, fixture, harness, or test was changed and that the original committee repository remained clean. This distribution does not re-access that Mac repository.

## Interpretation

The report corroborates the described rerun but does not supply independently inspectable raw execution provenance. An existing Sprint 7 transcript has the same stdout digest; it remains under its original Sprint 7 identity and is not relabeled QA-004. Identical console text does not establish a shared execution date or environment.

The historical July processed inventory and packaged QA-003 records remain separate evidence. The 38 fixtures are prepared-record acceptance scenarios, not repository-discovery or formula-fidelity measurements. A repeated run is not a second independent validation sample.

## Transfer needed

Copy the existing original QA-004 directory from the author's local workspace without editing its contents. Verify its own manifest and inspect the actual environment/run receipt before describing it as included and independently inspectable. Do not construct missing raw files from this summary and do not rerun merely to recreate a historical record.
