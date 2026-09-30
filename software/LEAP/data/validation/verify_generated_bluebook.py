#!/usr/bin/env python3
"""Verify generated LEAP Bluebook HTML without regenerating it.

This checker is intentionally conservative: it flags rendering, compliance,
asset, and status consistency defects as errors, while broad-scan artifacts
from testing an entire repository are reported as warnings.
"""

from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, asdict
from html import unescape
from pathlib import Path
from urllib.parse import urldefrag, unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
DOCS_BUILD = ROOT / "docs" / "_build"
REPORT_MD = Path(__file__).resolve().parent / "generated_bluebook_validation_report.md"
REPORT_JSON = Path(__file__).resolve().parent / "generated_bluebook_validation_report.json"

COMPLIANCE_STANDARDS = {
    "KSA-PDPL-REG-01": "KSA PDPL",
    "KSA-NCA-ECC-SEC-04": "KSA NCA ECC",
    "KSA-NCA-ECC-AUD-02": "KSA NCA ECC",
    "GDPR-DATA-PROC-01": "GDPR",
    "SOC2-LINEAGE-AUDIT-01": "SOC2",
}

FORMULA_PATTERNS = [
    ("bad_result_slash", re.compile(r"Result\s*=\s*/")),
    ("bad_text_slash", re.compile(r"\\text\{\s*/\s*\}")),
    ("bad_text_nullif", re.compile(r"\\text\{\s*Nullif\s*\}", re.I)),
    ("bad_mathrm_case", re.compile(r"\\Mathrm|\\Frac")),
    ("mathjax_error_markup", re.compile(r"merror|mathcolor", re.I)),
    ("raw_underscore_in_mathrm", re.compile(r"\\mathrm\{[^}]*_[^}]*\}")),
]

FORBIDDEN_COMPLIANCE_CLAIMS = [
    "legally compliant",
    "SOC 2 Type II compliant",
    "GDPR compliant",
    "PDPL compliant",
]

SCAN_NOISE_SLUGS = {
    "archive_manifest",
    "claim_audit",
    "claim_status_register",
    "current_architecture",
    "historical_claim_map",
    "inconsistency_register",
    "language_support",
    "normalize_kpi_name",
    "raw_evidence_checksums",
    "research_record_register",
    "source_note_inventory",
    "source_package_checksums",
    "start_generation",
    "transformation_log",
    "verify_scenario_rendered_alarms",
    "webp_to_svg",
    "generate_figures",
    "generate_last_figs",
    "count_generated_kpis",
}


@dataclass
class Finding:
    severity: str
    category: str
    page: str
    detail: str


def strip_tags(html: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html)).strip()


def page_title(html: str, fallback: str) -> str:
    h1 = re.search(r"<h1[^>]*>(.*?)</h1>", html, re.S | re.I)
    if h1:
        return unescape(strip_tags(h1.group(1)))
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.S | re.I)
    if title:
        return unescape(strip_tags(title.group(1)))
    return fallback


def local_html_pages() -> list[Path]:
    ignored = {
        "genindex.html",
        "search.html",
        "py-modindex.html",
    }
    return sorted(
        p for p in DOCS_BUILD.glob("*.html")
        if p.name not in ignored and not p.name.startswith("_")
    )


