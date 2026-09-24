from pathlib import Path

import pytest

from app import app


@pytest.fixture()
def client():
    app.config.update(TESTING=True)
    return app.test_client()


def test_control_plane_routes_are_available(client):
    for path in ("/", "/status", "/api/stats"):
        response = client.get(path)
        assert response.status_code == 200, path


def test_worker_count_is_reported_only_for_ai_enrichment():
    from bluebook_generator.main import _worker_context

    assert _worker_context(False, 4) == ""
    assert _worker_context(True, 4) == " with 4 AI enrichment workers"


def test_workspace_stats_payload_shape(client):
    response = client.get("/api/stats")
    payload = response.get_json()

    assert isinstance(payload["total_kpis"], int)
    assert isinstance(payload["validated_kpis"], int)
    assert isinstance(payload["review_items"], int)
    assert "avg_confidence" in payload
    assert payload["workspace_state"] in {"Idle", "Ready", "Built"}


def test_committed_bluebook_pages_are_served(client):
    pages = (
        "/bluebook/index.html",
        "/bluebook/discovery_report.html",
        "/bluebook/raci_directory.html",
        "/bluebook/search.html",
        "/bluebook/genindex.html",
    )

    for path in pages:
        response = client.get(path)
        assert response.status_code == 200, path
        assert b"LEAP" in response.data or b"KPI" in response.data


def test_bluebook_static_assets_are_served(client):
    assets = (
        "/bluebook/_static/custom.css",
        "/bluebook/_static/leap/ECDS_TOKENS.css",
        "/bluebook/_static/leap-axis-logo.svg",
    )

    for path in assets:
        response = client.get(path)
        assert response.status_code == 200, path
        assert response.data


def test_enterprise_workspace_assets_are_present():
    required = (
        "docs/_build/_static/custom.css",
        "docs/_build/_static/leap/ECDS_TOKENS.css",
        "docs/_build/index.html",
        "docs/_build/discovery_report.html",
        "docs/_build/raci_directory.html",
    )

    for filename in required:
        path = Path(filename)
        assert path.exists(), filename
        assert path.stat().st_size > 0, filename


def test_compliance_alarms_pdpl_pii():
    from governance_patch import run_compliance_alarms
    # Positive case: PII triggers
    kpi_trigger = {
        "file_path": "data/demo/sample_project/dummy_compliance_pdpl_pii.py",
        "code_context": "# KPI: Customer Activity Index\ndef calculate(national_id, phone_num): pass"
    }
    alarms_trigger = run_compliance_alarms(kpi_trigger)
    assert len(alarms_trigger) == 1
    assert alarms_trigger[0]["rule_id"] == "KSA-PDPL-REG-01"
    assert "national_id" in alarms_trigger[0]["evidence"]

    # Clean control case: Masking present, does not trigger
    kpi_clean = {
        "file_path": "data/demo/sample_project/dummy_compliance_pdpl_pii_clean.py",
        "code_context": "# KPI: Masked Customer Activity Index\ndef calculate_activity_clean(national_id):\n    masked_id = mask_value(national_id)\n    return 1.0"
    }
    alarms_clean = run_compliance_alarms(kpi_clean)
    assert len(alarms_clean) == 0


def test_compliance_alarms_nca_sec():
    from governance_patch import run_compliance_alarms
    # Positive case: os.system/eval triggers
    kpi_trigger = {
        "file_path": "data/demo/sample_project/dummy_compliance_nca_sec.py",
        "code_context": "eval('2+2')\nos.system('echo')"
    }
    alarms_trigger = run_compliance_alarms(kpi_trigger)
    assert len(alarms_trigger) == 1
    assert alarms_trigger[0]["rule_id"] == "KSA-NCA-ECC-SEC-04"
    assert "eval" in alarms_trigger[0]["evidence"]
    assert "os.system" in alarms_trigger[0]["evidence"]

    # Clean control case
    kpi_clean = {
        "file_path": "data/demo/sample_project/dummy_compliance_nca_sec_clean.py",
        "code_context": "len('safe')"
    }
    alarms_clean = run_compliance_alarms(kpi_clean)
    assert len(alarms_clean) == 0


