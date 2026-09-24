"""Canonical repository-relative paths for LEAP package assets."""

from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPOSITORY_ROOT / "data"
DEMO_PROJECT_DIR = DATA_DIR / "demo" / "sample_project"
KNOWLEDGE_BASE_DIR = DATA_DIR / "runtime" / "knowledge_base"
GOVERNANCE_DATA_DIR = DATA_DIR / "runtime" / "governance"
OVERRIDES_DIR = DATA_DIR / "runtime" / "overrides"
GOVERNANCE_RULES_PATH = GOVERNANCE_DATA_DIR / "governance_rules.json"
BUSINESS_OVERRIDES_PATH = OVERRIDES_DIR / "business_overrides.json"
GOVERNANCE_OVERRIDES_PATH = OVERRIDES_DIR / "governance_overrides.json"
VALIDATION_DIR = DATA_DIR / "validation"
SCENARIO_FIXTURES_DIR = VALIDATION_DIR / "generated_scenario_kpis"
GOVERNANCE_CONFIG_PATH = VALIDATION_DIR / "kpi_governance.json"


def resolve_workspace_path(value: str | Path) -> Path:
    """Resolve a user path while preserving the public sample-project alias."""
    raw = Path(value)
    if str(value) == "sample_project":
        return DEMO_PROJECT_DIR
    return raw if raw.is_absolute() else (REPOSITORY_ROOT / raw).resolve()
