# LEAP Dissertation Committee Review Guide

This guide is the committee entry point for the LEAP research artifact. The dissertation examines a knowledge gap: KPI business meaning, mathematical definitions, executable implementations, provenance, and review status are commonly separated across people, documents, and technical systems. LEAP is the hybrid, code-anchored intervention used to investigate whether those forms of knowledge can be made inspectable together.

The package demonstrates implemented technical behavior and provides a reviewable Interactive Bluebook. It should be read alongside the dissertation as evidence of technical feasibility, not as standalone proof of the prospective human and organizational hypotheses. In particular, meeting-duration observations are descriptive and noncausal; claims about reduced clarification time, improved interpretation, or adoption require the planned controlled and participant-level studies.

## 1. Committee Review Route
The candidate package contains a pre-compiled static Interactive Bluebook build that can be reviewed immediately:
- **Starting Point:** Open [docs/_build/index.html](../docs/_build/index.html) in any web browser.
- **RACI Directory:** Navigate to [docs/_build/raci_directory.html](../docs/_build/raci_directory.html) to see stakeholder assignments.
- **Compilation Report:** Navigate to [docs/_build/discovery_report.html](../docs/_build/discovery_report.html) for extraction metrics.

Suggested review sequence:
1. Open the Bluebook index and select a KPI dossier.
2. Compare the business definition, formal formula, evidence and lineage, ownership, and review signals on the same dossier.
3. Open the Discovery Report to inspect how the current sample workspace was inventoried.
4. Use the reproducibility commands below to verify the implemented technical paths.

To run the interactive web application, follow the installation commands in `../README.md`, run:
```bash
python app.py
```
And navigate to `http://127.0.0.1:5000` in your browser.

## 2. Research Artifact: What LEAP Makes Inspectable
- **Business-to-implementation connection:** The dossier is designed to let a reviewer move between a KPI's stated business meaning and the executable evidence available for its calculation.
- **Traceable knowledge representation:** Formula, variables, source location, provenance, ownership, and review status are assembled into a shared record when that evidence exists.
- **Visible uncertainty:** Missing formula declarations, conflicts, weak candidates, and rule-mapped conditions are routed to review rather than treated as silently resolved facts.

## 3. Implemented Technical Capabilities
- **Hybrid Evidence Approach:** LEAP combines deterministic source analysis with AI-agent assistance. Deterministic routes identify and preserve traceable source evidence; the AI layer can provide evidence-grounded explanation and workflow support.
- **Deterministic Evidence Engine:** Scans target source files, extracts KPI comments (e.g. `# KPI:`, `-- Objective:`), and identifies math expressions.
- **MATE (Mathematical Annotation and Tagging Engine):** Renders annotated KPI formulas, associates operators/operands with business and development labels, and presents lineage details inside the Interactive Bluebook.
- **Governance Engine:** Assigns RACI ownership based on source tags and local override rules.
- **Review Queue:** Routes weak metric candidates to the review view, providing owner confirmation guidance, Copy Review Text, and Open Email Draft actions.
- **Compliance Scanner:** Evaluates rules against tested structural scenarios.

## 4. Explicit Boundaries and Evidence Posture
- **VATE (Visual Annotation Engine):** Not implemented.
- **EBRE (Evidence-Based Rule Engine):** Not implemented.
- **AI-Agent Boundary:** The AI agent supplements the evidence workflow; it does not replace source evidence, establish an authoritative formula, or remove the need for human review. Deterministic and AI-assisted capabilities are complementary parts of LEAP's hybrid approach.
- **Compliance Boundaries:** Compliance checks are structural rule checks tested in bounded validation scenarios. They do not constitute legal compliance, regulatory certification, or audit assurance for GDPR, Saudi PDPL, NCA ECC, or SOC 2.
- **Review Workflow Limits:** The review queue provides copy, drafting, and guidance actions. Persistent review state management (e.g., resolutions, approvals, overrides, or mutes) is not implemented.
- **Research Claims:** This package demonstrates the technical intervention and its tested behaviors. It does not independently establish causal effects on meeting duration, documentation effort, comprehension, collaboration, satisfaction, or adoption.

## 5. Local Execution & Privacy Boundaries
- **Offline Operations:** All deterministic parser functions, governance resolutions, and HTML builds execute locally. No source code or metrics data is transmitted to external endpoints.
- **Credential Separation:** API keys are read from standard environment variables (like `OPENAI_API_KEY`) and are never stored or hardcoded.
- **Path and Data Privacy:** Local workspace directories and personal paths are excluded from packaging guides and active configurations. Stakeholder emails in RACI models use template examples (`cfo.office@enterprise.example`).

## 6. Pipeline Reproducibility Commands
To verify the extraction pipeline, run these commands from the repository root:
1. **Regenerate the Bluebook:**
   ```bash
   python run_generation.py sample_project
   ```
2. **Execute Unit Tests:**
   ```bash
   python -m pytest -q
   ```
3. **Verify Scenario Fixtures:**
   ```bash
   python data/validation/test_scenario_fixtures.py
   ```
   This validates all 38 compliance and extraction scenarios under `data/validation/generated_scenario_kpis/`.

## 7. Review Readiness: READY_WITH_QUALIFICATIONS
The committee candidate package is ready for evaluation with the following qualifications:
- AI-agent assistance is evidence-grounded and does not replace technical review or source authority.
- Compliance scanner outputs are bounded checks and do not represent legal compliance certifications.
- VATE and EBRE are not implemented.
- Persistent state management for review queue decisions is not implemented.
- Running the generation pipeline requires local Python dependencies (Sphinx, Flask, python-dotenv, click, Jinja2).