def test_compliance_alarms_nca_aud():
    from governance_patch import run_compliance_alarms
    # Positive case: update/write without audit logs
    kpi_trigger = {
        "file_path": "data/demo/sample_project/dummy_compliance_nca_aud.py",
        "code_context": "UPDATE inventory SET qty = 10"
    }
    alarms_trigger = run_compliance_alarms(kpi_trigger)
    assert len(alarms_trigger) == 1
    assert alarms_trigger[0]["rule_id"] == "KSA-NCA-ECC-AUD-02"

    # Clean control case: modification with all audit keywords
    kpi_clean = {
        "file_path": "data/demo/sample_project/dummy_compliance_nca_aud_clean.py",
        "code_context": "UPDATE inventory -- actor: admin timestamp: 2026 before: 1 after: 2 diff: 1"
    }
    alarms_clean = run_compliance_alarms(kpi_clean)
    assert len(alarms_clean) == 0


def test_compliance_alarms_gdpr_proc():
    from governance_patch import run_compliance_alarms
    # Positive case: cross_border / gdpr without consent or processing agreement
    kpi_trigger = {
        "file_path": "data/demo/sample_project/dummy_compliance_gdpr_proc.py",
        "code_context": "cross_border export of personal_data"
    }
    alarms_trigger = run_compliance_alarms(kpi_trigger)
    assert len(alarms_trigger) == 1
    assert alarms_trigger[0]["rule_id"] == "GDPR-DATA-PROC-01"

    # Clean control case: with agreement/consent
    kpi_clean = {
        "file_path": "data/demo/sample_project/dummy_compliance_gdpr_proc_clean.py",
        "code_context": "cross_border dataset transfer under processing_agreement with consent"
    }
    alarms_clean = run_compliance_alarms(kpi_clean)
    assert len(alarms_clean) == 0


def test_compliance_alarms_soc2_lineage():
    from governance_patch import run_compliance_alarms
    # Positive case: lineage/trace without signature
    kpi_trigger = {
        "file_path": "data/demo/sample_project/dummy_compliance_soc2_lineage.py",
        "code_context": "lineage trace tracking"
    }
    alarms_trigger = run_compliance_alarms(kpi_trigger)
    assert len(alarms_trigger) == 1
    assert alarms_trigger[0]["rule_id"] == "SOC2-LINEAGE-AUDIT-01"

    # Clean control case: signature present
    kpi_clean = {
        "file_path": "data/demo/sample_project/dummy_compliance_soc2_lineage_clean.py",
        "code_context": "lineage trace tracking signed signature"
    }
    alarms_clean = run_compliance_alarms(kpi_clean)
    assert len(alarms_clean) == 0


