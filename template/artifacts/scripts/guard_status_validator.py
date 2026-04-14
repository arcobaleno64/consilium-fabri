#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Set, Tuple

__version__ = "0.7.0"

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
COMMIT_SHA_PATTERN = re.compile(r"^[0-9a-f]{40}$", re.IGNORECASE)
PREMORTEM_MIN_RISKS_DEFAULT = 2
PREMORTEM_MIN_RISKS_HIGH = 4
PREMORTEM_REQUIRED_FIELDS = ("Risk:", "Trigger:", "Detection:", "Mitigation:", "Severity:")
PREMORTEM_BANNED_PHRASES = ("風險低", "應該沒問題", "可能有風險", "視情況而定", "再觀察", "注意一下", "需評估", "有待確認")
HIGH_RISK_KEYWORDS = ("security", "安全", "dependency", "依賴", "upstream pr", "upstream", "cross-repo", "cross repo", "跨 repo")
IGNORED_GIT_SCOPE_PATHS = {"obsidian/workspace.json", ".obsidian/workspace.json"}
DIFF_EVIDENCE_SUPPORTED_TYPES = {"commit-range", "github-pr"}
SCOPE_WAIVER_EXCEPTION_TYPE = "allow-scope-drift"
GITHUB_API_VERSION = "2022-11-28"
MAX_GITHUB_PR_FILES_PAGES = 30


@dataclass
class ValidationResult:
    errors: List[str]
    warnings: List[str]

    @property
    def ok(self) -> bool:
        return not self.errors


@dataclass
class ScopeCheckResult:
    errors: List[str]
    waiver_candidate_errors: List[str]
    warnings: List[str]
    drift_files: Set[str]


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


def parse_key_value_section(section_text: str) -> Dict[str, str]:
    values: Dict[str, str] = {}
    for raw_line in section_text.splitlines():
        match = re.match(r"^-\s*([^:]+):\s*(.*)$", raw_line.strip())
        if match:
            values[match.group(1).strip().lower()] = match.group(2).strip()
    return values


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


def parse_csv_file_tokens(value: str) -> Set[str]:
    if not value or value.strip().lower() == "none":
        return set()
    tokens: Set[str] = set()
    for part in value.split(","):
        normalized = normalize_path_token(part)
        if normalized:
            tokens.add(normalized)
    return tokens


def compute_snapshot_sha256(paths: Set[str]) -> str:
    payload = "\n".join(sorted(paths))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def resolve_workspace_relative_path(repo_root: Path, raw_path: str) -> Tuple[Optional[str], Optional[Path], Optional[str]]:
    normalized = normalize_path_token(raw_path)
    if not normalized:
        return None, None, "path is empty"
    if normalized.startswith("/") or normalized == ".." or normalized.startswith("../") or "/../" in normalized:
        return None, None, "path must stay within repository root"
    candidate = repo_root / normalized
    try:
        resolved_root = repo_root.resolve()
        resolved_candidate = candidate.resolve()
    except OSError as exc:
        return None, None, str(exc)
    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return None, None, "path escapes repository root"
    return normalized, resolved_candidate, None


def parse_repository_ref(value: str) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    parts = [part.strip() for part in value.split("/")]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None, None, "Repository must use owner/repo format"
    if parts[0] in {".", ".."} or parts[1] in {".", ".."}:
        return None, None, "Repository owner/repo segments must be concrete names"
    return parts[0], parts[1], None


def normalize_api_base_url(raw_value: str) -> Tuple[Optional[str], Optional[str]]:
    value = raw_value.strip() or "https://api.github.com"
    value = value.rstrip("/")
    parsed = urllib.parse.urlparse(value)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        return None, "API Base URL must be an absolute http(s) URL"
    return value, None


def summarize_remote_error_detail(raw_body: bytes, fallback: str) -> str:
    if raw_body:
        text = raw_body.decode("utf-8", errors="replace").strip()
        if text:
            return text[:200] + ("..." if len(text) > 200 else "")
    return fallback


