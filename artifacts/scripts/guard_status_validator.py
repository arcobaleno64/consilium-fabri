#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set

__version__ = "0.4.0"

STATE_ORDER = ["drafted", "researched", "planned", "coding", "testing", "verifying", "done", "blocked"]
VALID_STATES: Set[str] = set(STATE_ORDER)
LEGAL_TRANSITIONS: Dict[str, Set[str]] = {
    "drafted": {"researched", "blocked"},
    "researched": {"planned", "blocked"},
    "planned": {"coding", "blocked"},
    "coding": {"testing", "verifying", "blocked"},
    "testing": {"verifying", "coding", "blocked"},
    "verifying": {"done", "coding", "blocked"},
    "done": set(),
    "blocked": {"drafted", "researched", "planned", "coding", "testing", "verifying"},
}
ARTIFACT_DIRS = {
    "task": "tasks",
    "research": "research",
    "plan": "plans",
    "code": "code",
    "test": "test",
    "verify": "verify",
    "decision": "decisions",
    "improvement": "improvement",
    "status": "status",
}
ARTIFACT_EXTENSIONS = {
    "task": ".task.md",
    "research": ".research.md",
    "plan": ".plan.md",
    "code": ".code.md",
    "test": ".test.md",
    "verify": ".verify.md",
    "decision": ".decision.md",
    "improvement": ".improvement.md",
    "status": ".status.json",
}
STATE_REQUIRED_ARTIFACTS = {
    "drafted": {"task", "status"},
    "researched": {"task", "research", "status"},
    "planned": {"task", "plan", "status"},
    "coding": {"task", "plan", "code", "status"},
    "testing": {"task", "plan", "code", "test", "status"},
    "verifying": {"task", "code", "status"},
    "done": {"task", "code", "verify", "status"},
    "blocked": {"task", "status"},
}
MARKERS = {
    "task": ("# Task:", "## Metadata", "Task ID:", "Artifact Type: task", "## Objective", "## Constraints", "## Acceptance Criteria"),
    "research": ("# Research:", "## Metadata", "Artifact Type: research", "## Research Questions", "## Confirmed Facts", "## Relevant References", "## Uncertain Items", "## Constraints For Implementation"),
    "plan": ("# Plan:", "## Metadata", "Artifact Type: plan", "## Scope", "## Files Likely Affected", "## Proposed Changes", "## Validation Strategy", "## Ready For Coding"),
    "code": ("# Code Result:", "## Metadata", "Artifact Type: code", "## Files Changed", "## Summary Of Changes", "## Mapping To Plan"),
    "test": ("# Test Report:", "## Metadata", "Artifact Type: test", "## Test Scope", "## Commands Executed", "## Result Summary"),
    "verify": ("# Verification:", "## Metadata", "Artifact Type: verify", "## Acceptance Criteria Checklist", "## Pass Fail Result", "## Build Guarantee"),
    "decision": ("# Decision Log:", "## Metadata", "Artifact Type: decision", "## Issue", "## Chosen Option", "## Reasoning"),
    "improvement": ("# Process Improvement", "## Metadata", "Artifact Type: improvement", "Source Task:", "Trigger Type:", "## 1. What Happened", "## 2. Why It Was Not Prevented", "## 3. Failure Classification", "## 5. Preventive Action (System Level)", "## 6. Validation", "## 8. Final Rule", "## 9. Status"),
}
ARTIFACT_ALLOWED_STATUSES = {
    "task": {"drafted", "approved", "blocked", "done"},
    "research": {"in_progress", "ready", "blocked", "superseded"},
    "plan": {"drafted", "ready", "approved", "blocked", "superseded"},
    "code": {"in_progress", "ready", "blocked", "superseded"},
    "test": {"in_progress", "pass", "fail", "blocked", "superseded"},
    "verify": {"pass", "fail", "blocked", "superseded"},
    "decision": {"done"},
    "improvement": {"draft", "approved", "applied"},
}

