# LEAP Workspace Package Inventory

This document lists the files and directories present in the LEAP candidate workspace.

## 1. Directory Tree
- `bluebook_generator/` - Core package directory.
  - `__init__.py`
  - `ai_generator.py` - AI enrichment module (OpenAI API connection).
  - `cli.py` - Command-line interface logic.
  - `governance.py` - Governance rule resolver.
  - `kpi_extractor.py` - Deterministic scanner and regex parser.
  - `main.py` - Master orchestrator.
  - `parser.py` - Code comment extraction utility.
- `data/` - Bundled LEAP data assets.
  - `runtime/knowledge_base/` - Reference templates and rule mappings.
  - `runtime/governance/` - Governance rule configuration.
  - `runtime/overrides/` - Business and governance override ledgers.
  - `demo/sample_project/` - Demonstration source workspace used by the public generation command.
  - `validation/` - Bounded validation fixtures, expected outcomes, and verification scripts.
- `docs/` - Source documentation files (ReStructuredText configurations).
  - `_build/` - Pre-compiled Interactive Bluebook static website pages.
- `templates/` - Jinja templates for HTML report rendering.
- `app.py` - Main Flask review web interface.
- `run_generation.py` - Script entry point to run deterministic parser on sample project.
- `setup.cfg` - Distribution packaging settings.
- `pyproject.toml` - Dependency declarations and environment configurations.
- `test_app.py` - Unit tests for core functions and routing.
- `README.md` - Core project description, setup guide, and execution commands (at repository root).
- `LICENSE` - MIT License text (at repository root).
- `Committee_Read/` - Directory containing dissertation committee reading materials.
  - `COMMITTEE_REVIEW_GUIDE.md` - Dissertation committee navigation portal and evaluation guide.
  - `PACKAGE_CONTENTS.md` - This workspace inventory manifest.