def load_archive_snapshot(repo_root: Path, code_path: Path, evidence: Dict[str, str], snapshot_files: Set[str]) -> Tuple[Optional[Set[str]], Optional[str], Optional[str]]:
    raw_archive_path = evidence.get("archive path", "").strip()
    archive_sha256 = evidence.get("archive sha256", "").strip().lower()
    if bool(raw_archive_path) != bool(archive_sha256):
        return None, None, f"{code_path.name}: commit-range ## Diff Evidence requires Archive Path and Archive SHA256 together"
    if not raw_archive_path:
        return None, None, None
    if not re.fullmatch(r"[0-9a-f]{64}", archive_sha256):
        return None, None, f"{code_path.name}: Archive SHA256 must be a 64-character hexadecimal string"
    archive_rel, archive_path, path_error = resolve_workspace_relative_path(repo_root, raw_archive_path)
    if path_error or archive_rel is None or archive_path is None:
        return None, None, f"{code_path.name}: invalid Archive Path '{raw_archive_path}': {path_error}"
    try:
        archive_bytes = archive_path.read_bytes()
    except FileNotFoundError:
        return None, None, f"{code_path.name}: Archive Path '{archive_rel}' does not exist"
    except OSError as exc:
        return None, None, f"{code_path.name}: unable to read Archive Path '{archive_rel}': {exc}"
    actual_archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
    if actual_archive_sha256 != archive_sha256:
        return None, None, (
            f"{code_path.name}: Archive SHA256 does not match archive file {archive_rel}. "
            f"expected={actual_archive_sha256} actual={archive_sha256}"
        )
    try:
        archive_text = archive_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        return None, None, f"{code_path.name}: Archive Path '{archive_rel}' must be UTF-8 text: {exc}"
    archive_lines = archive_text.splitlines()
    if not archive_lines:
        return None, None, f"{code_path.name}: Archive Path '{archive_rel}' must contain at least one normalized file path"
    normalized_lines: List[str] = []
    seen: Set[str] = set()
    for index, raw_line in enumerate(archive_lines, start=1):
        if not raw_line.strip():
            return None, None, f"{code_path.name}: Archive Path '{archive_rel}' contains a blank line at line {index}"
        normalized = normalize_path_token(raw_line)
        if not normalized or normalized == ".." or normalized.startswith("../") or "/../" in normalized:
            return None, None, f"{code_path.name}: Archive Path '{archive_rel}' contains an invalid path at line {index}: {raw_line!r}"
        if normalized in seen:
            return None, None, f"{code_path.name}: Archive Path '{archive_rel}' contains a duplicate path at line {index}: {normalized}"
        seen.add(normalized)
        normalized_lines.append(normalized)
    if normalized_lines != sorted(normalized_lines):
        return None, None, f"{code_path.name}: Archive Path '{archive_rel}' must contain sorted normalized file paths"
    archive_files = set(normalized_lines)
    if archive_files != snapshot_files:
        return None, None, (
            f"{code_path.name}: Archive file {archive_rel} does not match Changed Files Snapshot. "
            f"snapshot={sorted(snapshot_files)} archive={sorted(archive_files)}"
        )
    return archive_files, archive_rel, None


