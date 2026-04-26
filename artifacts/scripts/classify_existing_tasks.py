#!/usr/bin/env python3
"""Classify existing task artifacts by risk level based on plan premortem severity.

Scans all TASK-*.plan.md under artifacts/plans/ and extracts Severity values from
the ## Risks section. Outputs a risk_classification.csv to artifacts/registry/.

Usage:
    python classify_existing_tasks.py --dry-run     # preview only
    python classify_existing_tasks.py               # write CSV
"""
from __future__ import annotations

import argparse
import csv
import io
import re
import sys
from pathlib import Path
from typing import List, Sequence, Tuple

SEVERITY_PATTERN = re.compile(r"^\s*-?\s*Severity:\s*(\S+)", re.IGNORECASE)
RISK_ID_PATTERN = re.compile(r"^R(\d+)\s*$", re.MULTILINE)
TASK_ID_PATTERN = re.compile(r"^TASK(?:-LITE)?-\d{3,}$")


def extract_risks_section(text: str) -> str:
    """Extract the ## Risks section from plan text."""
    match = re.search(r"## Risks\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_severities(risks_text: str) -> List[str]:
    """Parse all Severity values from a risks section.

    Handles both standalone lines (``- Severity: blocking``) and inline
    occurrences within a single-line risk description (``... Severity: non-blocking（...）``).
    """
    severities: List[str] = []
    for line in risks_text.splitlines():
        # Find all occurrences of "Severity:" in the line
        for m in re.finditer(r"Severity:\s*(blocking|non-blocking)", line, re.IGNORECASE):
            severities.append(m.group(1).strip().lower())
    return severities


def classify_task(plan_path: Path) -> Tuple[str, str, str, int, int, str]:
    """Classify a single task by its plan's risk severities.

    Returns (task_id, max_severity, risk_level, blocking_count, total_count, excerpt).
    """
    task_id = plan_path.stem.split(".")[0]
    text = plan_path.read_text(encoding="utf-8")
    risks_text = extract_risks_section(text)

    if not risks_text or risks_text.lower() in ("none", "n/a"):
        return (task_id, "none", "low-risk", 0, 0, "(no risks section)")

    severities = parse_severities(risks_text)
    if not severities:
        return (task_id, "unknown", "low-risk", 0, 0, "(risks section found but no Severity field parsed)")

    blocking_count = sum(1 for s in severities if s == "blocking")
    total_count = len(severities)
    max_severity = "blocking" if blocking_count > 0 else "non-blocking"
    risk_level = "high-risk" if blocking_count > 0 else "low-risk"

    # Build excerpt of first 2 severity lines for human audit
    excerpt_lines = []
    for line in risks_text.splitlines():
        if SEVERITY_PATTERN.match(line) or "severity:" in line.lower():
            excerpt_lines.append(line.strip())
            if len(excerpt_lines) >= 2:
                break
    excerpt = " | ".join(excerpt_lines) if excerpt_lines else "(no excerpt)"

    return (task_id, max_severity, risk_level, blocking_count, total_count, excerpt)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Classify existing tasks by risk level.")
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not write CSV")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    plans_dir = root / "artifacts" / "plans"

    if not plans_dir.exists():
        print(f"[ERROR] Plans directory not found: {plans_dir}", file=sys.stderr)
        return 1

    plan_files = sorted(plans_dir.glob("TASK-*.plan.md"))
    if not plan_files:
        print("[ERROR] No plan files found", file=sys.stderr)
        return 1

    results: List[Tuple[str, str, str, int, int, str]] = []
    for plan_path in plan_files:
        result = classify_task(plan_path)
        results.append(result)

    # Print summary
    high_risk_count = sum(1 for r in results if r[2] == "high-risk")
    low_risk_count = sum(1 for r in results if r[2] == "low-risk")
    print(f"\n=== Risk Classification Summary ===")
    print(f"Total tasks classified: {len(results)}")
    print(f"  high-risk (blocking): {high_risk_count}")
    print(f"  low-risk: {low_risk_count}")
    print()

    # Print per-task detail
    for task_id, max_sev, risk_level, blocking, total, excerpt in results:
        marker = "[HIGH]" if risk_level == "high-risk" else "[ OK ]"
        print(f"  {marker} {task_id}: {risk_level} (max={max_sev}, blocking={blocking}/{total})")
        print(f"      excerpt: {excerpt}")

    if args.dry_run:
        print("\n[DRY-RUN] No CSV written.")
        return 0

    # Write CSV
    registry_dir = root / "artifacts" / "registry"
    registry_dir.mkdir(parents=True, exist_ok=True)
    csv_path = registry_dir / "risk_classification.csv"

    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(["task_id", "max_severity", "risk_level", "blocking_count", "total_count"])
    for task_id, max_sev, risk_level, blocking, total, _ in results:
        writer.writerow([task_id, max_sev, risk_level, blocking, total])

    csv_path.write_text(buf.getvalue(), encoding="utf-8")
    print(f"\n[OK] Written {csv_path.relative_to(root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
