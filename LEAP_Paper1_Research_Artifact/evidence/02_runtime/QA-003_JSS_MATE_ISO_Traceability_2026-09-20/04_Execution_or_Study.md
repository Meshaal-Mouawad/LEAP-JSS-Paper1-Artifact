# Execution

Commands were executed from `software/LEAP/`:

```bash
python -m pytest -q
python data/validation/test_scenario_fixtures.py
python run_generation.py sample_project
python data/validation/verify_generated_bluebook.py
```

Six Flask routes were checked with the application test client:

- `/`
- `/bluebook/index.html`
- `/bluebook/discovery_report.html`
- `/bluebook/search.html`
- `/bluebook/_static/custom.css`
- `/bluebook/_static/leap-axis-logo.svg`
