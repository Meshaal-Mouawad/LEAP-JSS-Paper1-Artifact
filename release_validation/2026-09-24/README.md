# Final packaging regression checks

Run date: 24 September 2026 (completed by 13:15:52 UTC). Environment: macOS Darwin arm64, Python 3.12.7. Tested an isolated temporary copy of this publication package's `software/LEAP/`; the frozen package was not used as the generation output directory. Source research baseline: `f3b7b1d7af61fb5a606ae769df1102775faf269b`, with the bounded JSS changes and release-only `pyproject.toml` metadata correction documented elsewhere.

| Command from isolated `software/LEAP/` | Exit | Result |
|---|---:|---|
| `python -m pytest -q` | 0 | 19 passed |
| `python data/validation/test_scenario_fixtures.py` | 0 | 38/38 prepared-record scenarios passed |
| `LEAP_ENABLE_AI=0 python run_generation.py sample_project` | 0 | 28 dossiers; 32 pages resolved; AI-disabled output did not report workers |
| `python data/validation/verify_generated_bluebook.py` | 0 | 32 pages checked; 0 errors; 0 warnings |
| Flask test client on `/`, index, discovery, search, stylesheet, and logo | 0 | 6/6 HTTP 200 |
| `latexmk -pdf -interaction=nonstopmode -halt-on-error LEAP_JSS_Paper1_Final.tex` in an isolated manuscript copy | 0 | 19 pages; extracted PDF text matched the packaged PDF |

The raw console logs, including temporary local paths, remain in the author's private release-validation directory. Their SHA-256 digests are: pytest `8b0f179e7ad65e0494f0c5f9cfcc9ef626ae2b388010639d032aa42c279f7210`; scenarios `dd3324a9a3d2b99ca8ede9fb6264922afc25543ce702886e0685cf1b78557b46`; generation `de694a14d58a438776ed408d2b4e0ec2529f48b08a39dc2dfe3a5f146e4d3ca9`; Bluebook validation `83cc7456ad341b7a933f7101259bff34a0c25128becf6f338f4f4f2222ce55a8`; routes `349f60cd01843f8994546c61edd8c678cc7838f38174a85583f5681bb8876a4b`.

These are current packaging checks. They do not replace historical July evidence or the unavailable original QA-004 execution receipt. Identical scenario stdout across separate runs is not evidence of identical execution time or environment.
