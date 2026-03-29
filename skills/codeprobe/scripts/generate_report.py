#!/usr/bin/env python3
"""
generate_report.py -- Aggregate JSON findings into a Markdown audit report.

Reads the orchestrator's findings JSON and fills the full-audit-report template.
Writes the completed report ONLY to the specified output path (never inside the project).
Dependencies: Python 3.8+ standard library only.

Usage:
    python3 generate_report.py --input findings.json --output /tmp/report.md
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Category key -> (display name, weight for sorting)
CATEGORIES: Dict[str, Tuple[str, float]] = {
    "review-security":       ("Security",         0.20),
    "review-solid":          ("SOLID Compliance",  0.15),
    "review-architecture":   ("Architecture",      0.15),
    "review-error-handling": ("Error Handling",    0.12),
    "review-performance":    ("Performance",       0.12),
    "review-testing":        ("Test Quality",      0.10),
    "review-code-smells":    ("Code Smells",       0.08),
    "review-patterns":       ("Design Patterns",   0.04),
    "review-framework":      ("Framework Usage",   0.04),
}

SEVERITY_ORDER: List[str] = ["critical", "major", "minor", "suggestion"]

SEVERITY_LABELS: Dict[str, str] = {
    "critical":   "Critical",
    "major":      "Major",
    "minor":      "Minor",
    "suggestion": "Suggestion",
}


def error_exit(message: str) -> None:
    """Print a JSON error to stdout and exit with code 1."""
    json.dump({"error": message}, sys.stdout, indent=2)
    print()
    sys.exit(1)


def load_template() -> str:
    """Load the report template relative to this script's location."""
    script_dir = Path(__file__).resolve().parent
    template_path = script_dir.parent / "templates" / "full-audit-report.md"
    if template_path.is_file():
        return template_path.read_text(encoding="utf-8")
    return ""