TASK_ID_PATTERN = re.compile(r"^TASK-\d{3,}$")
TAIPEI_TIMESTAMP_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?\+08:00$")
CITATION_PATTERN = re.compile(r"(https?://\S+|`gh api [^`]+`|`[^`\n]+\.(?:md|json|txt|py|ps1|csproj)[^`\n]*`)", re.IGNORECASE)
LIST_ITEM_PATTERN = re.compile(r"^(?:- |\d+\. )")
GITHUB_REPO_REF_PATTERNS = (
    re.compile(r"https?://github\.com/([^/\s]+)/([^/\s`#?]+)/?", re.IGNORECASE),
    re.compile(r"https?://raw\.githubusercontent\.com/([^/\s]+)/([^/\s`#?]+)/", re.IGNORECASE),
)
FILE_PATH_TOKEN_PATTERN = re.compile(r"\b(?:[A-Za-z]:[\\/])?[A-Za-z0-9_.\-\\/]+\.[A-Za-z0-9]{1,10}\b")
PREMORTEM_MIN_RISKS_DEFAULT = 2
PREMORTEM_MIN_RISKS_HIGH = 4
PREMORTEM_REQUIRED_FIELDS = ("Risk:", "Trigger:", "Detection:", "Mitigation:", "Severity:")
PREMORTEM_BANNED_PHRASES = ("風險低", "應該沒問題", "可能有風險", "視情況而定", "再觀察", "注意一下", "需評估", "有待確認")
HIGH_RISK_KEYWORDS = ("security", "安全", "dependency", "依賴", "upstream pr", "upstream", "cross-repo", "cross repo", "跨 repo")


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
    return artifacts_root / ARTIFACT_DIRS[artifact_type] / f"{task_id}{ARTIFACT_EXTENSIONS[artifact_type]}"


def find_artifact_paths(artifacts_root: Path, task_id: str, artifact_type: str) -> List[Path]:
    if artifact_type == "improvement":
        return sorted((artifacts_root / ARTIFACT_DIRS[artifact_type]).glob(f"{task_id}*.improvement.md"))
    path = artifact_path(artifacts_root, task_id, artifact_type)
    return [path] if path.exists() else []


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


