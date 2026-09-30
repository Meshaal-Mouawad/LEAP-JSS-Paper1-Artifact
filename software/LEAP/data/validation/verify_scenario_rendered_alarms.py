import re
import sys
from pathlib import Path


EXPECTED_RENDERED_ALARMS = {
    "pdpl_pii_violation.html": {
        "rule_id": "KSA-PDPL-REG-01",
        "framework": "SDAIA-PDPL",
        "message": "SDAIA governance alert",
    },
    "nca_restricted_execution.html": {
        "rule_id": "KSA-NCA-ECC-SEC-04",
        "framework": "NCA-ECC",
        "message": "NCA control alert",
    },
    "nca_audit_gap.html": {
        "rule_id": "KSA-NCA-ECC-AUD-02",
        "framework": "NCA-ECC",
        "message": "NCA audit alert",
    },
    "gdpr_data_export_violation.html": {
        "rule_id": "GDPR-DATA-PROC-01",
        "framework": "GDPR",
        "message": "GDPR processing alert",
    },
    "gdpr_alarm_only.html": {
        "rule_id": "GDPR-DATA-PROC-01",
        "framework": "GDPR",
        "message": "GDPR processing alert",
    },
    "soc2_unsigned_lineage.html": {
        "rule_id": "SOC2-LINEAGE-AUDIT-01",
        "framework": "SOC2-TypeII",
        "message": "SOC 2 lineage alert",
    },
    "yield_rate.html": {
        "rule_id": "KSA-PDPL-REG-01",
        "framework": "SDAIA-PDPL",
        "message": "SDAIA governance alert",
    },
}

ALL_COMPLIANCE_RULE_IDS = {
    expected["rule_id"] for expected in EXPECTED_RENDERED_ALARMS.values()
}

CLEAN_CONTROL_PAGES = [
    "pdpl_clean_control.html",
    "nca_restricted_clean_control.html",
    "audit_clean_control.html",
    "gdpr_clean_control.html",
    "soc2_clean_control.html",
]

COMPLIANCE_ONLY_PAGES = [
    "pdpl_pii_violation.html",
    "nca_restricted_execution.html",
    "nca_audit_gap.html",
    "gdpr_data_export_violation.html",
    "gdpr_alarm_only.html",
    "soc2_unsigned_lineage.html",
]

NO_GENERIC_ISO_CONFLICT_PAGES = [
    "pdpl_pii_violation.html",
    "nca_restricted_execution.html",
    "nca_audit_gap.html",
    "gdpr_data_export_violation.html",
    "gdpr_alarm_only.html",
    "soc2_unsigned_lineage.html",
    "pdpl_clean_control.html",
    "nca_restricted_clean_control.html",
    "audit_clean_control.html",
    "gdpr_clean_control.html",
    "soc2_clean_control.html",
]

FORBIDDEN_COMPLIANCE_WORDING = [
    "legally compliant",
    "SOC 2 Type II compliant",
    "SOC 2 Type II Compliance",
    "GDPR compliant",
    "PDPL compliant",
]


def _html_text(path: Path) -> str:
    html = path.read_text(encoding="utf-8")
    return re.sub(r"\s+", " ", html)


def verify_rendered_alarms() -> None:
    build_dir = Path("docs/_build")
    failures = []

    checked_pages = 0

    for filename, expected in EXPECTED_RENDERED_ALARMS.items():
        path = build_dir / filename
        if not path.exists():
            failures.append(f"{filename}: generated page is missing")
            continue

        text = _html_text(path)
        checked_pages += 1
        required_snippets = [
            f"Alert detected: {expected['rule_id']}",
            f"Control evaluated: {expected['rule_id']}",
            f"Rule mapped: {expected['framework']}",
            expected["message"],
            "Evidence incomplete:",
            "Action: Review required",
        ]
        for snippet in required_snippets:
            if snippet not in text:
                failures.append(f"{filename}: missing rendered snippet {snippet!r}")

        for rule_id in ALL_COMPLIANCE_RULE_IDS - {expected["rule_id"]}:
            wrong_rule_snippets = [
                f"Alert detected: {rule_id}",
                f"Control evaluated: {rule_id}",
            ]
            for snippet in wrong_rule_snippets:
                if snippet in text:
                    failures.append(f"{filename}: wrong compliance rule rendered {snippet!r}")

        for forbidden in FORBIDDEN_COMPLIANCE_WORDING:
            if forbidden.lower() in text.lower():
                failures.append(f"{filename}: forbidden compliance wording {forbidden!r}")

    for filename in NO_GENERIC_ISO_CONFLICT_PAGES:
        path = build_dir / filename
        if not path.exists():
            failures.append(f"{filename}: generated page is missing")
            continue
        text = _html_text(path)
        if "ISO Compliance & Governance Conflict" in text:
            failures.append(f"{filename}: unexpected generic ISO governance conflict")

    for filename in CLEAN_CONTROL_PAGES:
        path = build_dir / filename
        if not path.exists():
            failures.append(f"{filename}: generated page is missing")
            continue
        text = _html_text(path)
        if "Alert detected:" in text:
            failures.append(f"{filename}: clean control rendered a compliance alert")
        if "Control evaluated:" in text:
            failures.append(f"{filename}: clean control rendered a compliance control card")
        if "REVIEW QUEUE" in text or "OWNER CONFIRMATION REQUIRED" in text:
            failures.append(f"{filename}: clean control rendered a Review Queue card")

    for filename in COMPLIANCE_ONLY_PAGES:
        path = build_dir / filename
        if not path.exists():
            failures.append(f"{filename}: generated page is missing")
            continue
        text = _html_text(path)
        if "GOVERNANCE REVIEW REQUIRED" in text:
            failures.append(f"{filename}: compliance-only page rendered governance conflict card")
        if "TECHNICAL REVIEW REQUIRED" in text:
            failures.append(f"{filename}: compliance-only page rendered technical review card")

    if failures:
        print("Rendered compliance alarm verification failed:")
        for failure in failures:
            print(f" - {failure}")
        raise AssertionError(f"{len(failures)} rendered alarm checks failed")

    print(
        "Rendered compliance alarm verification passed: "
        f"{checked_pages} alarm pages, {len(CLEAN_CONTROL_PAGES)} clean controls, "
        "and compliance-only separation checks."
    )


if __name__ == "__main__":
    try:
        verify_rendered_alarms()
    except Exception as exc:
        print(exc)
        sys.exit(1)