def collect_all_findings(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten all findings from every category into a single list."""
    findings: List[Dict[str, Any]] = []
    categories = data.get("categories", {})
    for cat_key, cat_data in categories.items():
        display_name = CATEGORIES.get(cat_key, (cat_key, 0.0))[0]
        for f in cat_data.get("findings", []):
            entry = dict(f)
            entry["_category_key"] = cat_key
            entry["_category_name"] = display_name
            findings.append(entry)
    return findings


def severity_rank(severity: str) -> int:
    """Return numeric rank for sorting (lower = more severe)."""
    try:
        return SEVERITY_ORDER.index(severity.lower())
    except ValueError:
        return len(SEVERITY_ORDER)


def sort_findings(findings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Sort findings by severity first, then by category weight (descending)."""
    def sort_key(f: Dict[str, Any]) -> Tuple[int, float]:
        sev = severity_rank(f.get("severity", "suggestion"))
        weight = CATEGORIES.get(f.get("_category_key", ""), ("", 0.0))[1]
        return (sev, -weight)
    return sorted(findings, key=sort_key)


def build_score_table(data: Dict[str, Any]) -> str:
    """Build the score breakdown table rows."""
    lines: List[str] = []
    categories = data.get("categories", {})
    for cat_key, (display_name, _weight) in CATEGORIES.items():
        cat = categories.get(cat_key, {})
        score = cat.get("score", "N/A")
        summary = cat.get("summary", {})
        crit = summary.get("critical", 0)
        major = summary.get("major", 0)
        minor = summary.get("minor", 0)
        sugg = summary.get("suggestion", 0)
        lines.append(
            f"| {display_name} | {score} | {crit} | {major} | {minor} | {sugg} |"
        )
    return "\n".join(lines)


def format_finding_full(f: Dict[str, Any]) -> str:
    """Format a single finding in full detail (for critical/major sections)."""
    fid = f.get("id", "???")
    problem = f.get("problem", "No description")
    loc = f.get("location", {})
    fpath = loc.get("file", "unknown")
    flines = loc.get("lines", "?")
    evidence = f.get("evidence", "N/A")
    suggestion = f.get("suggestion", "N/A")
    fix_prompt = f.get("fix_prompt", "N/A")
    return (
        f"**{fid}** -- {problem}\n"
        f"- **File:** `{fpath}` (lines {flines})\n"
        f"- **Evidence:** {evidence}\n"
        f"- **Suggestion:** {suggestion}\n"
        f"- **Fix Prompt:** `{fix_prompt}`"
    )


def format_finding_compact(f: Dict[str, Any]) -> str:
    """Format a single finding as a compact one-liner (for minor/suggestion)."""
    fid = f.get("id", "???")
    loc = f.get("location", {})
    fpath = loc.get("file", "unknown")
    flines = loc.get("lines", "?")
    problem = f.get("problem", "No description")
    suggestion = f.get("suggestion", "N/A")
    return f"- **{fid}** `{fpath}:{flines}` -- {problem} -> {suggestion}"


def build_severity_section(
    findings: List[Dict[str, Any]], severity: str, full: bool
) -> str:
    """Build the section for a given severity level."""
    subset = [f for f in findings if f.get("severity", "").lower() == severity]
    if not subset:
        return "None found."
    if full:
        return "\n\n".join(format_finding_full(f) for f in subset)
    return "\n".join(format_finding_compact(f) for f in subset)


def build_quick_wins(findings: List[Dict[str, Any]], count: int = 5) -> str:
    """Select the top N quick wins (highest severity, most impactful)."""
    candidates = [f for f in findings if f.get("fix_prompt")]
    if not candidates:
        return "No actionable quick wins identified."
    lines: List[str] = []
    for i, f in enumerate(candidates[:count], 1):
        fix = f.get("fix_prompt", "")
        sev = SEVERITY_LABELS.get(f.get("severity", ""), "Issue")
        cat = f.get("_category_name", "General")
        lines.append(f"{i}. {fix} -- {sev} in {cat}")
    return "\n".join(lines)


def build_roadmap(findings: List[Dict[str, Any]]) -> str:
    """Build an ordered refactoring roadmap from sorted findings."""
    actionable = [f for f in findings if f.get("fix_prompt")]
    if not actionable:
        return "No refactoring steps identified."
    ordinals = ["First", "Then", "Then", "Then", "Then", "Then", "Then", "Then"]
    lines: List[str] = []
    for i, f in enumerate(actionable):
        label = ordinals[i] if i < len(ordinals) else "Then"
        fix = f.get("fix_prompt", "")
        sev = SEVERITY_LABELS.get(f.get("severity", ""), "Issue")
        cat = f.get("_category_name", "General")
        reason = f"addresses {sev.lower()} {cat.lower()} issue"
        if i > 0:
            reason += ", depends on earlier fixes"
        lines.append(f"{i + 1}. **{label}:** {fix} -- {reason}")
    return "\n".join(lines)


def build_fix_prompts(findings: List[Dict[str, Any]]) -> str:
    """Build a numbered list of all fix prompts, severity-ordered."""
    prompts = [f.get("fix_prompt", "") for f in findings if f.get("fix_prompt")]
    if not prompts:
        return "No fix prompts available."
    return "\n".join(f"{i}. {p}" for i, p in enumerate(prompts, 1))


def generate_report(data: Dict[str, Any]) -> str:
    """Generate the full Markdown report from findings data."""
    all_findings = sort_findings(collect_all_findings(data))

    project_name = data.get("project_name", "Unknown Project")
    date = data.get("date", "N/A")
    stacks = data.get("detected_stacks", [])
    stacks_str = ", ".join(stacks) if stacks else "Not detected"
    overall_score = data.get("overall_score", "N/A")

    template = load_template()

    # Build all sections
    score_table = build_score_table(data)
    critical_section = build_severity_section(all_findings, "critical", full=True)
    major_section = build_severity_section(all_findings, "major", full=True)
    minor_section = build_severity_section(all_findings, "minor", full=False)
    suggestion_section = build_severity_section(all_findings, "suggestion", full=False)
    quick_wins = build_quick_wins(all_findings)
    roadmap = build_roadmap(all_findings)
    fix_prompts = build_fix_prompts(all_findings)

    # If template loaded, we ignore its placeholders and generate inline
    # (template uses non-standard {placeholders} mixed with iteration markers)
    report_lines = [
        "# Code Review Audit Report",
        "",
        f"## Project: {project_name}",
        f"## Date: {date}",
        f"## Detected Stack: {stacks_str}",
        "",
        "---",
        "",
        f"### Overall Score: {overall_score} / 100",
        "",
        "### Score Breakdown",
        "",
        "| Category | Score | Critical | Major | Minor | Suggestion |",
        "|----------|-------|----------|-------|-------|------------|",
        score_table,
        "",
        "---",
        "",
        "### Critical Issues (Fix Immediately)",
        "",
        critical_section,
        "",
        "---",
        "",
        "### Major Issues (Fix This Sprint)",
        "",
        major_section,
        "",
        "---",
        "",
        "### Minor Issues (Tech Debt Backlog)",
        "",
        minor_section,
        "",
        "---",
        "",
        "### Suggestions",
        "",
        suggestion_section,
        "",
        "---",
        "",
        "### Top 5 Quick Wins",
        "",
        quick_wins,
        "",
        "---",
        "",
        "### Refactoring Roadmap",
        "",
        roadmap,
        "",
        "---",
        "",
        "### Fix Prompts (Copy into Claude Code)",
        "",
        fix_prompts,
        "",
        "---",
        "",
        "*Generated by code-review-claude v2.0.0 -- Read-only analysis -- no files were modified*",
        "",
    ]
    return "\n".join(report_lines)


def validate_output_path(output_path: str, data: Dict[str, Any]) -> None:
    """Ensure the output path is not inside the project directory."""
    project_path = data.get("project_path")
    if not project_path:
        return
    resolved_output = os.path.realpath(output_path)
    resolved_project = os.path.realpath(project_path)
    if resolved_output.startswith(resolved_project + os.sep):
        error_exit(
            f"Output path is inside the project directory: {output_path}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a Markdown audit report from findings JSON."
    )
    parser.add_argument("--input", required=True, help="Path to findings JSON file")
    parser.add_argument("--output", required=True, help="Path for the output report")
    args = parser.parse_args()

    # Read input JSON
    if not os.path.isfile(args.input):
        error_exit(f"Input file not found: {args.input}")

    try:
        with open(args.input, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        error_exit(f"Invalid JSON in input file: {e}")
    except (OSError, IOError) as e:
        error_exit(f"Cannot read input file: {e}")

    # Safety check
    validate_output_path(args.output, data)

    # Generate the report
    report = generate_report(data)

    # Write output
    try:
        output_dir = os.path.dirname(args.output)
        if output_dir and not os.path.isdir(output_dir):
            os.makedirs(output_dir, exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(report)
    except (OSError, IOError) as e:
        error_exit(f"Cannot write output file: {e}")

    # Summary to stdout
    all_findings = collect_all_findings(data)
    counts = {}
    for sev in SEVERITY_ORDER:
        counts[sev] = sum(
            1 for fl in all_findings if fl.get("severity", "").lower() == sev
        )
    total = len(all_findings)
    print(f"Report generated: {args.output}")
    print(f"Total findings: {total} "
          f"(critical: {counts['critical']}, major: {counts['major']}, "
          f"minor: {counts['minor']}, suggestion: {counts['suggestion']})")


if __name__ == "__main__":
    main()