def collect_github_pr_files(repository: str, pull_number: str, api_base_url: str) -> Tuple[Set[str], Optional[str]]:
    owner, repo, repo_error = parse_repository_ref(repository)
    if repo_error or owner is None or repo is None:
        return set(), repo_error
    if not pull_number.isdigit() or int(pull_number) <= 0:
        return set(), "PR Number must be a positive integer"
    base_url, base_error = normalize_api_base_url(api_base_url)
    if base_error or base_url is None:
        return set(), base_error
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": f"antigravity-guard-status-validator/{__version__}",
        "X-GitHub-Api-Version": GITHUB_API_VERSION,
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"
    changed_files: Set[str] = set()
    for page in range(1, MAX_GITHUB_PR_FILES_PAGES + 2):
        url = (
            f"{base_url}/repos/{urllib.parse.quote(owner, safe='')}/{urllib.parse.quote(repo, safe='')}"
            f"/pulls/{pull_number}/files?per_page=100&page={page}"
        )
        request = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                response_body = response.read()
        except urllib.error.HTTPError as exc:
            detail = summarize_remote_error_detail(exc.read(), exc.reason or "HTTP error")
            auth_hint = " Set GITHUB_TOKEN or GH_TOKEN when accessing private or rate-limited repositories." if exc.code in {401, 403, 404} and not token else ""
            return set(), f"HTTP {exc.code} from {url}: {detail}{auth_hint}"
        except urllib.error.URLError as exc:
            return set(), f"connection error while fetching {url}: {exc.reason}"
        try:
            payload = json.loads(response_body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            return set(), f"invalid JSON response from {url}: {exc}"
        if not isinstance(payload, list):
            return set(), f"unexpected non-list response from {url}"
        if page > MAX_GITHUB_PR_FILES_PAGES and payload:
            return set(), f"provider response exceeds GitHub PR files endpoint cap of {MAX_GITHUB_PR_FILES_PAGES * 100} files"
        if not payload:
            break
        for item in payload:
            if not isinstance(item, dict):
                return set(), f"provider response from {url} contains a non-object file entry"
            filename = item.get("filename")
            if not isinstance(filename, str) or not filename.strip():
                return set(), f"provider response from {url} contains a file entry without filename"
            normalized = normalize_path_token(filename)
            if not normalized:
                return set(), f"provider response from {url} contains an invalid filename {filename!r}"
            changed_files.add(normalized)
        if len(payload) < 100:
            break
    return changed_files, None


def compare_reconstructed_scope(plan_path: Path, code_path: Path, changed_files: Set[str], scope_label: str) -> ScopeCheckResult:
    errors: List[str] = []
    waiver_candidate_errors: List[str] = []
    warnings: List[str] = []
    drift_files: Set[str] = set()
    plan_text = load_text(plan_path)
    code_text = load_text(code_path)
    planned_files = extract_file_tokens(extract_section(plan_text, "Files Likely Affected"))
    declared_changed = extract_file_tokens(extract_section(code_text, "Files Changed"))
    undeclared_actual = sorted(changed_files - declared_changed)
    if undeclared_actual:
        waiver_candidate_errors.append(
            f"{code_path.name}: {scope_label} found diff files not listed in ## Files Changed: {undeclared_actual}"
        )
        drift_files.update(undeclared_actual)
    unplanned_actual = sorted(changed_files - planned_files)
    if unplanned_actual:
        waiver_candidate_errors.append(
            f"{plan_path.name}: {scope_label} found diff files not listed in ## Files Likely Affected: {unplanned_actual}"
        )
        drift_files.update(unplanned_actual)
    return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)


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


def parse_diff_evidence(code_text: str) -> Optional[Dict[str, str]]:
    section = extract_section(code_text, "Diff Evidence")
    if not section or section.strip().lower() == "none":
        return None
    return parse_key_value_section(section)


def detect_git_root(start: Path) -> Optional[Path]:
    resolved = start.resolve()
    for candidate in [resolved, *resolved.parents]:
        if (candidate / ".git").exists():
            return candidate
    return None


def load_git_scope_context(artifacts_root: Path, task_id: str) -> Tuple[Optional[Path], Set[str], Set[str], List[str]]:
    repo_root = detect_git_root(artifacts_root)
    if not repo_root:
        return None, set(), set(), []
    actual_changed, warnings = collect_git_changed_files(repo_root)
    task_artifacts = task_artifact_relative_paths(artifacts_root, task_id, repo_root)
    return repo_root, actual_changed, task_artifacts, warnings


def collect_git_changed_files(repo_root: Path) -> Tuple[Set[str], List[str]]:
    warnings: List[str] = []
    changed: Set[str] = set()
    commands = [
        ["git", "-C", str(repo_root), "diff", "--name-only", "--cached"],
        ["git", "-C", str(repo_root), "diff", "--name-only"],
        ["git", "-C", str(repo_root), "ls-files", "--others", "--exclude-standard"],
    ]
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
        except FileNotFoundError:
            return set(), ["git-backed scope check skipped: git command not available"]
        if result.returncode != 0:
            detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
            warnings.append(f"git-backed scope check skipped in {repo_root}: {' '.join(command[3:])} failed: {detail}")
            return set(), warnings
        for raw_line in result.stdout.splitlines():
            normalized = normalize_path_token(raw_line)
            if normalized and normalized not in IGNORED_GIT_SCOPE_PATHS and not (repo_root / normalized).is_dir():
                changed.add(normalized)
    return changed, warnings