def test_review_queue_signal_separation():
    from governance_patch import evaluate_all_conflicts

    # 1. Validated KPI with no conflicts, no compliance alarms, no technical notes
    kpi_clean = {
        "file_path": "data/demo/sample_project/dummy_clean_kpi.py",
        "code_context": "# KPI: Clean Yield\n# Formula: 1.0\ndef calculate(): return 1.0"
    }
    details_clean = {
        "formula_description": "1.0",
        "business_formula": "1.0"
    }
    res_clean = evaluate_all_conflicts(kpi_clean, details_clean, "Operations Owner")
    assert len(res_clean["conflicts"]) == 0
    assert len(res_clean["audit_notes"]) == 0
    assert len(res_clean["compliance_alarms"]) == 0

    # 2. Missing formula comment alone does not create severe high-severity conflict, but a medium audit note
    kpi_no_comment = {
        "file_path": "data/demo/sample_project/dummy_no_comment.py",
        "code_context": "def calculate(): return 1.0"
    }
    details_no_comment = {}
    res_no_comment = evaluate_all_conflicts(kpi_no_comment, details_no_comment, "Operations Owner")
    assert len(res_no_comment["conflicts"]) == 0
    assert len(res_no_comment["audit_notes"]) >= 1
    assert any("Evidence incomplete: business formula comment not declared" in n["reason"] for n in res_no_comment["audit_notes"])

    # 3. TODO/FIXME/BUG creates technical note (Medium severity)
    kpi_todo = {
        "file_path": "data/demo/sample_project/dummy_todo.py",
        "code_context": "# TODO: fix logic later\ndef calculate(): return 1.0"
    }
    details_todo = {
        "formula_description": "1.0",
        "business_formula": "1.0"
    }
    res_todo = evaluate_all_conflicts(kpi_todo, details_todo, "Operations Owner")
    assert len(res_todo["conflicts"]) == 0
    assert len(res_todo["audit_notes"]) == 1
    assert "Found potential development issues" in res_todo["audit_notes"][0]["reason"]
    assert res_todo["audit_notes"][0]["severity"] == "Medium"

    # 4. Governance conflict creates high-severity conflict
    kpi_gov = {
        "name": "HSE Safety incident rate",
        "file_path": "data/demo/sample_project/dummy_gov.py",
        "code_context": "SELECT * FROM finance.ledger"
    }
    details_gov = {
        "formula_description": "1.0",
        "business_formula": "1.0"
    }
    res_gov = evaluate_all_conflicts(kpi_gov, details_gov, "HSE Admin")
    assert len(res_gov["conflicts"]) == 1
    assert res_gov["conflicts"][0]["type"] == "domain_conflict"
    assert res_gov["conflicts"][0]["severity"] == "High"


def test_candidate_promotion_gate_quarantines_helper_and_register_noise(tmp_path):
    from bluebook_generator.kpi_extractor import find_kpis_in_directory

    helper = tmp_path / "governance_patch.py"
    helper.write_text(
        'def _normalize_kpi_name(name):\n'
        '    """Normalize KPI names for deterministic ISO template matching."""\n'
        '    text = (name or "").lower()\n'
        '    text = text.replace("_", " ")\n'
        '    return text\n',
        encoding="utf-8",
    )
    meeting_log = tmp_path / "meeting_duration_log.csv"
    meeting_log.write_text(
        "Meeting No,Timezone,Duration Hours\n"
        "1,Asia/Riyadh UTC+3,1.0\n",
        encoding="utf-8",
    )
    checksum = tmp_path / "SOURCE_PACKAGE_CHECKSUMS.csv"
    checksum.write_text(
        "Source_File,SHA256,Role,Legacy_ID\n"
        "jss_evidence.zip,fb55123ef9b644eaeb08e2b6fa8fa60e727f2c3f0ef2451d25ae5b6d766ce8e3,Original package,N/A\n",
        encoding="utf-8",
    )

    kpis, stats = find_kpis_in_directory(str(tmp_path), include_stats=True)
    promoted_names = {k["name"].lower() for k in kpis}
    review_names = {r["candidate_name"].lower() for r in stats["candidate_review"]}

    assert "normalize kpi name" not in promoted_names
    assert "meeting duration log" not in promoted_names
    assert "source package checksums" not in promoted_names
    assert "meeting duration log" in review_names
    assert "source package checksums" in review_names


def test_candidate_promotion_gate_promotes_explicit_formula_kpi(tmp_path):
    from bluebook_generator.kpi_extractor import find_kpis_in_directory

    source = tmp_path / "yield_rate.sql"
    source.write_text(
        "-- KPI: Yield Rate\n"
        "-- Formula: good_output / total_input\n"
        "-- Objective: Track production yield.\n"
        "SELECT good_output / NULLIF(total_input, 0) AS yield_rate FROM production_summary;\n",
        encoding="utf-8",
    )

    kpis, stats = find_kpis_in_directory(str(tmp_path), include_stats=True)
    promoted_names = {k["name"].lower() for k in kpis}

    assert "yield rate" in promoted_names
    assert not stats["candidate_review"]