def check_assets_and_links(pages: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    attr_re = re.compile(r"""(?:href|src)=["']([^"']+)["']""", re.I)
    for page in pages:
        html = page.read_text(errors="replace")
        for raw in attr_re.findall(html):
            target, _frag = urldefrag(unescape(raw))
            if not target or re.match(r"^[a-z][a-z0-9+.-]*:", target, re.I):
                continue
            if target.startswith("#") or target.startswith("mailto:"):
                continue
            if target.startswith("/"):
                continue
            decoded = unquote(urlsplit(target).path)
            if decoded.endswith((".html", ".css", ".js", ".svg", ".png", ".webp", ".ico")) or "_static/" in decoded:
                resolved = (page.parent / decoded).resolve()
                try:
                    resolved.relative_to(DOCS_BUILD.resolve())
                except ValueError:
                    continue
                if not resolved.exists():
                    findings.append(Finding("ERROR", "missing_asset_or_link", page.name, decoded))
    return findings


def check_formula_safety(pages: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    math_block_re = re.compile(r"<div[^>]+class=[\"'][^\"']*math-equation[^\"']*[\"'][^>]*>(.*?)</div>", re.S | re.I)
    for page in pages:
        html = page.read_text(errors="replace")
        for category, pattern in FORMULA_PATTERNS:
            for match in pattern.finditer(html):
                excerpt = strip_tags(html[max(0, match.start() - 80): match.end() + 80])
                findings.append(Finding("ERROR", category, page.name, excerpt[:240]))
        for block in math_block_re.findall(html):
            content = strip_tags(block)
            if not content or content in {"\\[ \\]", "\\[\\]"}:
                findings.append(Finding("ERROR", "empty_math_equation", page.name, "Empty Formal Formula MathJax block"))
    return findings


def check_compliance_mapping(pages: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    alarm_re = re.compile(
        r"<div[^>]+class=[\"'][^\"']*compliance-alarm-card[^\"']*[\"'][^>]*>(.*?)</div>\s*</div>?",
        re.S | re.I,
    )
    for page in pages:
        html = page.read_text(errors="replace")
        text = unescape(strip_tags(html))
        lower = text.lower()
        for phrase in FORBIDDEN_COMPLIANCE_CLAIMS:
            if phrase.lower() in lower:
                findings.append(Finding("ERROR", "forbidden_compliance_claim", page.name, phrase))
        for card_html in alarm_re.findall(html):
            card_text = unescape(strip_tags(card_html))
            for rule_id, expected in COMPLIANCE_STANDARDS.items():
                if rule_id not in card_text:
                    continue
                if f"Mapped Standard: {expected}" not in card_text and f"Rule mapped: {expected}" not in card_text:
                    findings.append(
                        Finding("ERROR", "wrong_or_missing_mapped_standard", page.name, f"{rule_id} expected {expected}")
                    )
                if "ISO Compliance & Governance Conflict" in card_text:
                    findings.append(
                        Finding("ERROR", "generic_iso_wording_near_compliance_alarm", page.name, rule_id)
                    )
    return findings


def check_review_queue_and_status(pages: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for page in pages:
        html = page.read_text(errors="replace")
        text = unescape(strip_tags(html))
        if "Audit Note:" in text:
            findings.append(Finding("ERROR", "stale_audit_note_text", page.name, "Audit Note:"))

        has_review_queue = 'id="governance-review-note"' in html
        has_alarm = any(marker in text for marker in [
            "COMPLIANCE REVIEW REQUIRED",
            "GOVERNANCE REVIEW REQUIRED",
            "TECHNICAL REVIEW REQUIRED",
            "OWNER CONFIRMATION REQUIRED",
            "Governance conflict detected",
            "Alert detected:",
        ])

        status_match = re.search(r"Governance Status\s+(Validated|Needs Review)", text, re.I)
        status = status_match.group(1).title() if status_match else ""
        if status == "Validated" and (has_review_queue or has_alarm):
            findings.append(
                Finding("ERROR", "validated_page_with_review_queue", page.name, "Validated status with review/alarm content")
            )

        # Repeated owner-confirmation cards are noisy and caused confusion during RC-G-3.3.
        owner_count = text.count("OWNER CONFIRMATION REQUIRED")
        if owner_count > 1:
            findings.append(Finding("ERROR", "duplicate_owner_confirmation", page.name, f"{owner_count} occurrences"))
    return findings


def check_scan_noise(pages: list[Path]) -> list[Finding]:
    warnings: list[Finding] = []
    for page in pages:
        slug = page.stem
        if slug in SCAN_NOISE_SLUGS:
            warnings.append(
                Finding("WARNING", "broad_scan_artifact_page", page.name, "Likely generated from research/script/register artifact")
            )
        if slug == "customer_activity_indexndef_calculatenational_id_phone_num_pass":
            warnings.append(
                Finding("WARNING", "suspicious_slug", page.name, "Slug appears to include executable code text")
            )
    return warnings


def write_reports(pages: list[Path], findings: list[Finding]) -> None:
    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARNING"]
    summary = {
        "docs_build": str(DOCS_BUILD),
        "html_pages_checked": len(pages),
        "errors": len(errors),
        "warnings": len(warnings),
        "findings": [asdict(f) for f in findings],
    }
    REPORT_JSON.write_text(json.dumps(summary, indent=2))

    lines = [
        "# Generated Bluebook Validation Report",
        "",
        f"- HTML pages checked: {len(pages)}",
        f"- Errors: {len(errors)}",
        f"- Warnings: {len(warnings)}",
        "",
    ]
    if errors:
        lines += ["## Errors", ""]
        for f in errors:
            lines.append(f"- **{f.category}** — `{f.page}`: {f.detail}")
        lines.append("")
    if warnings:
        lines += ["## Warnings", ""]
        for f in warnings:
            lines.append(f"- **{f.category}** — `{f.page}`: {f.detail}")
        lines.append("")
    if not findings:
        lines.append("No errors or warnings detected.")
    REPORT_MD.write_text("\n".join(lines) + "\n")


def main() -> int:
    if not DOCS_BUILD.exists():
        print(f"ERROR: docs build folder not found: {DOCS_BUILD}")
        return 2

    pages = local_html_pages()
    findings: list[Finding] = []
    findings.extend(check_assets_and_links(pages))
    findings.extend(check_formula_safety(pages))
    findings.extend(check_compliance_mapping(pages))
    findings.extend(check_review_queue_and_status(pages))
    findings.extend(check_scan_noise(pages))

    findings.sort(key=lambda f: (f.severity != "ERROR", f.category, f.page, f.detail))
    write_reports(pages, findings)

    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARNING"]
    print(f"Checked {len(pages)} generated HTML pages.")
    print(f"Errors: {len(errors)}")
    print(f"Warnings: {len(warnings)}")
    print(f"Report: {REPORT_MD}")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
