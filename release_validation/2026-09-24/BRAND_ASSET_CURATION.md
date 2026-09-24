# Public-artifact brand-asset curation check

Date: 24 September 2026. This is a release-validation check, not a new scientific experiment.

The publication copy removes both source and built copies of 30 integration-icon SVGs whose exact upstream provenance was not retained. The dashboard template now renders the same 30 product/format labels as plain text; the stylesheet gives those labels intrinsic width. No integration-detection, KPI-data, algorithm, test, fixture, or scientific-evidence logic changed. Frozen generated dossier/index content was restored after a temporary regeneration changed date labels; the publication HTML adds only a LEAP-owned favicon reference to avoid a missing browser asset. The private master retains its original graphical assets.

| Check (from `software/LEAP/`) | Result |
|---|---|
| `python -m pytest -q` | 19 passed; exit 0 |
| `python data/validation/test_scenario_fixtures.py` | 38/38 passed; exit 0 |
| `LEAP_ENABLE_AI=0 python run_generation.py sample_project` | 28 dossiers, 32 generated pages; exit 0 |
| `python data/validation/verify_generated_bluebook.py` | 32 pages, 0 errors, 0 warnings; exit 0 |
| Flask test-client HTML asset checks | 35 pages queried, seven unique local assets, 0 missing; exit 0 |
| Headless Chrome dashboard check | 30 text labels, 0 `<img>` elements in the integration list, 0 HTTP errors; exit 0 |

The `plus.png`, `minus.png`, and `file.png` copies match Sphinx 8.2.3 Basic theme assets byte-for-byte; their exact hashes and source location are recorded in `THIRD_PARTY_NOTICES.md`. Sphinx and Pygments license notices are retained in `third_party_licenses/`.

The six scientific manuscript figures were not edited. A visual check of those figures found no vendor integration logos, but the frozen dashboard screenshot contains a visible local workstation path. It is a separate author-decision item before public visibility; it must not be silently modified or omitted.
