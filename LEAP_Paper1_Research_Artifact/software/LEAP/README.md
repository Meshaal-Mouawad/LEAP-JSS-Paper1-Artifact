# LEAP: A Literate Programming Framework Bridging Code and Business Knowledge through Deterministic Analysis and AI-Assisted Authoring for Enterprise KPI Knowledge Engineering

LEAP is the research artifact for a dissertation addressing a persistent enterprise knowledge problem: the business meaning of a Key Performance Indicator (KPI), its mathematical definition, its implementation in source code, and its governance record are often maintained in separate systems and by different stakeholders.

This separation creates a recurring translation burden between business and technical teams. It can make KPI interpretation difficult, obscure the relationship between documentation and executable logic, complicate governance reviews, and allow business descriptions to drift from the code that produces reported values.

The dissertation investigates whether literate programming can provide a structured bridge between these forms of knowledge. LEAP instantiates that research framework by combining:

- deterministic source-code and repository analysis;
- optional AI-assisted literate authoring;
- evidence-grounded KPI knowledge representations;
- provenance and source traceability;
- formula and dependency presentation;
- business and technical explanations;
- ownership, review, and governance signals; and
- an Interactive Bluebook for inspecting the resulting knowledge.

Executable source code remains authoritative for what a system computes. LEAP does not replace that authority. Instead, it creates a traceable knowledge representation through which technical and business stakeholders can examine the available evidence together.

---

## Dissertation Research Context

The dissertation is organized under the following umbrella title:

> **Bridging Code and Business Knowledge through Literate Programming: Deterministic Analysis and AI-Assisted Authoring for Enterprise KPI Knowledge Engineering**

Literate programming is the central theoretical and methodological foundation of the research. It is not treated only as a documentation style or user-interface feature.

The dissertation extends the literate-programming principle of presenting executable logic together with human-readable explanation into the domain of enterprise KPI knowledge engineering. It examines how source evidence, formulas, variables, dependencies, definitions, explanatory narratives, provenance, ownership, and review information can be represented as an integrated and inspectable body of knowledge.

LEAP is the proof-of-concept implementation used to instantiate and examine that framework.

The dissertation’s individual papers and chapters address specific developments of the same framework, including:

1. deterministic construction of traceable KPI evidence;
2. AI-assisted authoring of literate KPI explanations and documentation;
3. interactive presentation, review, governance, and knowledge exploration through the Bluebook.

These developments are not separate research systems. They are complementary components of the broader literate-programming framework.

---

## Research Proposition

The research proposition is not that software generation alone solves an organizational communication problem.

The proposition is that code-anchored, literate KPI knowledge can provide a durable boundary object between:

- people who define, govern, interpret, and use a metric; and
- people who implement, test, maintain, and operate the code that computes it.

LEAP investigates this proposition through a hybrid technical approach.

### Deterministic analysis

The deterministic layer identifies, structures, and preserves evidence available in source repositories and related artifacts.

Depending on the available source material, this layer may support:

- repository and file discovery;
- identification of KPI-related implementation evidence;
- source-location capture;
- variable and formula reconstruction;
- dependency and lineage representation;
- provenance tracking;
- structured evidence generation; and
- reproducible Bluebook construction.

The deterministic layer provides the correctness-critical and traceable foundation of the system.

### AI-assisted literate authoring

When AI capabilities are enabled, the AI layer works from structured evidence to assist with authoring the human-readable portions of the literate representation.

Depending on configuration and available evidence, AI assistance may support drafting:

- KPI definitions;
- business-facing explanations;
- technical explanations;
- formula narratives;
- dependency descriptions;
- source-code commentary;
- literate-programming sections;
- review prompts; and
- stakeholder-oriented documentation.

AI-authored content is not treated as authoritative source evidence. It should remain distinguishable from deterministic findings and subject to human review.

### Interactive knowledge presentation

LEAP publishes the resulting information through an Interactive Bluebook.

A Bluebook record may bring together:

- KPI name and available definition;
- mathematical or computational formula;
- variables and dependencies;
- implementation locations;
- source provenance;
- business and technical explanations;
- ownership information;
- review status;
- governance signals; and
- visible uncertainty or incomplete evidence.

The Interactive Bluebook is one developed output of the framework. It is not the complete dissertation contribution.

---

## What This Repository Demonstrates

This repository allows reviewers to inspect the implemented research artifact behind the dissertation proposition.

It demonstrates:

- deterministic discovery and structuring of KPI evidence from heterogeneous source artifacts;
- traceable links between generated records and available source evidence;
- optional AI-assisted authoring grounded in structured evidence;
- reconstruction and presentation of formula lineage where evidence is available;
- generation of an Interactive Bluebook;
- presentation of business-facing and technical information in a shared record;
- provenance, ownership, governance, and review indicators;
- controlled validation scenarios; and
- automated tests of selected technical behaviors.

The repository demonstrates the implemented system and its technical behavior. It does not, by itself, establish organizational or causal outcomes.

---

## What This Repository Does Not Claim

This package does **not** claim:

- universal KPI-detection accuracy;
- universal formula-reconstruction accuracy;
- legal, regulatory, or accounting certification;
- replacement of expert review;
- replacement of source-code inspection;
- proof that AI-authored explanations are always correct;
- completed human-subject evaluation;
- causal reductions in meeting duration;
- causal reductions in documentation effort;
- elimination of stakeholder misunderstandings; or
- guaranteed organizational adoption.

Historical meeting observations discussed in the dissertation provide contextual and descriptive evidence concerning communication burden. They do not independently demonstrate that LEAP caused a reduction in meeting duration.

Likewise, final claims concerning precision, recall, formula fidelity, interpretation, usability, cognitive bridging, collaboration, or organizational outcomes require the separately governed adjudicated or participant-level evidence described in the dissertation.

---

## Committee Review

Begin with the:

[Committee Review Guide](Committee_Read/COMMITTEE_REVIEW_GUIDE.md)

The guide provides a focused route through:

- the research proposition;
- the artifact boundaries;
- the static Bluebook;
- representative KPI records;
- provenance and traceability features;
- controlled validation scenarios; and
- reproducibility checks.

### Static Bluebook review

After cloning or downloading the repository, open the following file in a local browser:

```text
docs/_build/index.html
```

The static build allows reviewers to inspect the generated Bluebook without launching the local application.

---

## Repository Review Path

For a focused committee review, use the following sequence:

1. Read this README.
2. Read `Committee_Read/COMMITTEE_REVIEW_GUIDE.md`.
3. Open `docs/_build/index.html`.
4. Inspect representative Bluebook records and their provenance.
5. Review the controlled validation scenarios.
6. Run the technical test suite.
7. Generate a new sample Bluebook.
8. Launch the local workspace when interactive review is needed.

---

## Technical Requirements

- Python 3.10 or later
- `pip`
- a Python virtual environment
- a modern web browser
- Git, when cloning the repository

AI-assisted authoring may require additional configuration and credentials depending on the selected provider. Credentials must not be committed to this repository.

The deterministic workflow and included static review materials should remain inspectable independently of optional AI services.

---

## Installation

Clone the repository and enter the project directory:

```bash
git clone <repository-url>
cd <repository-directory>
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it on macOS or Linux:

```bash
source .venv/bin/activate
```

Activate it on Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

Install the project and its dependencies in editable mode:

```bash
python -m pip install --upgrade pip
pip install -e .
```

---

## Generate the Sample Bluebook

Run:

```bash
python run_generation.py sample_project
```

This command processes the included sample project and generates the corresponding Bluebook output.

Generated records should be interpreted in relation to the evidence available in the sample project. Absence of information in a Bluebook record may indicate that the corresponding evidence was unavailable, unsupported, or not identified by the configured analysis.

---

## Run the Technical Tests

Run the primary test suite:

```bash
python -m pytest -q
```

Run the controlled scenario validation:

```bash
python data/validation/test_scenario_fixtures.py
```

These tests examine selected implemented behaviors. Passing tests demonstrate that the tested technical conditions were satisfied in the current environment. They do not establish universal extraction accuracy or human-subject outcomes.

---

## Launch the Local Workspace

Run:

```bash
python app.py
```

Then open:

```text
http://127.0.0.1:5000
```

The local workspace supports interactive inspection of the implemented artifact.

Stop the server with:

```text
Ctrl+C
```

---

## Reproducibility

For committee submission, the repository should be associated with a fixed release, tag, or commit.

Record the inspected version with:

```bash
git rev-parse HEAD
```

Reviewers should use the committee-designated commit or release so that the source code, static Bluebook, tests, and dissertation references remain aligned.

Reproducibility may be affected by:

- Python version;
- dependency versions;
- operating system;
- optional AI-provider availability;
- model or service changes;
- local configuration;
- source-project contents; and
- credentials or network restrictions.

Deterministic outputs should be reproducible under the documented configuration and the same input artifacts. AI-assisted outputs may vary across providers, models, configurations, or execution times.

---

## Evidence and Provenance Principles

LEAP follows several evidence-handling principles:

1. **Source code remains authoritative for executable behavior.**
2. **Deterministic findings should remain traceable to their source locations.**
3. **AI-authored content should not be presented as deterministic evidence.**
4. **Missing or ambiguous evidence should remain visible.**
5. **Generated explanations should remain reviewable.**
6. **Governance metadata should not be interpreted as certification.**
7. **Technical tests should not be presented as human-subject validation.**
8. **Artifact behavior should not be generalized beyond the evidence evaluated.**

These principles are intended to reduce unsupported certainty and preserve the distinction between extracted evidence, generated explanation, and human interpretation.

---

## Security and Confidentiality

Do not commit:

- API keys;
- access tokens;
- passwords;
- private certificates;
- proprietary enterprise source code;
- confidential KPI definitions;
- participant-level research data;
- personally identifiable information;
- protected organizational records; or
- machine-specific secret configuration.

Use environment variables or locally managed configuration for optional credentials.

Before applying LEAP to an enterprise repository, confirm that the source material may be processed under the applicable organizational, contractual, research, and data-governance requirements.

---

## Scope of the Committee Package

This committee package contains:

- the runnable LEAP research artifact;
- a static Interactive Bluebook build;
- a sample project;
- controlled validation scenarios;
- automated technical tests; and
- concise committee-review material.

It does not contain the complete separately governed research-evidence archive unless that archive has been explicitly included through an approved submission process.

It should not be interpreted as:

- legal certification;
- regulatory approval;
- universal extraction validation;
- completed organizational evaluation; or
- completed human-subject evidence.

---

## Conceptual Grounding

LEAP builds on research concerning literate programming, program understanding, knowledge capture, computational narratives, living documentation, and AI-assisted documentation.

Selected works include:

- Knuth, D. E. (1984). *Literate Programming*. The Computer Journal, 27(2), 97–111.  
  https://doi.org/10.1093/comjnl/27.2.97

- Rugaber, S. (2000). *The Use of Domain Knowledge in Program Understanding*. Annals of Software Engineering, 9, 143–192.  
  https://doi.org/10.1023/A:1018976708691

- Correia, F. F., and Aguiar, A. (2009). *Software Knowledge Capture and Acquisition: Tool Support for Agile Settings*. Fourth International Conference on Software Engineering Advances.  
  https://ieeexplore.ieee.org/document/5298747

- Schulte, E., Davison, D., Dye, T., and Dominik, C. (2012). *A Multi-Language Computing Environment for Literate Programming and Reproducible Research*. Journal of Statistical Software, 46(3), 1–24.  
  https://doi.org/10.18637/jss.v046.i03

- Martraire, C. (2019). *Living Documentation: Continuous Knowledge Sharing by Design*. Addison-Wesley Professional.  
  https://www.informit.com/store/living-documentation-continuous-knowledge-sharing-by-9780134689326

- Wang, A. Y., Wang, D., Drozdal, J., Muller, M., Park, S., Weisz, J. D., Liu, X., Wu, L., and Dugan, C. (2022). *Documentation Matters: Human-Centered AI System to Assist Data Science Code Documentation in Computational Notebooks*. ACM Transactions on Computer-Human Interaction.  
  https://doi.org/10.1145/3489465

- McNutt, A. M., Wang, C., Deline, R., and Drucker, S. M. (2023). *On the Design of AI-Powered Code Assistants for Notebooks*. Proceedings of the 2023 CHI Conference on Human Factors in Computing Systems.  
  https://doi.org/10.1145/3544548.3580940

- Petersen, S. D., Levassor, L., Pedersen, C. M., and colleagues. (2024). *teemi: An Open-Source Literate Programming Approach for Iterative Design-Build-Test-Learn Cycles in Bioengineering*. PLOS Computational Biology, 20(3), e1011929.  
  https://doi.org/10.1371/journal.pcbi.1011929

---

## Research-Artifact Boundary

LEAP should be interpreted as an implemented research artifact supporting investigation of a broader proposition:

> Literate programming can bridge executable KPI logic and business knowledge when deterministic evidence construction, AI-assisted authoring, provenance, and human review are combined in a traceable enterprise knowledge representation.

The artifact demonstrates how that proposition can be instantiated technically. The dissertation’s empirical studies determine which claims can be supported beyond the implementation itself.