def collect_git_diff_range_files(repo_root: Path, base_ref: str, head_ref: str) -> Tuple[Set[str], Optional[str]]:
    command = ["git", "-C", str(repo_root), "diff", "--name-only", f"{base_ref}..{head_ref}"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        return set(), "git command not available"
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        return set(), detail
    changed: Set[str] = set()
    for raw_line in result.stdout.splitlines():
        normalized = normalize_path_token(raw_line)
        if normalized and normalized not in IGNORED_GIT_SCOPE_PATHS and not (repo_root / normalized).is_dir():
            changed.add(normalized)
    return changed, None


def resolve_git_revision_commit(repo_root: Path, revision: str) -> Tuple[Optional[str], Optional[str]]:
    command = ["git", "-C", str(repo_root), "rev-parse", f"{revision}^{{commit}}"]
    try:
        result = subprocess.run(command, capture_output=True, text=True, encoding="utf-8")
    except FileNotFoundError:
        return None, "git command not available"
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip() or "unknown git error"
        return None, detail
    return result.stdout.strip().splitlines()[0], None


def task_artifact_relative_paths(artifacts_root: Path, task_id: str, repo_root: Path) -> Set[str]:
    paths: Set[str] = set()
    for artifact_type in ARTIFACT_DIRS:
        for path in find_artifact_paths(artifacts_root, task_id, artifact_type):
            try:
                relative = path.relative_to(repo_root)
            except ValueError:
                continue
            paths.add(normalize_path_token(str(relative)))
    return paths


def detect_git_backed_scope_drift(plan_path: Path, code_path: Path, actual_changed: Set[str], task_artifacts: Set[str]) -> ScopeCheckResult:
    errors: List[str] = []
    waiver_candidate_errors: List[str] = []
    warnings: List[str] = []
    drift_files: Set[str] = set()
    if not actual_changed or not task_artifacts.intersection(actual_changed):
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    plan_text = load_text(plan_path)
    code_text = load_text(code_path)
    planned_files = extract_file_tokens(extract_section(plan_text, "Files Likely Affected"))
    declared_changed = extract_file_tokens(extract_section(code_text, "Files Changed"))
    actual_scope_changed = {
        path
        for path in (actual_changed - task_artifacts)
        if not path.startswith("artifacts/") or path in declared_changed or path in planned_files
    }
    if not actual_scope_changed:
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    undeclared_actual = sorted(actual_scope_changed - declared_changed)
    if undeclared_actual:
        waiver_candidate_errors.append(
            f"{code_path.name}: git-backed scope check found actual changed files not listed in ## Files Changed: {undeclared_actual}"
        )
        drift_files.update(undeclared_actual)
    unplanned_actual = sorted(actual_scope_changed - planned_files)
    if unplanned_actual:
        waiver_candidate_errors.append(
            f"{plan_path.name}: git-backed scope check found actual changed files not listed in ## Files Likely Affected: {unplanned_actual}"
        )
        drift_files.update(unplanned_actual)
    return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)


