#!/usr/bin/env python3
"""Backfill PDCA Stage metadata labels and TAO Trace blocks into existing artifacts.

Phase 5 of TASK-1000: adds ``- PDCA Stage: P/D/C`` to plan/code/verify Metadata
sections, and optionally inserts ``## TAO Trace`` blocks for high-risk tasks.

Usage:
    python backfill_pdca_labels.py --dry-run          # preview all changes
    python backfill_pdca_labels.py                    # apply PDCA Stage labels
    python backfill_pdca_labels.py --include-tao      # also insert TAO Trace blocks
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

TAIPEI_TZ = timezone(timedelta(hours=8))
PDCA_LABELS = {
    "plan": "P",
    "code": "D",
    "verify": "C",
}
ARTIFACT_DIRS = {
    "plan": "plans",
    "code": "code",
    "verify": "verify",
}
ARTIFACT_EXTENSIONS = {
    "plan": ".plan.md",
    "code": ".code.md",
    "verify": ".verify.md",
}

PDCA_STAGE_PATTERN = re.compile(r"^- PDCA Stage:", re.MULTILINE)
LAST_UPDATED_PATTERN = re.compile(r"^(- Last Updated:\s*.+)$", re.MULTILINE)
TAO_TRACE_HEADING = "## TAO Trace"

# Insert TAO Trace after these headings (in order of preference)
TAO_INSERT_AFTER_CODE = ("## Known Risks",)
TAO_INSERT_BEFORE_CODE = ("## Blockers",)
TAO_INSERT_AFTER_VERIFY = ("## Build Guarantee",)
TAO_INSERT_BEFORE_VERIFY = ("## Pass Fail Result",)

RECONSTRUCTED_TAO_BLOCK = """## TAO Trace

Reconstructed from artifact history. This task predates the TAO schema (introduced in TASK-1000 Phase 2).

### Step 1
- Thought Log: (Reconstructed) Reviewed plan Proposed Changes and executed accordingly.
- Action Step: Implemented changes per plan scope.
- Observation: Completed (inferred from verify artifact AC checklist).
- Next-Step Decision: continue
"""


def current_taipei_timestamp() -> str:
    return datetime.now(TAIPEI_TZ).isoformat(timespec="seconds")


def load_high_risk_tasks(csv_path: Path) -> Set[str]:
    """Load high-risk task IDs from risk_classification.csv."""
    high_risk: Set[str] = set()
    if not csv_path.exists():
        return high_risk
    with csv_path.open(encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("risk_level") == "high-risk":
                high_risk.add(row["task_id"])
    return high_risk


def backfill_pdca_stage(text: str, pdca_label: str) -> Tuple[str, bool]:
    """Insert ``- PDCA Stage: X`` after ``- Last Updated:`` if not present.

    Returns (new_text, changed).
    """
    if PDCA_STAGE_PATTERN.search(text):
        return text, False

    match = LAST_UPDATED_PATTERN.search(text)
    if not match:
        return text, False

    insertion = f"\n- PDCA Stage: {pdca_label}"
    new_text = text[:match.end()] + insertion + text[match.end():]
    return new_text, True


def insert_tao_trace_code(text: str) -> Tuple[str, bool]:
    """Insert TAO Trace block into a code artifact."""
    if TAO_TRACE_HEADING in text:
        return text, False

    # Try inserting before ## Blockers
    for before in TAO_INSERT_BEFORE_CODE:
        idx = text.find(f"\n{before}")
        if idx >= 0:
            new_text = text[:idx] + "\n\n" + RECONSTRUCTED_TAO_BLOCK.rstrip() + "\n" + text[idx:]
            return new_text, True

    # Fallback: append before end
    return text.rstrip() + "\n\n" + RECONSTRUCTED_TAO_BLOCK, True


def insert_tao_trace_verify(text: str) -> Tuple[str, bool]:
    """Insert TAO Trace block into a verify artifact."""
    if TAO_TRACE_HEADING in text:
        return text, False

    # Try inserting before ## Pass Fail Result
    for before in TAO_INSERT_BEFORE_VERIFY:
        idx = text.find(f"\n{before}")
        if idx >= 0:
            new_text = text[:idx] + "\n\n" + RECONSTRUCTED_TAO_BLOCK.rstrip() + "\n" + text[idx:]
            return new_text, True

    # Fallback: append before end
    return text.rstrip() + "\n\n" + RECONSTRUCTED_TAO_BLOCK, True


def process_artifact(
    path: Path,
    artifact_type: str,
    high_risk_tasks: Set[str],
    include_tao: bool,
    dry_run: bool,
) -> List[str]:
    """Process a single artifact file. Returns list of change descriptions."""
    changes: List[str] = []
    task_id = path.stem.split(".")[0]

    text = path.read_text(encoding="utf-8")
    original = text

    # 1. PDCA Stage backfill
    pdca_label = PDCA_LABELS.get(artifact_type, "?")
    text, pdca_changed = backfill_pdca_stage(text, pdca_label)
    if pdca_changed:
        changes.append(f"  + PDCA Stage: {pdca_label}")

    # 2. TAO Trace backfill (high-risk only)
    if include_tao and task_id in high_risk_tasks:
        if artifact_type == "code":
            text, tao_changed = insert_tao_trace_code(text)
        elif artifact_type == "verify":
            text, tao_changed = insert_tao_trace_verify(text)
        else:
            tao_changed = False

        if tao_changed:
            changes.append("  + TAO Trace (reconstructed)")

    if not changes:
        return []

    if not dry_run:
        path.write_text(text, encoding="utf-8")

    return changes


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Backfill PDCA Stage labels and TAO Trace blocks.")
    parser.add_argument("--root", default=".", help="Repository root (default: .)")
    parser.add_argument("--dry-run", action="store_true", help="Preview only, do not modify files")
    parser.add_argument("--include-tao", action="store_true", help="Also insert TAO Trace for high-risk tasks")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    artifacts_root = root / "artifacts"

    # Load risk classification if available
    csv_path = root / "artifacts" / "registry" / "risk_classification.csv"
    high_risk_tasks = load_high_risk_tasks(csv_path)
    if args.include_tao and not high_risk_tasks:
        print("[WARN] --include-tao specified but no risk_classification.csv found or no high-risk tasks")

    total_changed = 0
    total_skipped = 0

    for artifact_type, subdir in ARTIFACT_DIRS.items():
        artifact_dir = artifacts_root / subdir
        if not artifact_dir.exists():
            continue

        ext = ARTIFACT_EXTENSIONS[artifact_type]
        for path in sorted(artifact_dir.glob(f"TASK-*{ext}")):
            changes = process_artifact(path, artifact_type, high_risk_tasks, args.include_tao, args.dry_run)
            if changes:
                task_id = path.stem.split(".")[0]
                label = "[DRY-RUN] " if args.dry_run else ""
                print(f"{label}{task_id}.{artifact_type}:")
                for change in changes:
                    print(change)
                total_changed += 1
            else:
                total_skipped += 1

    print(f"\n=== Backfill Summary ===")
    print(f"Changed: {total_changed}")
    print(f"Skipped (already up-to-date): {total_skipped}")
    if args.dry_run:
        print("[DRY-RUN] No files modified.")
    else:
        print("[OK] Backfill complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