def test_mate_preserves_explicit_latex_and_formula_annotations():
    from bluebook_generator.main import (
        _latex_formula_html,
        _looks_like_latex_formula,
        _normalize_latex_formula,
    )

    source = (
        r"\mathrm{Yield Rate} = "
        r"\frac{\text{good_output_mass}}{\text{raw_input_mass}} \times 100"
    )
    assert _looks_like_latex_formula(source)

    normalized = _normalize_latex_formula(source)
    assert normalized == (
        r"\mathrm{Yield\,Rate} = "
        r"\frac{\mathrm{good\,output\,mass}}{\mathrm{raw\,input\,mass}} \times 100"
    )

    rendered = _latex_formula_html(source)
    assert rendered["formula_expression"] == normalized
    assert '<div class="math-equation">' in rendered["formula_html"]
    assert "Numerator:</i> good output mass" in rendered["formula_html"]
    assert "Denominator:</i> raw input mass" in rendered["formula_html"]
    assert "Scale:</i> ×100" in rendered["formula_html"]


def test_mate_generated_dossier_contains_annotated_formula_lineage():
    page = Path("docs/_build/ethylene_production_yield.html")
    html = page.read_text(encoding="utf-8")

    assert '<div class="math-equation">' in html
    assert "Annotated Formula" in html
    assert "leap-annotated-equation" in html
    assert 'data-biz="Ethylene Produced"' in html
    assert 'data-dev="VARIABLE: ethylene_produced_tons"' in html
    assert 'data-dev="OPERATOR: /"' in html


def test_iso_22400_yield_rule_detection_and_clean_control():
    from governance_patch import (
        _load_iso_framework,
        detect_yield_operator_conflict,
        detect_yield_variable_conflict,
    )

    framework = _load_iso_framework()
    assert framework["iso_standard_reference"] == "ISO-22400-2:2014"
    assert (
        framework["universal_metric_templates"]["yield_efficiency"]["iso_id"]
        == "ISO-22400-RE-1"
    )

    operator_conflict = detect_yield_operator_conflict({
        "name": "Yield Rate",
        "code_context": (
            "SELECT good_output_mass + raw_input_mass AS yield_rate FROM production"
        ),
    })
    assert operator_conflict["rule_id"] == "ISO-22400-RE-1"
    assert operator_conflict["framework"] == "ISO-22400-2:2014"

    variable_conflict = detect_yield_variable_conflict({
        "name": "Yield Rate",
        "code_context": (
            "SELECT scrap_mass / raw_input_mass AS yield_rate FROM production"
        ),
    })
    assert variable_conflict["rule_id"] == "ISO-22400-RE-1"

    clean = {
        "name": "Yield Rate",
        "code_context": (
            "SELECT good_output_mass / raw_input_mass AS yield_rate FROM production"
        ),
    }
    assert detect_yield_operator_conflict(clean) is None
    assert detect_yield_variable_conflict(clean) is None


def test_iso_22400_asset_utilization_rule_detection_and_clean_control():
    from governance_patch import _load_iso_framework, detect_asset_utilization_conflict

    framework = _load_iso_framework()
    assert (
        framework["universal_metric_templates"]["asset_utilization"]["iso_id"]
        == "ISO-22400-UE-2"
    )

    conflict = detect_asset_utilization_conflict({
        "name": "Asset Utilization",
        "code_context": (
            "SELECT maintenance_down_time / planned_operation_time "
            "AS asset_utilization FROM operations"
        ),
    })
    assert conflict["rule_id"] == "ISO-22400-UE-2"
    assert conflict["framework"] == "ISO-22400-2:2014"

    clean = detect_asset_utilization_conflict({
        "name": "Asset Utilization",
        "code_context": (
            "SELECT actual_production_time / planned_operation_time "
            "AS asset_utilization FROM operations"
        ),
    })
    assert clean is None