def extract_section(text: str, heading: str) -> str:
    match = re.search(rf"## {re.escape(heading)}\s*\n(.*?)(?=\n## |\Z)", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def parse_list_items(section_text: str) -> List[str]:
    items: List[str] = []
    current: List[str] = []
    for raw_line in section_text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            if current:
                current.append("")
            continue
        stripped = line.strip()
        if LIST_ITEM_PATTERN.match(stripped):
            if current:
                items.append("\n".join(current).strip())
            current = [LIST_ITEM_PATTERN.sub("", stripped, count=1)]
        elif current:
            current.append(stripped)
        else:
            current = [stripped]
    if current:
        items.append("\n".join(current).strip())
    return [item for item in items if item and item.lower() != "none"]


def normalize_path_token(token: str) -> str:
    value = token.strip().strip("`\"'.,:;()[]{}")
    value = value.replace("\\", "/")
    if re.match(r"^[A-Za-z]:/", value):
        value = value[2:]
    if value.startswith("./"):
        value = value[2:]
    if value.startswith("a/") or value.startswith("b/"):
        value = value[2:]
    return value


def extract_file_tokens(section_text: str) -> Set[str]:
    tokens: Set[str] = set()
    for item in parse_list_items(section_text):
        for inline in re.findall(r"`([^`\n]+)`", item):
            normalized = normalize_path_token(inline)
            if "." in normalized:
                tokens.add(normalized)
        for match in FILE_PATH_TOKEN_PATTERN.findall(item):
            normalized = normalize_path_token(match)
            if "." in normalized:
                tokens.add(normalized)
    return tokens


def detect_mixed_github_sources(text: str) -> List[str]:
    owners_by_repo: Dict[str, Set[str]] = {}
    for pattern in GITHUB_REPO_REF_PATTERNS:
        for owner, repo in pattern.findall(text):
            normalized_repo = repo.lower()
            owners_by_repo.setdefault(normalized_repo, set()).add(owner.lower())
    mixed: List[str] = []
    for repo, owners in sorted(owners_by_repo.items()):
        if len(owners) > 1:
            mixed.append(f"{repo}: {sorted(owners)}")
    return mixed


def detect_plan_code_scope_drift(plan_text: str, code_text: str) -> List[str]:
    planned_files = extract_file_tokens(extract_section(plan_text, "Files Likely Affected"))
    changed_files = extract_file_tokens(extract_section(code_text, "Files Changed"))
    if not planned_files or not changed_files:
        return []
    return sorted(changed_files - planned_files)


def validate_task_id(task_id: str) -> List[str]:
    return [] if TASK_ID_PATTERN.match(task_id) else [f"Invalid task id '{task_id}'. Expected format like TASK-001."]


def validate_taipei_timestamp(value: str, label: str) -> List[str]:
    return [] if TAIPEI_TIMESTAMP_PATTERN.match(str(value).strip()) else [f"{label} must be Asia/Taipei ISO 8601 with +08:00, got '{value}'"]


def validate_status_schema(status: dict, expected_task_id: str) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    required_keys = {"task_id", "state", "current_owner", "next_agent", "required_artifacts", "available_artifacts", "missing_artifacts", "blocked_reason", "last_updated"}
    missing = required_keys - set(status.keys())
    if missing:
        errors.append(f"status.json missing required keys: {sorted(missing)}")
    if status.get("task_id") != expected_task_id:
        errors.append(f"status.json task_id mismatch. Expected {expected_task_id}, got {status.get('task_id')}")
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
    errors.extend(validate_taipei_timestamp(status.get("last_updated", ""), "status.json last_updated"))
    return ValidationResult(errors, warnings)


def validate_research_artifact(text: str, path: Path) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    if "## Recommendation" in text:
        errors.append(f"{path.name}: research artifact must be fact-only and must not contain ## Recommendation")
    confirmed_items = parse_list_items(extract_section(text, "Confirmed Facts"))
    if not confirmed_items:
        errors.append(f"{path.name}: ## Confirmed Facts must contain at least one concrete claim")
    for item in confirmed_items:
        if "UNVERIFIED:" in item:
            errors.append(f"{path.name}: UNVERIFIED item found in ## Confirmed Facts")
        if not CITATION_PATTERN.search(item):
            errors.append(f"{path.name}: each Confirmed Facts item must include an inline citation")
    for item in parse_list_items(extract_section(text, "Uncertain Items")):
        if not item.startswith("UNVERIFIED:"):
            errors.append(f"{path.name}: each Uncertain Items entry must start with UNVERIFIED:")
    constraints = extract_section(text, "Constraints For Implementation")
    if not constraints or constraints.lower() == "none":
        errors.append(f"{path.name}: ## Constraints For Implementation must not be empty")
    for mixed_entry in detect_mixed_github_sources(text):
        warnings.append(
            f"{path.name}: possible mixed truth source detected for repo '{mixed_entry}' (upstream/fork may be mixed)"
        )
    return ValidationResult(errors, warnings)


def validate_improvement_artifact(text: str, path: Path, task_id: str) -> ValidationResult:
    errors: List[str] = []
    source_match = re.search(r"^- Source Task:\s*(.+)$", text, re.MULTILINE)
    if not source_match or not source_match.group(1).strip():
        errors.append(f"{path.name}: missing non-empty Source Task field")
    elif task_id not in source_match.group(1):
        errors.append(f"{path.name}: Source Task must reference {task_id}")
    trigger_match = re.search(r"^- Trigger Type:\s*(.+)$", text, re.MULTILINE)
    if not trigger_match or trigger_match.group(1).strip() not in {"failure", "blocked", "inefficiency", "guard miss"}:
        errors.append(f"{path.name}: Trigger Type must be one of failure / blocked / inefficiency / guard miss")
    for heading in ("5. Preventive Action (System Level)", "6. Validation", "8. Final Rule", "9. Status"):
        value = extract_section(text, heading)
        if not value or value.lower() == "none":
            errors.append(f"{path.name}: ## {heading} must not be empty")
    return ValidationResult(errors, [])


def validate_markdown_artifact(path: Path, artifact_type: str, task_id: str) -> ValidationResult:
    text = load_text(path)
    errors: List[str] = []
    warnings: List[str] = []
    missing_markers = [marker for marker in MARKERS[artifact_type] if marker not in text]
    if missing_markers:
        errors.append(f"{path.name} missing required markers: {missing_markers}")
    if f"Task ID: {task_id}" not in text:
        errors.append(f"{path.name} missing exact task id marker 'Task ID: {task_id}'")
    owner_match = re.search(r"^- Owner:\s*(.+)$", text, re.MULTILINE)
    if not owner_match or not owner_match.group(1).strip():
        errors.append(f"{path.name} missing non-empty Owner field")
    status_match = re.search(r"^- Status:\s*(.+)$", text, re.MULTILINE)
    if not status_match or not status_match.group(1).strip():
        errors.append(f"{path.name} missing non-empty Status field")
    else:
        status_value = status_match.group(1).strip()
        if status_value not in ARTIFACT_ALLOWED_STATUSES.get(artifact_type, set()):
            errors.append(f"{path.name} has invalid Status '{status_value}' for artifact type '{artifact_type}'")
    updated_match = re.search(r"^- Last Updated:\s*(.+)$", text, re.MULTILINE)
    if not updated_match or not updated_match.group(1).strip():
        errors.append(f"{path.name} missing non-empty Last Updated field")
    else:
        errors.extend(validate_taipei_timestamp(updated_match.group(1).strip(), f"{path.name} Last Updated"))
    if artifact_type == "plan" and not re.search(r"## Ready For Coding\s+\n?\s*(yes|no)\b", text, re.IGNORECASE):
        errors.append(f"{path.name} does not clearly declare Ready For Coding as yes/no")
    if artifact_type == "verify" and not re.search(r"## Pass Fail Result\s+\n?\s*(pass|fail)\b", text, re.IGNORECASE):
        errors.append(f"{path.name} does not clearly declare Pass Fail Result as pass/fail")
    if artifact_type == "research":
        result = validate_research_artifact(text, path)
        errors.extend(result.errors)
        warnings.extend(result.warnings)
    if artifact_type == "improvement":
        result = validate_improvement_artifact(text, path, task_id)
        errors.extend(result.errors)
    return ValidationResult(errors, warnings)


def verify_result_is_pass(verify_path: Path) -> bool:
    match = re.search(r"## Pass Fail Result\s+\n?\s*(pass|fail)\b", load_text(verify_path), re.IGNORECASE)
    return bool(match and match.group(1).lower() == "pass")


def plan_ready_for_coding(plan_path: Path) -> bool:
    match = re.search(r"## Ready For Coding\s+\n?\s*(yes|no)\b", load_text(plan_path), re.IGNORECASE)
    return bool(match and match.group(1).lower() == "yes")


def task_is_high_risk(task_path: Optional[Path], plan_text: str) -> bool:
    task_text = load_text(task_path) if task_path and task_path.exists() else ""
    haystack = f"{task_text}\n{plan_text}".lower()
    return any(keyword in haystack for keyword in HIGH_RISK_KEYWORDS)


def validate_premortem(plan_path: Path, task_path: Optional[Path]) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    text = load_text(plan_path)
    risks_text = extract_section(text, "Risks")
    if not risks_text:
        errors.append(f"{plan_path.name}: premortem check failed — ## Risks section not found")
        return ValidationResult(errors, warnings)
    if risks_text.lower() in ("none", "n/a", "low risk", ""):
        errors.append(f"{plan_path.name}: premortem check failed — ## Risks section is empty or trivially dismissed")
        return ValidationResult(errors, warnings)
    risk_count = len(set(re.findall(r"\bR(\d+)\b", risks_text)))
    min_risks = PREMORTEM_MIN_RISKS_HIGH if task_is_high_risk(task_path, text) else PREMORTEM_MIN_RISKS_DEFAULT
    if risk_count < min_risks:
        errors.append(f"{plan_path.name}: premortem requires at least {min_risks} numbered risks (R1, R2, ...), found {risk_count}")
    for field in PREMORTEM_REQUIRED_FIELDS:
        if field not in risks_text:
            errors.append(f"{plan_path.name}: premortem missing required field '{field}'")
    severity_values = re.findall(r"Severity:\s*(.+)", risks_text)
    for severity in severity_values:
        if severity.strip().lower() not in ("blocking", "non-blocking"):
            errors.append(f"{plan_path.name}: premortem Severity must be 'blocking' or 'non-blocking', got '{severity.strip()}'")
    has_blocking = any(value.strip().lower() == "blocking" for value in severity_values)
    if task_is_high_risk(task_path, text):
        if not has_blocking:
            errors.append(f"{plan_path.name}: high-risk premortem must include at least one blocking risk")
    elif not has_blocking and risk_count > 0:
        warnings.append(f"{plan_path.name}: premortem has no blocking risk — review whether this is appropriate")
    for phrase in PREMORTEM_BANNED_PHRASES:
        if phrase in risks_text:
            warnings.append(f"{plan_path.name}: premortem contains potentially vague phrase '{phrase}' — ensure it has concrete trigger/detection/mitigation")
    return ValidationResult(errors, warnings)


def compute_existing_artifacts(artifacts_root: Path, task_id: str) -> Set[str]:
    return {artifact_type for artifact_type in ARTIFACT_DIRS if find_artifact_paths(artifacts_root, task_id, artifact_type)}


def state_required_artifacts(state: str, existing: Set[str]) -> Set[str]:
    required = set(STATE_REQUIRED_ARTIFACTS[state])
    if state in {"planned", "coding", "testing", "verifying", "done"} and "research" in existing:
        required.add("research")
    if state in {"verifying", "done"} and "test" in existing:
        required.add("test")
    return required


def validate_artifact_presence(artifacts_root: Path, task_id: str, state: str, status: dict, strict_scope: bool = False) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    existing = compute_existing_artifacts(artifacts_root, task_id)
    required = state_required_artifacts(state, existing)
    missing_required = sorted(required - existing)
    if missing_required:
        errors.append(f"Missing required artifacts for state '{state}': {missing_required}")
    status_available = set(status.get("available_artifacts", []))
    status_missing = set(status.get("missing_artifacts", []))
    status_required = set(status.get("required_artifacts", []))
    if status_available != existing:
        warnings.append(f"available_artifacts mismatch. status.json={sorted(status_available)} actual={sorted(existing)}")
    if status_required != required:
        warnings.append(f"required_artifacts mismatch. status.json={sorted(status_required)} computed={sorted(required)}")
    computed_missing = required - existing
    if status_missing != computed_missing:
        warnings.append(f"missing_artifacts mismatch. status.json={sorted(status_missing)} computed={sorted(computed_missing)}")
    for artifact_type in sorted(existing - {'status'}):
        for path in find_artifact_paths(artifacts_root, task_id, artifact_type):
            result = validate_markdown_artifact(path, artifact_type, task_id)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
    if state in {"coding", "testing", "verifying", "done"}:
        plan_path = artifact_path(artifacts_root, task_id, "plan")
        task_path = artifact_path(artifacts_root, task_id, "task")
        if plan_path.exists() and not plan_ready_for_coding(plan_path):
            errors.append(f"Plan artifact is not Ready For Coding = yes: {plan_path.name}")
        if plan_path.exists():
            premortem_result = validate_premortem(plan_path, task_path if task_path.exists() else None)
            if state == "coding":
                errors.extend(premortem_result.errors)
            else:
                warnings.extend(premortem_result.errors)
            warnings.extend(premortem_result.warnings)
        code_path = artifact_path(artifacts_root, task_id, "code")
        if plan_path.exists() and code_path.exists():
            drift_files = detect_plan_code_scope_drift(load_text(plan_path), load_text(code_path))
            if drift_files:
                scope_message = (
                    f"{code_path.name}: files changed not listed in {plan_path.name} "
                    f"## Files Likely Affected: {drift_files}"
                )
                if strict_scope:
                    errors.append(scope_message)
                else:
                    warnings.append(scope_message)
    if state == "done":
        verify_path = artifact_path(artifacts_root, task_id, "verify")
        if verify_path.exists() and not verify_result_is_pass(verify_path):
            errors.append("done state requires verify artifact with Pass Fail Result = pass")
    return ValidationResult(errors, warnings)


def validate_transition(from_state: str, to_state: str, artifacts_root: Optional[Path] = None, task_id: Optional[str] = None) -> ValidationResult:
    errors: List[str] = []
    warnings: List[str] = []
    if from_state not in VALID_STATES:
        return ValidationResult([f"Unknown from_state: {from_state}"], warnings)
    if to_state not in VALID_STATES:
        return ValidationResult([f"Unknown to_state: {to_state}"], warnings)
    if to_state not in LEGAL_TRANSITIONS.get(from_state, set()):
        errors.append(f"Illegal state transition: {from_state} -> {to_state}")
    if from_state == "blocked" and to_state != "blocked" and artifacts_root and task_id:
        improvement_paths = find_artifact_paths(artifacts_root, task_id, "improvement")
        if not improvement_paths:
            errors.append(f"Gate E (PDCA): resuming from blocked requires an improvement artifact for {task_id} in artifacts/improvement/")
            return ValidationResult(errors, warnings)
        applied_found = False
        for path in improvement_paths:
            result = validate_markdown_artifact(path, "improvement", task_id)
            errors.extend(result.errors)
            warnings.extend(result.warnings)
            status_match = re.search(r"^- Status:\s*(.+)$", load_text(path), re.MULTILINE)
            if status_match and status_match.group(1).strip() == "applied":
                applied_found = True
        if not applied_found:
            errors.append(f"Gate E (PDCA): resuming from blocked requires an improvement artifact with Status: applied for {task_id}")
    return ValidationResult(errors, warnings)


def validate_all(artifacts_root: Path, task_id: str, strict_scope: bool = False) -> ValidationResult:
    errors: List[str] = validate_task_id(task_id)
    warnings: List[str] = []
    if errors:
        return ValidationResult(errors, warnings)
    status = load_json(artifact_path(artifacts_root, task_id, "status"))
    schema_result = validate_status_schema(status, task_id)
    errors.extend(schema_result.errors)
    warnings.extend(schema_result.warnings)
    state = status.get("state")
    if state in VALID_STATES:
        presence_result = validate_artifact_presence(artifacts_root, task_id, state, status, strict_scope=strict_scope)
        errors.extend(presence_result.errors)
        warnings.extend(presence_result.warnings)
    return ValidationResult(errors, warnings)


def write_transition(artifacts_root: Path, task_id: str, from_state: str, to_state: str, strict_scope: bool = False) -> ValidationResult:
    transition_result = validate_transition(from_state, to_state, artifacts_root, task_id)
    if transition_result.errors:
        return transition_result
    full_result = validate_all(artifacts_root, task_id, strict_scope=strict_scope)
    if full_result.errors:
        return full_result
    status_path = artifact_path(artifacts_root, task_id, "status")
    status = load_json(status_path)
    if status.get("state") != from_state:
        return ValidationResult([f"Refusing transition because status.json state is {status.get('state')}, not expected {from_state}"], [])
    target_presence = validate_artifact_presence(artifacts_root, task_id, to_state, status, strict_scope=strict_scope)
    if target_presence.errors:
        return ValidationResult([f"Target state '{to_state}' requirements are not yet satisfied.", *target_presence.errors], target_presence.warnings)
    existing = compute_existing_artifacts(artifacts_root, task_id)
    required = state_required_artifacts(to_state, existing)
    status["state"] = to_state
    status["required_artifacts"] = sorted(required)
    status["available_artifacts"] = sorted(existing)
    status["missing_artifacts"] = sorted(required - existing)
    if to_state != "blocked":
        status["blocked_reason"] = ""
    status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return ValidationResult([], transition_result.warnings + full_result.warnings + target_presence.warnings)


def print_result(result: ValidationResult) -> None:
    print("[OK] Validation passed" if result.ok else "[ERROR] Validation failed")
    for warning in result.warnings:
        print(f"[WARN] {warning}")
    for error in result.errors:
        print(f"[FAIL] {error}")


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate artifact workflow status and transitions.")
    parser.add_argument("--task-id", required=True, help="Task id, for example TASK-001")
    parser.add_argument("--artifacts-root", default="./artifacts", help="Artifacts root directory. Default: ./artifacts")
    parser.add_argument("--from-state", help="Validate a proposed transition from this state")
    parser.add_argument("--to-state", help="Validate a proposed transition to this state")
    parser.add_argument("--write-transition", nargs=2, metavar=("FROM_STATE", "TO_STATE"), help="Validate and write the transition into status.json if allowed")
    parser.add_argument(
        "--allow-scope-drift",
        action="store_true",
        help="Allow plan/code scope drift as warning only. Default behavior treats drift as failure.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    artifacts_root = Path(args.artifacts_root).resolve()
    strict_scope = not args.allow_scope_drift
    try:
        if args.write_transition:
            result = write_transition(
                artifacts_root,
                args.task_id,
                args.write_transition[0],
                args.write_transition[1],
                strict_scope=strict_scope,
            )
            print_result(result)
            return 0 if result.ok else 1
        if bool(args.from_state) != bool(args.to_state):
            print("[FAIL] --from-state and --to-state must be used together", file=sys.stderr)
            return 2
        result = validate_all(artifacts_root, args.task_id, strict_scope=strict_scope)
        if args.from_state and args.to_state:
            transition_result = validate_transition(args.from_state, args.to_state, artifacts_root, args.task_id)
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
