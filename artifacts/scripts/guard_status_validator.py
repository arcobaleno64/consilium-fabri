#!/usr/bin/env python3
"""
Artifact-first workflow guard script.

Purpose:
- Validate status.json structure
- Validate artifact presence and minimal schema markers
- Validate workflow state transitions using WORKFLOW_STATE_MACHINE rules
- Prevent illegal jumps such as drafted -> coding or coding -> done

Usage:
  python guard_status_validator.py --task-id TASK-001
  python guard_status_validator.py --task-id TASK-001 --from-state planned --to-state coding
  python guard_status_validator.py --task-id TASK-001 --artifacts-root ./artifacts
  python guard_status_validator.py --task-id TASK-001 --write-transition planned coding

Exit codes:
  0 = valid
  1 = validation failed
  2 = usage error
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple


__version__ = "0.1.0"


STATE_ORDER = [
    "drafted",
    "researched",
    "planned",
    "coding",
    "testing",
    "verifying",
    "done",
    "blocked",
]

VALID_STATES: Set[str] = set(STATE_ORDER)

# Legal transitions based on the workflow state machine.
LEGAL_TRANSITIONS: Dict[str, Set[str]] = {
    "drafted": {"researched", "blocked"},
    "researched": {"planned", "blocked"},
    "planned": {"coding", "blocked"},
    "coding": {"testing", "verifying", "blocked"},
    "testing": {"verifying", "coding", "blocked"},
    "verifying": {"done", "coding", "blocked"},
    "done": set(),
    "blocked": {
        "drafted",
        "researched",
        "planned",
        "coding",
        "testing",
        "verifying",
    },
}

ARTIFACT_DIRS: Dict[str, str] = {
    "task": "tasks",
    "research": "research",
    "plan": "plans",
    "code": "code",
    "test": "test",
    "verify": "verify",
    "decision": "decisions",
    "status": "status",
}

ARTIFACT_EXTENSIONS: Dict[str, str] = {
    "task": ".task.md",
    "research": ".research.md",
    "plan": ".plan.md",
    "code": ".code.md",
    "test": ".test.md",
    "verify": ".verify.md",
    "decision": ".decision.md",
    "status": ".status.json",
}

# Minimum artifact requirements by state.
STATE_REQUIRED_ARTIFACTS: Dict[str, Set[str]] = {
    "drafted": {"task", "status"},
    "researched": {"task", "research", "status"},
    "planned": {"task", "plan", "status"},
    "coding": {"task", "plan", "code", "status"},
    "testing": {"task", "plan", "code", "test", "status"},
    "verifying": {"task", "code", "status"},
    "done": {"task", "code", "verify", "status"},
    "blocked": {"task", "status"},
}

# Additional conditional requirements.
DONE_VERIFY_PASS_REQUIRED = True

# Minimal markdown markers per artifact type.
MARKERS: Dict[str, Sequence[str]] = {
    "task": (
        "# Task:",
        "## Metadata",
        "Task ID:",
        "Artifact Type: task",
        "## Objective",
        "## Constraints",
        "## Acceptance Criteria",
    ),
    "research": (
        "# Research:",
        "## Metadata",
        "Artifact Type: research",
        "## Research Questions",
        "## Confirmed Facts",
        "## Constraints For Implementation",
    ),
    "plan": (
        "# Plan:",
        "## Metadata",
        "Artifact Type: plan",
        "## Scope",
        "## Files Likely Affected",
        "## Proposed Changes",
        "## Validation Strategy",
        "## Ready For Coding",
    ),
    "code": (
        "# Code Result:",
        "## Metadata",
        "Artifact Type: code",
        "## Files Changed",
        "## Summary Of Changes",
        "## Mapping To Plan",
    ),
    "test": (
        "# Test Report:",
        "## Metadata",
        "Artifact Type: test",
        "## Test Scope",
        "## Commands Executed",
        "## Result Summary",
    ),
    "verify": (
        "# Verification:",
        "## Metadata",
        "Artifact Type: verify",
        "## Acceptance Criteria Checklist",
        "## Pass Fail Result",
        "## Build Guarantee",
    ),
    "decision": (
        "# Decision Log:",
        "## Metadata",
        "Artifact Type: decision",
        "## Issue",
        "## Chosen Option",
        "## Reasoning",
    ),
}

TASK_ID_PATTERN = re.compile(r"^TASK-\d{3,}$")

# Premortem guard: minimum risk count by task category.
PREMORTEM_MIN_RISKS_DEFAULT = 2
PREMORTEM_MIN_RISKS_HIGH = 4  # security / dependency / upstream PR / cross-repo

# Required fields in each risk entry.
PREMORTEM_REQUIRED_FIELDS = ("Risk:", "Trigger:", "Detection:", "Mitigation:", "Severity:")

# Prohibited vague phrases (standalone — if no concrete fields follow).
PREMORTEM_BANNED_PHRASES = (
    "風險低",
    "應該沒問題",
    "可能有風險",
    "視情況而定",
    "再觀察",
    "注意一下",
    "需評估",
    "有待確認",
)


@dataclass
class ValidationResult:
    errors: List[str]
    warnings: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors


class GuardError(Exception):
    pass


def artifact_path(artifacts_root: Path, task_id: str, artifact_type: str) -> Path:
    if artifact_type not in ARTIFACT_DIRS:
        raise GuardError(f"Unknown artifact type: {artifact_type}")
    directory = ARTIFACT_DIRS[artifact_type]
    extension = ARTIFACT_EXTENSIONS[artifact_type]
    return artifacts_root / directory / f"{task_id}{extension}"


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise GuardError(f"Missing JSON file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise GuardError(f"Invalid JSON in {path}: {exc}") from exc


def load_text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise GuardError(f"Missing text file: {path}") from exc


def validate_task_id(task_id: str) -> List[str]:
    errors: List[str] = []
    if not TASK_ID_PATTERN.match(task_id):
        errors.append(
            f"Invalid task id '{task_id}'. Expected format like TASK-001."
        )
    return errors


def validate_status_schema(status: dict, expected_task_id: str) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    required_keys = {
        "task_id",
        "state",
        "current_owner",
        "next_agent",
        "required_artifacts",
        "available_artifacts",
        "missing_artifacts",
        "blocked_reason",
        "last_updated",
    }

    missing = required_keys - set(status.keys())
    if missing:
        errors.append(f"status.json missing required keys: {sorted(missing)}")

    if status.get("task_id") != expected_task_id:
        errors.append(
            f"status.json task_id mismatch. Expected {expected_task_id}, got {status.get('task_id')}"
        )

    state = status.get("state")
    if state not in VALID_STATES:
        errors.append(f"Invalid state: {state!r}")

    for key in ("required_artifacts", "available_artifacts", "missing_artifacts"):
        value = status.get(key)
        if not isinstance(value, list):
            errors.append(f"status.json field '{key}' must be a list")
            continue
        unknown = sorted(set(value) - set(ARTIFACT_DIRS.keys()))
        if unknown:
            errors.append(f"status.json field '{key}' contains unknown artifacts: {unknown}")

    if state == "blocked" and not str(status.get("blocked_reason", "")).strip():
        errors.append("blocked state requires non-empty blocked_reason")

    if state != "blocked" and str(status.get("blocked_reason", "")).strip():
        warnings.append("blocked_reason is non-empty while state is not blocked")

    return ValidationResult(errors, warnings)


def validate_markdown_artifact(path: Path, artifact_type: str, task_id: str) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    text = load_text(path)
    missing_markers = [marker for marker in MARKERS[artifact_type] if marker not in text]
    if missing_markers:
        errors.append(
            f"{path.name} missing required markers: {missing_markers}"
        )

    if f"Task ID: {task_id}" not in text:
        errors.append(f"{path.name} missing exact task id marker 'Task ID: {task_id}'")

    owner_match = re.search(r"^- Owner:\s*(.+)$", text, re.MULTILINE)
    if not owner_match or not owner_match.group(1).strip():
        errors.append(f"{path.name} missing non-empty Owner field")

    status_match = re.search(r"^- Status:\s*(.+)$", text, re.MULTILINE)
    if not status_match or not status_match.group(1).strip():
        errors.append(f"{path.name} missing non-empty Status field")

    updated_match = re.search(r"^- Last Updated:\s*(.+)$", text, re.MULTILINE)
    if not updated_match or not updated_match.group(1).strip():
        errors.append(f"{path.name} missing non-empty Last Updated field")

    if artifact_type == "plan":
        if not re.search(r"## Ready For Coding\s+\n?\s*(yes|no)\b", text, re.IGNORECASE):
            warnings.append(
                f"{path.name} does not clearly declare Ready For Coding as yes/no"
            )

    if artifact_type == "verify":
        if not re.search(r"## Pass Fail Result\s+\n?\s*(pass|fail)\b", text, re.IGNORECASE):
            warnings.append(
                f"{path.name} does not clearly declare Pass Fail Result as pass/fail"
            )

    return ValidationResult(errors, warnings)


def verify_result_is_pass(verify_path: Path) -> bool:
    text = load_text(verify_path)
    match = re.search(r"## Pass Fail Result\s+\n?\s*(pass|fail)\b", text, re.IGNORECASE)
    return bool(match and match.group(1).lower() == "pass")


def plan_ready_for_coding(plan_path: Path) -> bool:
    text = load_text(plan_path)
    match = re.search(r"## Ready For Coding\s+\n?\s*(yes|no)\b", text, re.IGNORECASE)
    return bool(match and match.group(1).lower() == "yes")


def validate_premortem(plan_path: Path, task_id: str) -> ValidationResult:
    """Validate premortem quality in the plan artifact's ## Risks section.

    Enforces PREMORTEM_RULES.md and PREMORTEM_GUARD_RULES.md:
    - Each risk must be numbered (R1, R2, ...)
    - Each risk must have Risk, Trigger, Detection, Mitigation, Severity fields
    - Severity must be 'blocking' or 'non-blocking'
    - At least PREMORTEM_MIN_RISKS_DEFAULT entries (2 for normal tasks)
    - Banned vague phrases without concrete follow-up are rejected
    """
    errors: List[str] = []
    warnings: List[str] = []

    text = load_text(plan_path)

    # Extract ## Risks section content (up to next ##)
    risks_match = re.search(
        r"## Risks\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL
    )
    if not risks_match:
        errors.append(
            f"{plan_path.name}: premortem check failed — ## Risks section not found"
        )
        return ValidationResult(errors, warnings)

    risks_text = risks_match.group(1).strip()

    if not risks_text or risks_text.lower() in ("none", "n/a", "low risk", ""):
        errors.append(
            f"{plan_path.name}: premortem check failed — ## Risks section is empty or trivially dismissed"
        )
        return ValidationResult(errors, warnings)

    # Find all risk entries (R1, R2, R3, ...)
    risk_entries = re.findall(r"\bR(\d+)\b", risks_text)
    risk_count = len(set(risk_entries))

    if risk_count < PREMORTEM_MIN_RISKS_DEFAULT:
        errors.append(
            f"{plan_path.name}: premortem requires at least {PREMORTEM_MIN_RISKS_DEFAULT} "
            f"numbered risks (R1, R2, ...), found {risk_count}"
        )

    # Check each required field exists at least once
    for field in PREMORTEM_REQUIRED_FIELDS:
        if field not in risks_text:
            errors.append(
                f"{plan_path.name}: premortem missing required field '{field}'"
            )

    # Check severity values are valid
    severity_values = re.findall(r"Severity:\s*(.+)", risks_text)
    for sv in severity_values:
        sv_clean = sv.strip().lower()
        if sv_clean not in ("blocking", "non-blocking"):
            errors.append(
                f"{plan_path.name}: premortem Severity must be 'blocking' or 'non-blocking', got '{sv.strip()}'"
            )

    # Check for at least one blocking risk
    has_blocking = any(
        "blocking" == sv.strip().lower() for sv in severity_values
    )
    if not has_blocking and risk_count > 0:
        warnings.append(
            f"{plan_path.name}: premortem has no blocking risk — review whether this is appropriate"
        )

    # Check for banned vague phrases (only flag if they appear without structured fields nearby)
    for phrase in PREMORTEM_BANNED_PHRASES:
        if phrase in risks_text:
            warnings.append(
                f"{plan_path.name}: premortem contains potentially vague phrase '{phrase}' — ensure it has concrete trigger/detection/mitigation"
            )

    return ValidationResult(errors, warnings)


def compute_existing_artifacts(artifacts_root: Path, task_id: str) -> Set[str]:
    found: Set[str] = set()
    for artifact_type in ARTIFACT_DIRS:
        path = artifact_path(artifacts_root, task_id, artifact_type)
        if path.exists():
            found.add(artifact_type)
    return found


def state_required_artifacts(state: str, existing: Set[str]) -> Set[str]:
    required = set(STATE_REQUIRED_ARTIFACTS[state])

    # If research exists or the status already claims it, planned/coding/testing/verifying/done
    # may reasonably require it. This keeps validation strict without forcing it on all tasks.
    if state in {"planned", "coding", "testing", "verifying", "done"} and "research" in existing:
        required.add("research")

    if state in {"verifying", "done"} and "test" in existing:
        required.add("test")

    return required


def validate_artifact_presence(
    artifacts_root: Path,
    task_id: str,
    state: str,
    status: dict,
) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    existing = compute_existing_artifacts(artifacts_root, task_id)
    required = state_required_artifacts(state, existing)

    missing_required = sorted(required - existing)
    if missing_required:
        errors.append(
            f"Missing required artifacts for state '{state}': {missing_required}"
        )

    status_available = set(status.get("available_artifacts", []))
    status_missing = set(status.get("missing_artifacts", []))
    status_required = set(status.get("required_artifacts", []))

    if status_available != existing:
        warnings.append(
            f"available_artifacts mismatch. status.json={sorted(status_available)} actual={sorted(existing)}"
        )

    if status_required != required:
        warnings.append(
            f"required_artifacts mismatch. status.json={sorted(status_required)} computed={sorted(required)}"
        )

    computed_missing = required - existing
    if status_missing != computed_missing:
        warnings.append(
            f"missing_artifacts mismatch. status.json={sorted(status_missing)} computed={sorted(computed_missing)}"
        )

    for artifact_type in sorted(existing - {"status"}):
        path = artifact_path(artifacts_root, task_id, artifact_type)
        result = validate_markdown_artifact(path, artifact_type, task_id)
        errors.extend(result.errors)
        warnings.extend(result.warnings)

    if state in {"coding", "testing", "verifying", "done"}:
        plan_path = artifact_path(artifacts_root, task_id, "plan")
        if plan_path.exists() and not plan_ready_for_coding(plan_path):
            errors.append(
                f"Plan artifact is not Ready For Coding = yes: {plan_path.name}"
            )
        # Premortem gate: validate risk quality before/during coding.
        # Hard-block on 'coding' state (the entry gate).
        # Downgrade to warnings on later states (legacy tasks may lack premortem).
        if plan_path.exists():
            premortem_result = validate_premortem(plan_path, task_id)
            if state == "coding":
                errors.extend(premortem_result.errors)
            else:
                warnings.extend(premortem_result.errors)
            warnings.extend(premortem_result.warnings)

    if state == "done" and DONE_VERIFY_PASS_REQUIRED:
        verify_path = artifact_path(artifacts_root, task_id, "verify")
        if verify_path.exists() and not verify_result_is_pass(verify_path):
            errors.append("done state requires verify artifact with Pass Fail Result = pass")

    return ValidationResult(errors, warnings)


def validate_transition(from_state: str, to_state: str) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    if from_state not in VALID_STATES:
        errors.append(f"Unknown from_state: {from_state}")
        return ValidationResult(errors, warnings)
    if to_state not in VALID_STATES:
        errors.append(f"Unknown to_state: {to_state}")
        return ValidationResult(errors, warnings)

    allowed = LEGAL_TRANSITIONS.get(from_state, set())
    if to_state not in allowed:
        errors.append(f"Illegal state transition: {from_state} -> {to_state}")

    return ValidationResult(errors, warnings)


def validate_all(artifacts_root: Path, task_id: str) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    errors.extend(validate_task_id(task_id))
    if errors:
        return ValidationResult(errors, warnings)

    status_path = artifact_path(artifacts_root, task_id, "status")
    status = load_json(status_path)

    schema_result = validate_status_schema(status, task_id)
    errors.extend(schema_result.errors)
    warnings.extend(schema_result.warnings)

    state = status.get("state")
    if state in VALID_STATES:
        presence_result = validate_artifact_presence(artifacts_root, task_id, state, status)
        errors.extend(presence_result.errors)
        warnings.extend(presence_result.warnings)

    return ValidationResult(errors, warnings)


def write_transition(artifacts_root: Path, task_id: str, from_state: str, to_state: str) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []

    transition_result = validate_transition(from_state, to_state)
    errors.extend(transition_result.errors)
    warnings.extend(transition_result.warnings)
    if errors:
        return ValidationResult(errors, warnings)

    full_result = validate_all(artifacts_root, task_id)
    errors.extend(full_result.errors)
    warnings.extend(full_result.warnings)
    if errors:
        return ValidationResult(errors, warnings)

    status_path = artifact_path(artifacts_root, task_id, "status")
    status = load_json(status_path)
    actual_state = status.get("state")

    if actual_state != from_state:
        errors.append(
            f"Refusing transition because status.json state is {actual_state}, not expected {from_state}"
        )
        return ValidationResult(errors, warnings)

    # Pre-transition artifact checks for target state.
    target_presence = validate_artifact_presence(artifacts_root, task_id, to_state, status)
    if target_presence.errors:
        errors.append(
            f"Target state '{to_state}' requirements are not yet satisfied."
        )
        errors.extend(target_presence.errors)
        warnings.extend(target_presence.warnings)
        return ValidationResult(errors, warnings)

    status["state"] = to_state
    status["required_artifacts"] = sorted(state_required_artifacts(to_state, compute_existing_artifacts(artifacts_root, task_id)))
    status["available_artifacts"] = sorted(compute_existing_artifacts(artifacts_root, task_id))
    status["missing_artifacts"] = sorted(
        state_required_artifacts(to_state, compute_existing_artifacts(artifacts_root, task_id))
        - compute_existing_artifacts(artifacts_root, task_id)
    )
    if to_state != "blocked":
        status["blocked_reason"] = ""

    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ValidationResult(errors, warnings)


def print_result(result: ValidationResult) -> None:
    if result.ok:
        print("[OK] Validation passed")
    else:
        print("[ERROR] Validation failed")

    for warning in result.warnings:
        print(f"[WARN] {warning}")
    for error in result.errors:
        print(f"[FAIL] {error}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate artifact workflow status and transitions.")
    parser.add_argument("--task-id", required=True, help="Task id, for example TASK-001")
    parser.add_argument(
        "--artifacts-root",
        default="./artifacts",
        help="Artifacts root directory. Default: ./artifacts",
    )
    parser.add_argument(
        "--from-state",
        help="Validate a proposed transition from this state",
    )
    parser.add_argument(
        "--to-state",
        help="Validate a proposed transition to this state",
    )
    parser.add_argument(
        "--write-transition",
        nargs=2,
        metavar=("FROM_STATE", "TO_STATE"),
        help="Validate and write the transition into status.json if allowed",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    artifacts_root = Path(args.artifacts_root).resolve()

    try:
        if args.write_transition:
            from_state, to_state = args.write_transition
            result = write_transition(artifacts_root, args.task_id, from_state, to_state)
            print_result(result)
            return 0 if result.ok else 1

        if bool(args.from_state) != bool(args.to_state):
            print("[FAIL] --from-state and --to-state must be used together", file=sys.stderr)
            return 2

        result = validate_all(artifacts_root, args.task_id)
        if args.from_state and args.to_state:
            transition_result = validate_transition(args.from_state, args.to_state)
            result.errors.extend(transition_result.errors)
            result.warnings.extend(transition_result.warnings)

        print_result(result)
        return 0 if result.ok else 1
    except GuardError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"[FAIL] Unexpected error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