def detect_historical_diff_scope_drift(repo_root: Optional[Path], plan_path: Path, code_path: Path) -> ScopeCheckResult:
    errors: List[str] = []
    waiver_candidate_errors: List[str] = []
    warnings: List[str] = []
    drift_files: Set[str] = set()
    code_text = load_text(code_path)
    evidence = parse_diff_evidence(code_text)
    if not evidence:
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    evidence_type = evidence.get("evidence type", "").strip().lower()
    if evidence_type not in DIFF_EVIDENCE_SUPPORTED_TYPES:
        errors.append(
            f"{code_path.name}: unsupported ## Diff Evidence type '{evidence_type or '<missing>'}'. Supported types: {sorted(DIFF_EVIDENCE_SUPPORTED_TYPES)}"
        )
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    snapshot_files = parse_csv_file_tokens(evidence.get("changed files snapshot", ""))
    snapshot_sha256 = evidence.get("snapshot sha256", "").strip().lower()
    if not snapshot_files or not snapshot_sha256:
        requirement = "Repository, PR Number, Changed Files Snapshot, and Snapshot SHA256" if evidence_type == "github-pr" else "Base Commit, Head Commit, Diff Command, Changed Files Snapshot, and Snapshot SHA256"
        errors.append(f"{code_path.name}: {evidence_type} ## Diff Evidence requires non-empty {requirement}")
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    expected_snapshot_hash = compute_snapshot_sha256(snapshot_files)
    if snapshot_sha256 != expected_snapshot_hash:
        errors.append(
            f"{code_path.name}: Snapshot SHA256 does not match Changed Files Snapshot. expected={expected_snapshot_hash} actual={snapshot_sha256 or '<missing>'}"
        )
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    if evidence_type == "github-pr":
        repository = evidence.get("repository", "").strip()
        pull_number = evidence.get("pr number", "").strip()
        api_base_url = evidence.get("api base url", "").strip()
        if not repository or not pull_number:
            errors.append(f"{code_path.name}: github-pr ## Diff Evidence requires non-empty Repository, PR Number, Changed Files Snapshot, and Snapshot SHA256")
            return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
        provider_files, provider_error = collect_github_pr_files(repository, pull_number, api_base_url)
        if provider_error:
            errors.append(f"{code_path.name}: github-pr evidence fetch failed for {repository} PR#{pull_number}: {provider_error}")
            return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
        if provider_files != snapshot_files:
            errors.append(
                f"{code_path.name}: Changed Files Snapshot does not match github-pr provider response. snapshot={sorted(snapshot_files)} provider={sorted(provider_files)}"
            )
            return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
        return compare_reconstructed_scope(plan_path, code_path, provider_files, "github-pr scope check")

    if not repo_root:
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    base_ref = evidence.get("base ref", "").strip()
    head_ref = evidence.get("head ref", "").strip()
    base_commit = evidence.get("base commit", "").strip()
    head_commit = evidence.get("head commit", "").strip()
    diff_command = evidence.get("diff command", "").strip()
    if not base_commit or not head_commit or not diff_command:
        errors.append(
            f"{code_path.name}: commit-range ## Diff Evidence requires non-empty Base Commit, Head Commit, Diff Command, Changed Files Snapshot, and Snapshot SHA256"
        )
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    if not COMMIT_SHA_PATTERN.match(base_commit) or not COMMIT_SHA_PATTERN.match(head_commit):
        errors.append(f"{code_path.name}: Base Commit and Head Commit must be full 40-character git commit SHAs")
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    archive_files, archive_rel, archive_error = load_archive_snapshot(repo_root, code_path, evidence, snapshot_files)
    if archive_error:
        errors.append(archive_error)
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    if base_ref:
        resolved_base, base_error = resolve_git_revision_commit(repo_root, base_ref)
        if base_error:
            warnings.append(f"{code_path.name}: Base Ref '{base_ref}' no longer resolves to a commit: {base_error}")
        elif resolved_base.lower() != base_commit.lower():
            warnings.append(
                f"{code_path.name}: Base Ref '{base_ref}' resolves to {resolved_base}, not pinned Base Commit {base_commit}"
            )
    if head_ref:
        resolved_head, head_error = resolve_git_revision_commit(repo_root, head_ref)
        if head_error:
            warnings.append(f"{code_path.name}: Head Ref '{head_ref}' no longer resolves to a commit: {head_error}")
        elif resolved_head.lower() != head_commit.lower():
            warnings.append(
                f"{code_path.name}: Head Ref '{head_ref}' resolves to {resolved_head}, not pinned Head Commit {head_commit}"
            )
    diff_changed, diff_error = collect_git_diff_range_files(repo_root, base_commit, head_commit)
    scope_label = "commit-range scope check"
    if diff_error:
        if archive_files is None or archive_rel is None:
            errors.append(f"{code_path.name}: commit-range diff replay failed for {base_commit}..{head_commit}: {diff_error}")
            return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
        warnings.append(
            f"{code_path.name}: commit-range diff replay failed for {base_commit}..{head_commit}; using archive fallback {archive_rel}: {diff_error}"
        )
        diff_changed = archive_files
        scope_label = "commit-range archive fallback"
    if diff_changed != snapshot_files:
        mismatch_source = f"archive fallback {archive_rel}" if scope_label == "commit-range archive fallback" and archive_rel else "replayed commit-range diff"
        errors.append(
            f"{code_path.name}: Changed Files Snapshot does not match {mismatch_source}. snapshot={sorted(snapshot_files)} replay={sorted(diff_changed)}"
        )
        return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)
    scope_result = compare_reconstructed_scope(plan_path, code_path, diff_changed, scope_label)
    warnings.extend(scope_result.warnings)
    waiver_candidate_errors.extend(scope_result.waiver_candidate_errors)
    drift_files.update(scope_result.drift_files)
    return ScopeCheckResult(errors, waiver_candidate_errors, warnings, drift_files)


