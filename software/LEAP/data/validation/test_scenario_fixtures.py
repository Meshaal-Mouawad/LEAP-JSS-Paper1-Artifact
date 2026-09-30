import os
import re
import sys
from pathlib import Path
from typing import Dict, Any, List

# Add workspace root to sys.path so we can import packages correctly
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

try:
    from bluebook_generator.ai_generator import generate_kpi_details
    from bluebook_generator.governance import attach_governance
    from bluebook_generator.kpi_extractor import _SUPPORTED_EXTS
except ImportError as e:
    print(f"Error importing LEAP modules: {e}")
    sys.exit(1)

EXPECTED_COMPLIANCE_METADATA = {
    "KSA-PDPL-REG-01": {
        "framework": "SDAIA-PDPL",
        "category": "PRIVACY_GOVERNANCE_ALERT",
        "severity": "CRITICAL_PRIVACY_ALERT",
        "message": "SDAIA governance alert",
    },
    "KSA-NCA-ECC-SEC-04": {
        "framework": "NCA-ECC",
        "category": "SECURITY_VULNERABILITY",
        "severity": "SECURITY_VULNERABILITY",
        "message": "NCA control alert",
    },
    "KSA-NCA-ECC-AUD-02": {
        "framework": "NCA-ECC",
        "category": "COMPLIANCE_AUDIT_GAP",
        "severity": "COMPLIANCE_AUDIT_GAP",
        "message": "NCA audit alert",
    },
    "GDPR-DATA-PROC-01": {
        "framework": "GDPR",
        "category": "REGULATORY_RISK",
        "severity": "REGULATORY_RISK",
        "message": "GDPR processing alert",
    },
    "SOC2-LINEAGE-AUDIT-01": {
        "framework": "SOC2-TypeII",
        "category": "AUDIT_INCOMPLETE",
        "severity": "AUDIT_INCOMPLETE",
        "message": "SOC 2 lineage alert",
    },
}

LEGACY_COMPLIANCE_SIGNAL_LABELS = {
    "compliance",
    "compliance conflict",
    "compliance risk",
}


def parse_expected_header(file_path: Path) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    expected = {
        "status": "Validated",
        "review_queue": "No",
        "signals": [],
        "rules": [],
        "formula": ""
    }

    # Find Expected LEAP Result block
    header_match = re.search(r"(?is)Expected LEAP Result:\s*\n(.*?)(?:\n\n|\n[^\s#\-\*\/']|$)", content)
    if header_match:
        block = header_match.group(1)
        for line in block.splitlines():
            line = re.sub(r"^[\s#\-\*\/']+", "", line).strip()
            if not line or ":" not in line:
                continue
            key, val = line.split(":", 1)
            key = key.strip().lower()
            val = val.strip()
            if "status" in key:
                expected["status"] = val
            elif "review queue" in key:
                expected["review_queue"] = val
            elif "signal" in key:
                expected["signals"] = [s.strip() for s in val.split(",") if s.strip() and s.strip().lower() != "none"]
            elif "rule" in key:
                expected["rules"] = [r.strip() for r in val.split(",") if r.strip() and r.strip().lower() != "none"]
            elif "formula" in key:
                expected["formula"] = val

    return expected


def evaluate_fixture(file_path: Path) -> Dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    ext = file_path.suffix.lower()

    # Parse KPI display name
    kpi_name_match = re.search(r"(?i)(?:KPI|kpi)\s*:\s*(.+)$", content, re.M)
    kpi_name = kpi_name_match.group(1).strip() if kpi_name_match else file_path.stem

    language = _SUPPORTED_EXTS.get(ext, "unknown")

    kpi_data = {
        "name": kpi_name,
        "file_path": str(file_path),
        "code_context": content,
        "language": language,
        "confidence": 90.0,
    }

    # Get details
    details = generate_kpi_details(kpi_name, content)
    kpi_data["details"] = details

    # Attach governance
    root_dir = Path(".")
    docs_dir = Path("docs")
    attach_governance([kpi_data], root_dir, docs_dir)

    governance = kpi_data.get("governance", {})
    conflicts = governance.get("conflicts", [])
    audit_notes = governance.get("audit_notes", [])
    compliance_alarms = kpi_data.get("compliance_alarms", [])
    accountable = governance.get("accountable") or ""

    if conflicts or audit_notes or compliance_alarms:
        status = "Needs Review"
    elif accountable:
        status = "Validated"
    else:
        status = "Needs Review"

    review_queue = "Yes" if (conflicts or audit_notes or compliance_alarms) else "No"

    return {
        "kpi_data": kpi_data,
        "status": status,
        "review_queue": review_queue,
        "conflicts": conflicts,
        "audit_notes": audit_notes,
        "compliance_alarms": compliance_alarms,
    }


