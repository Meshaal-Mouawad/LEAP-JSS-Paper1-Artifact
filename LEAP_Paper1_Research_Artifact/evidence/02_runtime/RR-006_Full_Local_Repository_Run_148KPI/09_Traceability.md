# Traceability

Raw terminal log:

- `05_Raw_Evidence/full_local_repository_run_148kpi_2026-07-15.log`

Processed summaries:

- `06_Processed_Evidence/execution_summary.csv`
- `06_Processed_Evidence/prepared_dossiers.csv`

Relevant QA follow-up:

- `phase3/verify_generated_bluebook.py` checks current generated HTML for missing static assets, broken local links, formula rendering defects, compliance alarm mapping, review queue duplication, and status/alarm consistency.

Generated-output QA result:

- `phase3/generated_bluebook_validation_report.md` records 0 critical errors and 20 broad-scan warnings for the current generated HTML set.