def validate_scope_drift_waiver(artifacts_root: Path, task_id: str, drift_files: Set[str]) -> ValidationResult:
    if not drift_files:
        return ValidationResult([], [])
    decision_paths = find_artifact_paths(artifacts_root, task_id, "decision")
    if not decision_paths:
        return ValidationResult(
            [
                f"--allow-scope-drift requires a decision artifact with ## Guard Exception covering drift files: {sorted(drift_files)}"
            ],
            [],
        )
    for path in decision_paths:
        section = extract_section(load_text(path), "Guard Exception")
        if not section:
            continue
        fields = parse_key_value_section(section)
        if fields.get("exception type", "").strip().lower() != SCOPE_WAIVER_EXCEPTION_TYPE:
            continue
        waived_files = parse_csv_file_tokens(fields.get("scope files", ""))
        justification = fields.get("justification", "").strip()
        if justification and drift_files.issubset(waived_files):
            return ValidationResult([], [f"{path.name}: explicit allow-scope-drift waiver applied for {sorted(drift_files)}"])
    return ValidationResult(
        [
            f"--allow-scope-drift requires a decision artifact with ## Guard Exception / Exception Type: allow-scope-drift / Scope Files covering drift files: {sorted(drift_files)}"
        ],
        [],
    )


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
            scope_drift_files: Set[str] = set()
            drift_files = detect_plan_code_scope_drift(load_text(plan_path), load_text(code_path))
            if drift_files:
                scope_drift_files.update(drift_files)
                scope_message = (
                    f"{code_path.name}: files changed not listed in {plan_path.name} "
                    f"## Files Likely Affected: {drift_files}"
                )
                if strict_scope:
                    errors.append(scope_message)
                else:
                    warnings.append(scope_message)
            repo_root, actual_changed, task_artifacts, git_context_warnings = load_git_scope_context(artifacts_root, task_id)
            warnings.extend(git_context_warnings)
            if task_artifacts.intersection(actual_changed):
                git_scope_result = detect_git_backed_scope_drift(plan_path, code_path, actual_changed, task_artifacts)
                scope_drift_files.update(git_scope_result.drift_files)
                errors.extend(git_scope_result.errors)
                if strict_scope:
                    errors.extend(git_scope_result.waiver_candidate_errors)
                else:
                    warnings.extend(git_scope_result.waiver_candidate_errors)
                warnings.extend(git_scope_result.warnings)
            else:
                history_scope_result = detect_historical_diff_scope_drift(repo_root, plan_path, code_path)
                scope_drift_files.update(history_scope_result.drift_files)
                errors.extend(history_scope_result.errors)
                if strict_scope:
                    errors.extend(history_scope_result.waiver_candidate_errors)
                else:
                    warnings.extend(history_scope_result.waiver_candidate_errors)
                warnings.extend(history_scope_result.warnings)
            if not strict_scope and scope_drift_files:
                waiver_result = validate_scope_drift_waiver(artifacts_root, task_id, scope_drift_files)
                errors.extend(waiver_result.errors)
                warnings.extend(waiver_result.warnings)
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
        "--strict-scope",
        action="store_true",
        help="Legacy compatibility flag. Scope checks are strict by default unless --allow-scope-drift is provided.",
    )
    parser.add_argument(
        "--allow-scope-drift",
        action="store_true",
        help="Allow plan/code scope drift, including git-backed or historical diff evidence checks, as warning only when an explicit decision waiver exists. Default behavior treats drift as failure.",
    )
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    artifacts_root = Path(args.artifacts_root).resolve()
    if args.strict_scope and args.allow_scope_drift:
        print("[FAIL] --strict-scope and --allow-scope-drift cannot be used together", file=sys.stderr)
        return 2
    strict_scope = args.strict_scope or not args.allow_scope_drift
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