def test_all_scenario_fixtures():
    fixtures_dir = Path(__file__).parent / "generated_scenario_kpis"
    if not fixtures_dir.exists():
        raise FileNotFoundError(f"Fixtures directory not found: {fixtures_dir}")

    fixture_files = sorted([f for f in fixtures_dir.iterdir() if f.is_file() and f.suffix in _SUPPORTED_EXTS])

    failures = []
    results = []

    print("\n========================================================")
    print("      LEAP SCENARIO FIXTURES ACCEPTANCE TEST            ")
    print("========================================================\n")

    for file_path in fixture_files:
        expected = parse_expected_header(file_path)
        actual = evaluate_fixture(file_path)

        file_failures = []

        # 1. Verify Status
        if actual["status"] != expected["status"]:
            file_failures.append(f"Status mismatch: expected '{expected['status']}', got '{actual['status']}'")

        # 2. Verify Review Queue
        if actual["review_queue"] != expected["review_queue"]:
            file_failures.append(f"Review Queue mismatch: expected '{expected['review_queue']}', got '{actual['review_queue']}'")

        # 3. Verify Compliance Rules by canonical rule identity, not old prose labels.
        actual_alarms_by_rule = {
            alarm.get("rule_id"): alarm for alarm in actual["compliance_alarms"]
        }
        actual_rule_ids = list(actual_alarms_by_rule)
        for rule_id in expected["rules"]:
            alarm = actual_alarms_by_rule.get(rule_id)
            if alarm is None:
                file_failures.append(f"Missing expected compliance alarm: '{rule_id}'")
                continue

            expected_metadata = EXPECTED_COMPLIANCE_METADATA.get(rule_id, {})
            for field, expected_value in expected_metadata.items():
                actual_value = alarm.get(field, "")
                if field == "message":
                    if expected_value.lower() not in str(actual_value).lower():
                        file_failures.append(
                            f"Compliance alarm '{rule_id}' message mismatch: expected to contain "
                            f"'{expected_value}', got '{actual_value}'"
                        )
                elif actual_value != expected_value:
                    file_failures.append(
                        f"Compliance alarm '{rule_id}' {field} mismatch: expected "
                        f"'{expected_value}', got '{actual_value}'"
                    )

            if alarm.get("status") != "REVIEW_REQUIRED":
                file_failures.append(
                    f"Compliance alarm '{rule_id}' status mismatch: expected "
                    f"'REVIEW_REQUIRED', got '{alarm.get('status')}'"
                )
            if not alarm.get("recommended_action"):
                file_failures.append(f"Compliance alarm '{rule_id}' missing recommended_action")
            if not alarm.get("evidence"):
                file_failures.append(f"Compliance alarm '{rule_id}' missing evidence")
        
        # Verify negative control (clean) compliance fixtures have no alarms
        if not expected["rules"] and actual["compliance_alarms"]:
            file_failures.append(f"Unexpected compliance alarm(s) triggered: {[a['rule_id'] for a in actual['compliance_alarms']]}")

        # 4. Verify Expected Signals
        all_actual_reasons = (
            [c["reason"] for c in actual["conflicts"]]
            + [n["reason"] if isinstance(n, dict) else str(n) for n in actual["audit_notes"]]
            + [a["message"] for a in actual["compliance_alarms"]]
        )
        for signal in expected["signals"]:
            # The generated scenario fixtures used old generic labels such as
            # "Compliance Conflict". Compliance validation is now rule-based
            # above so NCA/GDPR/PDPL/SOC2 cannot be mistaken for a generic ISO
            # message.
            if expected["rules"] and signal.lower() in LEGACY_COMPLIANCE_SIGNAL_LABELS:
                continue
            found = any(signal.lower() in reason.lower() for reason in all_actual_reasons)
            if not found:
                file_failures.append(f"Missing expected signal: '{signal}'")

        status_str = "PASS" if not file_failures else "FAIL"
        results.append({
            "filename": file_path.name,
            "status": status_str,
            "expected_status": expected["status"],
            "actual_status": actual["status"],
            "failures": file_failures
        })

        if file_failures:
            failures.append((file_path.name, file_failures))

    # Print summary table
    print(f"{'Filename':<40} | {'Status':<6} | {'Expected':<12} | {'Actual':<12}")
    print("-" * 80)
    for r in results:
        print(f"{r['filename']:<40} | {r['status']:<6} | {r['expected_status']:<12} | {r['actual_status']:<12}")

    if failures:
        print("\n========================================================")
        print("                  FAILURE DETAILS                       ")
        print("========================================================\n")
        for fn, f_list in failures:
            print(f"❌ {fn}:")
            for f in f_list:
                print(f"   - {f}")
            print()
        
        # Raise assertion error when run under pytest
        assert not failures, f"Fixture verification failed for {len(failures)} fixtures."
    else:
        print("\n✅ All scenario fixtures verified successfully!")


if __name__ == "__main__":
    try:
        test_all_scenario_fixtures()
        sys.exit(0)
    except AssertionError:
        sys.exit(1)
    except Exception as e:
        print(f"Error executing test harness: {e}")
        sys.exit(1)
