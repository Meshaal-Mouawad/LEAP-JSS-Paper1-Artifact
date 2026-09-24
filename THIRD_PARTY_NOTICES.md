# Third-party materials in the LEAP Paper 1 artifact

This inventory records redistributed third-party files and release-only removals. It does not treat a logo library's code license as proof that an individual vendor mark may be republished. Five scientific manuscript figures are byte-identical to the pre-release set. The sixth has only an administrative privacy redaction of a local workstation path embedded in its dashboard screenshot; no scientific values, interface evidence, or manuscript claims were changed.

For compactness, `S/` means `software/LEAP/docs/_static/`, and `B/` means `software/LEAP/docs/_build/_static/`. For retained assets, `S/<file>; B/<file>` identifies their source and built copies. The icon filenames listed below describe files deliberately removed from both locations.

## Elsevier LaTeX files: KEEP — ATTRIBUTED

| File | Component and copyright | Redistribution basis | Source URL | Modified |
|---|---|---|---|---|
| `manuscript/cas-dc.cls` | Elsevier CAS Bundle; Elsevier/template contributors | Embedded header permits LPPL 1.2 or later; header preserved | [CTAN CAS bundle](https://ctan.org/pkg/els-cas-templates) | No |
| `manuscript/cas-common.sty` | Elsevier CAS Bundle; Elsevier/template contributors | Embedded header permits LPPL 1.3c or later; header preserved | [CTAN CAS bundle](https://ctan.org/pkg/els-cas-templates) | No |
| `manuscript/cas-model2-names.bst` | Elsevier CAS/elsarticle bundle; copyright Elsevier Ltd 2009-2024 | Embedded header permits LPPL 1.3c or later; header preserved | [CTAN CAS bundle](https://ctan.org/pkg/els-cas-templates) | No |

## Generated documentation assets: KEEP — ATTRIBUTED

These assets are produced by the frozen Sphinx/Read the Docs/Pygments documentation build. The exact source provenance of each generated derivative has not been independently reconstructed, but the named toolchain and upstream redistribution terms are documented. The source and built copies are separately listed below.

| Files | Component and copyright holder | License/basis | Source URL | Modified |
|---|---|---|---|---|
| `S/basic.css; B/basic.css` | Sphinx, Sphinx team | BSD-style Sphinx license | [Sphinx license](https://github.com/sphinx-doc/sphinx/blob/master/LICENSE.rst) | Generated build copy |
| `S/doctools.js; B/doctools.js` | Sphinx, Sphinx team | BSD-style Sphinx license | [Sphinx license](https://github.com/sphinx-doc/sphinx/blob/master/LICENSE.rst) | Generated build copy |
| `S/searchtools.js; B/searchtools.js` | Sphinx, Sphinx team | BSD-style Sphinx license | [Sphinx license](https://github.com/sphinx-doc/sphinx/blob/master/LICENSE.rst) | Generated build copy |
| `S/sphinx_highlight.js; B/sphinx_highlight.js` | Sphinx, Sphinx team | BSD-style Sphinx license | [Sphinx license](https://github.com/sphinx-doc/sphinx/blob/master/LICENSE.rst) | Generated build copy |
| `S/language_data.js; B/language_data.js` | Sphinx, Sphinx team | BSD-style Sphinx license | [Sphinx license](https://github.com/sphinx-doc/sphinx/blob/master/LICENSE.rst) | Generated build copy |
| `S/documentation_options.js; B/documentation_options.js` | Sphinx-generated configuration | Generated output from Sphinx build | [Sphinx repository](https://github.com/sphinx-doc/sphinx) | Generated |
| `S/pygments.css; B/pygments.css` | Pygments-generated highlighting, respective Pygments authors | BSD 2-clause; preserve upstream notice | [Pygments license](https://github.com/pygments/pygments/blob/master/LICENSE) | Generated |
| `S/plus.png; B/plus.png` | Sphinx 8.2.3 Basic theme; Sphinx team | BSD 2-clause; exact SHA-256 `54115199b96a130cba02147c47c0deb43dcc9b9f08b5162bba8642b34980ac63` matches installed `sphinx/themes/basic/static/plus.png` | [Sphinx Basic static source](https://github.com/sphinx-doc/sphinx/tree/v8.2.3/sphinx/themes/basic/static) | No |
| `S/minus.png; B/minus.png` | Sphinx 8.2.3 Basic theme; Sphinx team | BSD 2-clause; exact SHA-256 `47e7fc50db3699f1ca41ce9a2ffa202c00c5d1d5180c55f62ba859b1bd6cc008` matches installed `sphinx/themes/basic/static/minus.png` | [Sphinx Basic static source](https://github.com/sphinx-doc/sphinx/tree/v8.2.3/sphinx/themes/basic/static) | No |
| `S/file.png; B/file.png` | Sphinx 8.2.3 Basic theme; Sphinx team | BSD 2-clause; exact SHA-256 `5c4bc9a16aebf38c4b950f59b8e501ca36495328cb9eb622218bce9064a35e3e` matches installed `sphinx/themes/basic/static/file.png` | [Sphinx Basic static source](https://github.com/sphinx-doc/sphinx/tree/v8.2.3/sphinx/themes/basic/static) | No |

The remaining `S/` and `B/` LEAP logos, metric icons, and `custom.css`/`leap/ECDS_TOKENS.css` are **PROJECT-OWNED** assets, not identified as an external library here. No font binaries are bundled. Google Fonts/CDN Fonts, MathJax, and Tailwind CSS are **REMOTE DEPENDENCIES — NOT REDISTRIBUTED** by this artifact. See `third_party_licenses/` for the Sphinx and Pygments notices that accompany the generated files.

## Platform and vendor icons: REMOVED FROM PUBLIC DISTRIBUTION

Original development snapshot contained graphical marks whose exact upstream redistribution provenance was not retained. They are preserved in the private research/development archive but intentionally excluded from the public research artifact. Product/vendor names remain only as textual identifiers. Every item below was removed from both `S/leap/integration-icons/<file>` and `B/leap/integration-icons/<file>`. No substitute vendor artwork was introduced. Historical source/attribution details remain unestablished; the named product is the former depicted mark, not a verified SVG author.

| Filename (both paths above) | Component / depicted mark | Copyright holder | Redistribution basis | Exact source URL | Modified | Status |
|---|---|---|---|---|---|---|
| `DAX.svg` | Microsoft DAX | Not established | Not established | Not recorded | Local replacement in `f11f8fc9` (`dax.svg` history) | REMOVED FROM PUBLIC DISTRIBUTION |
| `abap.svg` | SAP ABAP | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `aws.svg` | Amazon Web Services | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `azuredevops.svg` | Microsoft Azure DevOps | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `bitbucket.svg` | Atlassian Bitbucket | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `confluence.svg` | Atlassian Confluence | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `csharp.svg` | Microsoft C# | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `csv.svg` | Generic CSV file mark | Not established | Local SVG, origin not recorded | Not recorded | Local change in `f11f8fc9` | REMOVED FROM PUBLIC DISTRIBUTION |
| `databricks.svg` | Databricks | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `dynamics-365.svg` | Microsoft Dynamics 365 | Not established | Not established | Not recorded | Local replacement in `f11f8fc9` | REMOVED FROM PUBLIC DISTRIBUTION |
| `gitlab.svg` | GitLab | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `hana.svg` | SAP HANA | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `iec-st.svg` | Generic IEC structured text mark | Not established | Local SVG, origin not recorded | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `jenkins.svg` | Jenkins | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `jira.svg` | Atlassian Jira | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `microsoft-teams.svg` | Microsoft Teams | Not established | Not established | Not recorded | Local change in `f11f8fc9` | REMOVED FROM PUBLIC DISTRIBUTION |
| `microsoft.svg` | Microsoft | Not established | Not established | Not recorded | Local change in `f11f8fc9` | REMOVED FROM PUBLIC DISTRIBUTION |
| `microsoftsqlserver.svg` | Microsoft SQL Server | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `oracle.svg` | Oracle | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `postgresql.svg` | PostgreSQL | Not established | Not established | Not recorded | Local replacement in `f11f8fc9` | REMOVED FROM PUBLIC DISTRIBUTION |
| `power-bi.svg` | Microsoft Power BI | Not established | Not established | Not recorded | Local change in `f11f8fc9` | REMOVED FROM PUBLIC DISTRIBUTION |
| `python.svg` | Python | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `salesforce.svg` | Salesforce | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `sap.svg` | SAP | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `servicenow.svg` | ServiceNow | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `slack.svg` | Slack | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `sqldeveloper.svg` | Oracle SQL Developer | Not established | Not established | Not recorded | Local change in `f11f8fc9` | REMOVED FROM PUBLIC DISTRIBUTION |
| `tableau.svg` | Tableau | Not established | Not established | Not recorded | Local change in `f11f8fc9` | REMOVED FROM PUBLIC DISTRIBUTION |
| `visualbasic.svg` | Microsoft Visual Basic | Not established | Not established | Not recorded | Unknown upstream | REMOVED FROM PUBLIC DISTRIBUTION |
| `workday.svg` | Workday | Not established | Not established | Not recorded | Local change in `f11f8fc9` | REMOVED FROM PUBLIC DISTRIBUTION |

The [Simple Icons disclaimer](https://github.com/simple-icons/simple-icons/blob/develop/DISCLAIMER.md) distinguishes the library license from individual brand-icon status. These 30 marks were removed rather than blanket-labeled CC0 or MIT.
