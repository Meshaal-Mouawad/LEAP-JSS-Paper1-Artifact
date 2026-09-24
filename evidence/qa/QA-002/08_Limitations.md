# Limitations

- QA-002 verifies the curated committee candidate, not the broader July 24
  development workspace used by QA-001.
- Its 14 application tests plus 38 controlled scenarios must not be combined
  with or substituted for QA-001's separate 117-test result.
- The scenario suite demonstrates expected behavior on controlled fixtures; it
  does not establish precision, recall, F1, calibration, or field prevalence.
- The generation run is a sample-project reproducibility check, not a runtime
  benchmark intended to replace RR-004 or RR-006.
- The committee baseline initially reported its parallel detail-worker count
  during deterministic execution. The JSS copy corrects that presentation
  wording and retains the underlying deterministic concurrency behavior.
