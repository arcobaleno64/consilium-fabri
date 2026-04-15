#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import re
import shutil
import subprocess
import sys
import threading
import urllib.parse
from contextlib import contextmanager
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Optional, Sequence

SCRIPT_PATH = Path(__file__).resolve()


def detect_repo_root() -> Path:
    matches = [
        parent
        for parent in SCRIPT_PATH.parents
        if (parent / "docs" / "red_team_runbook.md").exists()
        and (parent / "artifacts" / "scripts" / "guard_contract_validator.py").exists()
        and (parent / "template").exists()
    ]
    if not matches:
        raise RuntimeError(f"Unable to detect repository root from {SCRIPT_PATH}")
    return matches[-1]


REPO_ROOT = detect_repo_root()
STATUS_GUARD = REPO_ROOT / "artifacts" / "scripts" / "guard_status_validator.py"
CONTRACT_GUARD = REPO_ROOT / "artifacts" / "scripts" / "guard_contract_validator.py"
PROMPT_REGRESSION = REPO_ROOT / "artifacts" / "scripts" / "prompt_regression_validator.py"
LOCAL_TMP_ROOT = REPO_ROOT / ".tmp-red-team" / SCRIPT_PATH.parents[2].name


@dataclass
class CaseResult:
    case_id: str
    phase: str
    title: str
    expected: str
    passed: bool
    exit_code: int
    evidence: str
    notes: str


@dataclass
class CaseDefinition:
    case_id: str
    phase: str
    title: str
    expected: str
    runner: Callable[[], CaseResult]


def load_module(path: Path, module_name: str):
    spec = importlib.util.spec_from_file_location(module_name, path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load module from {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_command(args: Sequence[str], cwd: Optional[Path] = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=cwd or REPO_ROOT, capture_output=True, text=True, encoding="utf-8")


def ensure_command_ok(result: subprocess.CompletedProcess[str], description: str) -> None:
    if result.returncode == 0:
        return
    detail = result.stderr.strip() or result.stdout.strip() or "unknown command failure"
    raise RuntimeError(f"{description} failed: {detail}")


def initialize_git_fixture(repo_root: Path) -> None:
    ensure_command_ok(run_command(["git", "init", "-q"], cwd=repo_root), "git init")
    ensure_command_ok(run_command(["git", "config", "user.email", "red-team@example.invalid"], cwd=repo_root), "git config user.email")
    ensure_command_ok(run_command(["git", "config", "user.name", "Red Team Fixture"], cwd=repo_root), "git config user.name")
    ensure_command_ok(run_command(["git", "add", "."], cwd=repo_root), "git add baseline")
    ensure_command_ok(run_command(["git", "commit", "-q", "-m", "baseline"], cwd=repo_root), "git commit baseline")


def git_rev_parse(repo_root: Path, revision: str) -> str:
    result = run_command(["git", "rev-parse", f"{revision}^{{commit}}"], cwd=repo_root)
    ensure_command_ok(result, f"git rev-parse {revision}")
    return result.stdout.strip().splitlines()[0]


def compute_snapshot_sha256(paths: Sequence[str]) -> str:
    payload = "\n".join(sorted(paths))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@contextmanager
def github_pr_files_server(repository: str, pull_number: int, pages: Dict[int, List[dict]]):
    owner, repo = repository.split("/", 1)
    expected_path = f"/repos/{owner}/{repo}/pulls/{pull_number}/files"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urllib.parse.urlparse(self.path)
            if parsed.path != expected_path:
                body = b'{"message": "not found"}'
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            query = urllib.parse.parse_qs(parsed.query)
            try:
                page = int(query.get("page", ["1"])[0])
            except ValueError:
                page = 1
            body = json.dumps(pages.get(page, [])).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, format: str, *args: object) -> None:
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def replace_task_id(text: str, source_task_id: str, target_task_id: str) -> str:
    return text.replace(source_task_id, target_task_id)


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def prepare_temp_root(case_id: str) -> Path:
    LOCAL_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    case_root = LOCAL_TMP_ROOT / case_id
    shutil.rmtree(case_root, ignore_errors=True)
    case_root.mkdir(parents=True, exist_ok=True)
    return case_root


def copy_task_fixture(temp_root: Path, source_task_id: str, target_task_id: str, include_improvement: bool = True) -> Path:
    dest_artifacts = temp_root / "artifacts"
    for directory in ("tasks", "research", "plans", "code", "verify", "status", "decisions", "improvement"):
        (dest_artifacts / directory).mkdir(parents=True, exist_ok=True)

    for source_path in (REPO_ROOT / "artifacts").rglob(f"{source_task_id}*"):
        if source_path.is_dir():
            continue
        if not include_improvement and source_path.suffix == ".md" and source_path.parent.name == "improvement":
            continue
        relative = source_path.relative_to(REPO_ROOT / "artifacts")
        dest_name = relative.name.replace(source_task_id, target_task_id, 1)
        dest_path = dest_artifacts / relative.parent / dest_name
        ensure_parent(dest_path)
        if source_path.suffix == ".json":
            payload = json.loads(source_path.read_text(encoding="utf-8"))
            if payload.get("task_id") == source_task_id:
                payload["task_id"] = target_task_id
            dest_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            text = source_path.read_text(encoding="utf-8")
            dest_path.write_text(replace_task_id(text, source_task_id, target_task_id), encoding="utf-8")
    return dest_artifacts


def contract_fixture_paths(contract_module) -> List[str]:
    paths = set(contract_module.EXACT_SYNC_FILES)
    paths.update(contract_module.REQUIRED_PHRASES.keys())
    for relative in list(paths):
        if not relative.startswith("template/"):
            paths.add(f"template/{relative}")
    return sorted(paths)


def copy_contract_fixture(temp_root: Path) -> None:
    contract_module = load_module(CONTRACT_GUARD, "guard_contract_validator_runtime")
    for relative in contract_fixture_paths(contract_module):
        source = REPO_ROOT / relative
        destination = temp_root / relative
        ensure_parent(destination)
        shutil.copy2(source, destination)


def blocked_sample_source() -> str:
    if (REPO_ROOT / "artifacts" / "tasks" / "TASK-902.task.md").exists():
        return "TASK-902"
    return "TASK-901"


def run_status_case(task_id: str, artifacts_root: Path, expected_substring: str, from_state: Optional[str] = None, to_state: Optional[str] = None, should_pass: bool = False, title: str = "", case_id: str = "", notes: str = "", extra_args: Optional[Sequence[str]] = None) -> CaseResult:
    args = [sys.executable, str(STATUS_GUARD), "--task-id", task_id, "--artifacts-root", str(artifacts_root)]
    if from_state and to_state:
        args.extend(["--from-state", from_state, "--to-state", to_state])
    if extra_args:
        args.extend(extra_args)
    result = run_command(args)
    output = (result.stdout + "\n" + result.stderr).strip()
    if should_pass:
        passed = result.returncode == 0 and "[OK] Validation passed" in output
        evidence = "[OK] Validation passed"
        expected = "pass"
    else:
        passed = result.returncode != 0
        evidence = expected_substring
        expected = "fail"
    return CaseResult(case_id=case_id, phase="static" if case_id.startswith("RT-0") else "live", title=title, expected=expected, passed=passed, exit_code=result.returncode, evidence=evidence, notes=notes or output.splitlines()[0] if output else "")


def run_contract_case(expected_substring: str, mutation: Callable[[Path], None], title: str, case_id: str, notes: str) -> CaseResult:
    temp_root = prepare_temp_root(case_id)
    try:
        copy_contract_fixture(temp_root)
        mutation(temp_root)
        result = run_command([sys.executable, str(CONTRACT_GUARD), "--root", str(temp_root)])
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)
    output = (result.stdout + "\n" + result.stderr).strip()
    passed = result.returncode != 0
    return CaseResult(case_id=case_id, phase="static", title=title, expected="fail", passed=passed, exit_code=result.returncode, evidence=expected_substring, notes=notes or output.splitlines()[0] if output else "")


def case_rt_001() -> CaseResult:
    temp_root = prepare_temp_root("RT-001")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-960")
        research_path = artifacts_root / "research" / "TASK-960.research.md"
        text = research_path.read_text(encoding="utf-8")
        text += "\n\n## Recommendation\n不要接受這份越界 research。\n"
        research_path.write_text(text, encoding="utf-8")
        return run_status_case("TASK-960", artifacts_root, "must not contain ## Recommendation", title="Research artifact contains Recommendation", case_id="RT-001")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_002() -> CaseResult:
    temp_root = prepare_temp_root("RT-002")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-961")
        research_path = artifacts_root / "research" / "TASK-961.research.md"
        text = research_path.read_text(encoding="utf-8")
        text = text.replace("- `guard_status_validator.py` 專責 task / artifact / state 驗證，會檢查 metadata、research fact-only 契約、premortem 與 Gate E", "- status validator 專責 task / artifact / state 驗證，會檢查 metadata、research fact-only 契約、premortem 與 Gate E", 1)
        text = re.sub(r"[（(]source:[^)）]+[)）]\.", ".", text, count=1)
        research_path.write_text(text, encoding="utf-8")
        return run_status_case("TASK-961", artifacts_root, "must include an inline citation", title="Confirmed Facts missing citation", case_id="RT-002")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_003() -> CaseResult:
    temp_root = prepare_temp_root("RT-003")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-962")
        research_path = artifacts_root / "research" / "TASK-962.research.md"
        text = research_path.read_text(encoding="utf-8").replace("## Uncertain Items\nNone", "## Uncertain Items\n- Needs manual follow-up")
        research_path.write_text(text, encoding="utf-8")
        return run_status_case("TASK-962", artifacts_root, "must start with UNVERIFIED:", title="Uncertain Items missing UNVERIFIED marker", case_id="RT-003")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_004() -> CaseResult:
    temp_root = prepare_temp_root("RT-004")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-963")
        task_path = artifacts_root / "tasks" / "TASK-963.task.md"
        task_text = task_path.read_text(encoding="utf-8").replace("驗證內建 sample artifacts 與兩支 guard（`guard_status_validator.py`、`guard_contract_validator.py`）在 root repo 中都能正常通過。", "驗證一個 security-sensitive workflow task 在高風險前提下，premortem 是否真的要求 blocking risk。")
        task_path.write_text(task_text, encoding="utf-8")
        plan_path = artifacts_root / "plans" / "TASK-963.plan.md"
        plan_text = plan_path.read_text(encoding="utf-8")
        plan_text = plan_text.replace("Severity: blocking", "Severity: non-blocking", 1)
        extra_risks = """- R3\n  - Risk: security-sensitive task 的 drift 說明沒有被 README 與 Obsidian 同步\n  - Trigger: 演練只更新單一入口文件\n  - Detection: contract guard 或人工交叉閱讀發現不一致\n  - Mitigation: 在同步步驟中強制包含 README 與 Obsidian\n  - Severity: non-blocking\n- R4\n  - Risk: high-risk task 的驗證只靠口頭判定\n  - Trigger: verify evidence 沒有列出實際 guard 命令\n  - Detection: verify artifact 缺少 evidence 指向 guard\n  - Mitigation: 在 verify 中固定列出 guard 命令與結果\n  - Severity: non-blocking\n\n"""
        plan_text = plan_text.replace("## Validation Strategy\n", extra_risks + "## Validation Strategy\n")
        plan_path.write_text(plan_text, encoding="utf-8")
        status_path = artifacts_root / "status" / "TASK-963.status.json"
        status = json.loads(status_path.read_text(encoding="utf-8"))
        status["state"] = "coding"
        status["required_artifacts"] = ["code", "plan", "research", "status", "task"]
        status["available_artifacts"] = ["code", "plan", "research", "status", "task", "verify"]
        status["missing_artifacts"] = []
        status_path.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return run_status_case("TASK-963", artifacts_root, "high-risk premortem must include at least one blocking risk", title="High-risk premortem without blocking risk", case_id="RT-004")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_005() -> CaseResult:
    temp_root = prepare_temp_root("RT-005")
    try:
        artifacts_root = copy_task_fixture(temp_root, blocked_sample_source(), "TASK-964", include_improvement=False)
        return run_status_case("TASK-964", artifacts_root, "requires an improvement artifact", from_state="blocked", to_state="planned", title="Blocked resume without improvement artifact", case_id="RT-005")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_006() -> CaseResult:
    temp_root = prepare_temp_root("RT-006")
    try:
        artifacts_root = copy_task_fixture(temp_root, blocked_sample_source(), "TASK-965")
        improvement_path = artifacts_root / "improvement" / "TASK-965.improvement.md"
        text = improvement_path.read_text(encoding="utf-8").replace("- Status: applied", "- Status: approved", 1).replace("## 9. Status\napplied", "## 9. Status\napproved")
        improvement_path.write_text(text, encoding="utf-8")
        return run_status_case("TASK-965", artifacts_root, "requires an improvement artifact with Status: applied", from_state="blocked", to_state="planned", title="Blocked resume with non-applied improvement", case_id="RT-006")
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_007() -> CaseResult:
    def mutation(temp_root: Path) -> None:
        path = temp_root / "template" / "docs" / "workflow_state_machine.md"
        path.write_text(path.read_text(encoding="utf-8") + "\n<!-- red-team drift marker -->\n", encoding="utf-8")
    return run_contract_case("Contract drift detected", mutation, "Contract drift between root and template", "RT-007", "template workflow state machine drift")


def case_rt_008() -> CaseResult:
    def mutation(temp_root: Path) -> None:
        path = temp_root / "OBSIDIAN.md"
        # Replace "Status: applied" with a neutral string so the required phrase is absent
        text = path.read_text(encoding="utf-8").replace("Status: applied", "Status: draft")
        path.write_text(text, encoding="utf-8")
    return run_contract_case("OBSIDIAN.md missing required phrase: Status: applied", mutation, "Obsidian drift", "RT-008", "Obsidian missing Gate E phrase")


def case_rt_009() -> CaseResult:
    def mutation(temp_root: Path) -> None:
        path = temp_root / "BOOTSTRAP_PROMPT.md"
        # Remove all lines containing guard_contract_validator.py so the required phrase is absent
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        text = "".join(line for line in lines if "guard_contract_validator.py" not in line)
        path.write_text(text, encoding="utf-8")
    return run_contract_case("BOOTSTRAP_PROMPT.md missing required phrase: guard_contract_validator.py", mutation, "Bootstrap missing contract guard", "RT-009", "bootstrap lost contract-guard step")


def case_rt_010() -> CaseResult:
    temp_root = prepare_temp_root("RT-010")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-966")
        initialize_git_fixture(temp_root)
        code_path = artifacts_root / "code" / "TASK-966.code.md"
        code_text = code_path.read_text(encoding="utf-8")
        code_path.write_text(code_text + "\n<!-- git-backed scope drift drill -->\n", encoding="utf-8")
        rogue_path = temp_root / "docs" / "rogue-change.md"
        ensure_parent(rogue_path)
        rogue_path.write_text("# Rogue Change\nThis file simulates an undeclared workspace change.\n", encoding="utf-8")
        return run_status_case(
            "TASK-966",
            artifacts_root,
            "git-backed scope check found actual changed files not listed",
            title="Git-backed scope drift auto-guard",
            case_id="RT-010",
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_011() -> CaseResult:
    temp_root = prepare_temp_root("RT-011")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-967")
        initialize_git_fixture(temp_root)
        base_commit = git_rev_parse(temp_root, "HEAD")
        rogue_path = temp_root / "docs" / "rogue-history.md"
        ensure_parent(rogue_path)
        rogue_path.write_text("# Rogue History\nThis file simulates an undeclared committed change.\n", encoding="utf-8")
        ensure_command_ok(run_command(["git", "add", "."], cwd=temp_root), "git add historical replay drift source")
        ensure_command_ok(run_command(["git", "commit", "-q", "-m", "historical replay drift source"], cwd=temp_root), "git commit historical replay drift source")
        head_commit = git_rev_parse(temp_root, "HEAD")
        code_path = artifacts_root / "code" / "TASK-967.code.md"
        code_text = code_path.read_text(encoding="utf-8")
        snapshot_files = ["docs/rogue-history.md"]
        snapshot_hash = compute_snapshot_sha256(snapshot_files)
        code_text += (
            "\n\n## Diff Evidence\n"
            "- Evidence Type: commit-range\n"
            "- Base Ref: HEAD~1\n"
            "- Head Ref: HEAD\n"
            f"- Base Commit: {base_commit}\n"
            f"- Head Commit: {head_commit}\n"
            "- Diff Command: git diff --name-only HEAD~1..HEAD\n"
            f"- Changed Files Snapshot: {', '.join(snapshot_files)}\n"
            f"- Snapshot SHA256: {snapshot_hash}\n"
        )
        code_path.write_text(code_text, encoding="utf-8")
        ensure_command_ok(run_command(["git", "add", "."], cwd=temp_root), "git add historical replay evidence")
        ensure_command_ok(run_command(["git", "commit", "-q", "-m", "historical replay evidence"], cwd=temp_root), "git commit historical replay evidence")
        return run_status_case(
            "TASK-967",
            artifacts_root,
            "commit-range scope check found diff files not listed",
            title="Historical commit-range diff reconstruction",
            case_id="RT-011",
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_014() -> CaseResult:
    temp_root = prepare_temp_root("RT-014")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-970")
        initialize_git_fixture(temp_root)
        base_commit = git_rev_parse(temp_root, "HEAD")
        pinned_path = temp_root / "docs" / "pinned-history.md"
        ensure_parent(pinned_path)
        pinned_path.write_text("# Pinned History\nThis file simulates a replayable historical change.\n", encoding="utf-8")
        ensure_command_ok(run_command(["git", "add", "."], cwd=temp_root), "git add historical checksum source")
        ensure_command_ok(run_command(["git", "commit", "-q", "-m", "historical checksum source"], cwd=temp_root), "git commit historical checksum source")
        head_commit = git_rev_parse(temp_root, "HEAD")
        code_path = artifacts_root / "code" / "TASK-970.code.md"
        code_text = code_path.read_text(encoding="utf-8")
        snapshot_files = ["docs/pinned-history.md"]
        code_text += (
            "\n\n## Diff Evidence\n"
            "- Evidence Type: commit-range\n"
            "- Base Ref: HEAD~1\n"
            "- Head Ref: HEAD\n"
            f"- Base Commit: {base_commit}\n"
            f"- Head Commit: {head_commit}\n"
            "- Diff Command: git diff --name-only HEAD~1..HEAD\n"
            f"- Changed Files Snapshot: {', '.join(snapshot_files)}\n"
            f"- Snapshot SHA256: {compute_snapshot_sha256(['docs/pinned-history.md', 'docs/rogue-history.md'])}\n"
        )
        code_path.write_text(code_text, encoding="utf-8")
        ensure_command_ok(run_command(["git", "add", "."], cwd=temp_root), "git add historical checksum evidence")
        ensure_command_ok(run_command(["git", "commit", "-q", "-m", "historical checksum evidence"], cwd=temp_root), "git commit historical checksum evidence")
        return run_status_case(
            "TASK-970",
            artifacts_root,
            "Snapshot SHA256 does not match Changed Files Snapshot",
            title="Historical diff evidence checksum corruption",
            case_id="RT-014",
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_015() -> CaseResult:
    temp_root = prepare_temp_root("RT-015")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-971")
        initialize_git_fixture(temp_root)
        repository = "octo/workflow"
        pull_number = "invalid"
        pages = {
            1: [{"filename": "docs/provider-safe.md"}],
            2: [{"filename": "docs/provider-rogue.md"}],
            3: [],
        }
        with github_pr_files_server(repository, pull_number, pages) as api_base_url:
            code_path = artifacts_root / "code" / "TASK-971.code.md"
            code_text = code_path.read_text(encoding="utf-8")
            code_text = re.sub(r"\n## Diff Evidence\s*\n.*?(?=\n## |\Z)", "", code_text, flags=re.DOTALL)
            snapshot_files = ["docs/provider-safe.md", "docs/provider-rogue.md"]
            code_text += (
                "\n\n## Diff Evidence\n"
                "- Evidence Type: github-pr\n"
                f"- Repository: {repository}\n"
                f"- PR Number: {pull_number}\n"
                f"- API Base URL: {api_base_url}\n"
                f"- Changed Files Snapshot: {', '.join(snapshot_files)}\n"
                f"- Snapshot SHA256: {compute_snapshot_sha256(snapshot_files)}\n"
            )
            code_path.write_text(code_text, encoding="utf-8")
            ensure_command_ok(run_command(["git", "add", "."], cwd=temp_root), "git add github-pr evidence")
            ensure_command_ok(run_command(["git", "commit", "-q", "-m", "github-pr evidence"], cwd=temp_root), "git commit github-pr evidence")
            return run_status_case(
                "TASK-971",
                artifacts_root,
                "PR Number must be a positive integer",
                title="GitHub provider-backed PR diff reconstruction",
                case_id="RT-015",
            )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_016() -> CaseResult:
    temp_root = prepare_temp_root("RT-016")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-972")
        initialize_git_fixture(temp_root)
        archive_rel = "artifacts/evidence/TASK-972.changed-files.txt"
        archive_path = temp_root / archive_rel
        ensure_parent(archive_path)
        archive_bytes = b"docs/archive-fallback.md\n"
        archive_path.write_bytes(archive_bytes)
        archive_sha256 = hashlib.sha256(archive_bytes).hexdigest()
        code_path = artifacts_root / "code" / "TASK-972.code.md"
        code_text = code_path.read_text(encoding="utf-8")
        snapshot_files = ["docs/archive-fallback.md"]
        code_text += (
            "\n\n## Diff Evidence\n"
            "- Evidence Type: commit-range\n"
            f"- Base Commit: {'1' * 40}\n"
            f"- Head Commit: {'2' * 40}\n"
            "- Diff Command: git diff --name-only <base>..<head>\n"
            f"- Changed Files Snapshot: {', '.join(snapshot_files)}\n"
            f"- Snapshot SHA256: {compute_snapshot_sha256(snapshot_files)}\n"
            f"- Archive Path: {archive_rel}\n"
            f"- Archive SHA256: {archive_sha256}\n"
        )
        code_path.write_text(code_text, encoding="utf-8")
        ensure_command_ok(run_command(["git", "add", "."], cwd=temp_root), "git add archive fallback evidence")
        ensure_command_ok(run_command(["git", "commit", "-q", "-m", "archive fallback evidence"], cwd=temp_root), "git commit archive fallback evidence")
        return run_status_case(
            "TASK-972",
            artifacts_root,
            "commit-range archive fallback found diff files not listed",
            title="Historical diff archive fallback reconstruction",
            case_id="RT-016",
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_017() -> CaseResult:
    temp_root = prepare_temp_root("RT-017")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-973")
        initialize_git_fixture(temp_root)
        archive_rel = "artifacts/evidence/TASK-973.changed-files.txt"
        archive_path = temp_root / archive_rel
        ensure_parent(archive_path)
        archive_bytes = b"docs/archive-corrupt.md\n"
        archive_path.write_bytes(archive_bytes)
        code_path = artifacts_root / "code" / "TASK-973.code.md"
        code_text = code_path.read_text(encoding="utf-8")
        snapshot_files = ["docs/archive-corrupt.md"]
        code_text += (
            "\n\n## Diff Evidence\n"
            "- Evidence Type: commit-range\n"
            f"- Base Commit: {'1' * 40}\n"
            f"- Head Commit: {'2' * 40}\n"
            "- Diff Command: git diff --name-only <base>..<head>\n"
            f"- Changed Files Snapshot: {', '.join(snapshot_files)}\n"
            f"- Snapshot SHA256: {compute_snapshot_sha256(snapshot_files)}\n"
            f"- Archive Path: {archive_rel}\n"
            f"- Archive SHA256: {'0' * 64}\n"
        )
        code_path.write_text(code_text, encoding="utf-8")
        ensure_command_ok(run_command(["git", "add", "."], cwd=temp_root), "git add archive corruption evidence")
        ensure_command_ok(run_command(["git", "commit", "-q", "-m", "archive corruption evidence"], cwd=temp_root), "git commit archive corruption evidence")
        return run_status_case(
            "TASK-973",
            artifacts_root,
            "Archive SHA256 does not match archive file",
            title="Historical diff archive corruption",
            case_id="RT-017",
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_012() -> CaseResult:
    temp_root = prepare_temp_root("RT-012")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-968")
        initialize_git_fixture(temp_root)
        code_path = artifacts_root / "code" / "TASK-968.code.md"
        text = code_path.read_text(encoding="utf-8")
        text = text.replace("## Summary Of Changes", "- `docs/rogue-waiver.md`\n\n## Summary Of Changes", 1)
        code_path.write_text(text, encoding="utf-8")
        return run_status_case(
            "TASK-968",
            artifacts_root,
            "--allow-scope-drift requires a decision artifact with ## Guard Exception",
            title="allow-scope-drift without decision waiver",
            case_id="RT-012",
            extra_args=["--allow-scope-drift"],
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_rt_013() -> CaseResult:
    temp_root = prepare_temp_root("RT-013")
    try:
        artifacts_root = copy_task_fixture(temp_root, "TASK-900", "TASK-969")
        initialize_git_fixture(temp_root)
        code_path = artifacts_root / "code" / "TASK-969.code.md"
        text = code_path.read_text(encoding="utf-8")
        text = text.replace("## Summary Of Changes", "- `docs/rogue-waiver.md`\n\n## Summary Of Changes", 1)
        code_path.write_text(text, encoding="utf-8")
        decision_path = artifacts_root / "decisions" / "TASK-969.decision.md"
        decision_path.write_text(
            "# Decision Log: TASK-969\n\n"
            "## Metadata\n"
            "- Task ID: TASK-969\n"
            "- Artifact Type: decision\n"
            "- Owner: Claude\n"
            "- Status: done\n"
            "- Last Updated: 2026-04-13T13:55:35+08:00\n\n"
            "## Issue\n"
            "這個 red-team case 需要模擬一個受控的 scope drift waiver。\n\n"
            "## Options Considered\n"
            "- 保持 strict scope，讓案例直接 fail\n"
            "- 使用 `--allow-scope-drift`，但不提供 decision waiver\n"
            "- 使用 `--allow-scope-drift`，並附帶顯式 decision waiver\n\n"
            "## Chosen Option\n"
            "使用 `--allow-scope-drift`，並附帶顯式 decision waiver。\n\n"
            "## Reasoning\n"
            "這個案例的目的就是驗證 validator 只接受結構化 waiver，而不是任何口頭例外。\n\n"
            "## Implications\n"
            "- `docs/rogue-waiver.md` 應被視為明確列出的受控 drift\n"
            "- 沒有 `## Guard Exception` 時，案例必須失敗\n\n"
            "## Follow Up\n"
            "保留此案例作為 decision-gated waiver static drill。\n\n"
            "## Guard Exception\n"
            "- Exception Type: allow-scope-drift\n"
            "- Scope Files: docs/rogue-waiver.md\n"
            "- Justification: red-team static drill requires one explicit waived file to verify the guard boundary.\n",
            encoding="utf-8",
        )
        return run_status_case(
            "TASK-969",
            artifacts_root,
            "[OK] Validation passed",
            title="allow-scope-drift with explicit decision waiver",
            case_id="RT-013",
            should_pass=True,
            extra_args=["--allow-scope-drift"],
        )
    finally:
        shutil.rmtree(temp_root, ignore_errors=True)


def case_live_950() -> CaseResult:
    result = run_command([sys.executable, str(STATUS_GUARD), "--task-id", "TASK-950", "--artifacts-root", str(REPO_ROOT / "artifacts")])
    output = (result.stdout + "\n" + result.stderr).strip()
    passed = result.returncode == 0 and "[OK] Validation passed" in output
    return CaseResult(case_id="RT-LIVE-950", phase="live", title="Role boundary live drill", expected="pass", passed=passed, exit_code=result.returncode, evidence="[OK] Validation passed", notes="TASK-950 live drill should stay valid after decision / improvement closure")


def case_live_951() -> CaseResult:
    result = run_command([sys.executable, str(STATUS_GUARD), "--task-id", "TASK-951", "--artifacts-root", str(REPO_ROOT / "artifacts")])
    output = (result.stdout + "\n" + result.stderr).strip()
    passed = result.returncode == 0 and "[OK] Validation passed" in output
    return CaseResult(case_id="RT-LIVE-951", phase="live", title="Blocked / PDCA / resume live drill", expected="pass", passed=passed, exit_code=result.returncode, evidence="[OK] Validation passed", notes="TASK-951 live drill should prove Gate E before resume")


def run_prompt_case(case_id: str, title: str, notes: str) -> CaseResult:
    result = run_command([sys.executable, str(PROMPT_REGRESSION), "--root", str(REPO_ROOT), "--case-id", case_id])
    output = (result.stdout + "\n" + result.stderr).strip()
    passed = result.returncode == 0
    evidence = "Prompt Regression Report"
    return CaseResult(
        case_id=case_id,
        phase="prompt",
        title=title,
        expected="pass",
        passed=passed,
        exit_code=result.returncode,
        evidence=evidence,
        notes=notes or (output.splitlines()[0] if output else ""),
    )


def case_pr_001() -> CaseResult:
    return run_prompt_case(
        "PR-001",
        "Violation input handling contract",
        "CLAUDE/CODEX prompts should enforce STOP or blocked behavior under ambiguous or invalid inputs",
    )


def case_pr_002() -> CaseResult:
    return run_prompt_case(
        "PR-002",
        "Role boundary contract",
        "Prompt contracts should prevent role overreach across Claude/Gemini/Codex",
    )


def case_pr_003() -> CaseResult:
    return run_prompt_case(
        "PR-003",
        "Fake citation defense contract",
        "Research prompt should enforce claim-level citation and anti-fabrication rules",
    )


def case_pr_004() -> CaseResult:
    return run_prompt_case(
        "PR-004",
        "Mixed truth-source isolation contract",
        "Research prompt should isolate upstream truth source from local fork assumptions",
    )


def case_pr_005() -> CaseResult:
    return run_prompt_case(
        "PR-005",
        "Research recommendation boundary",
        "Research prompt should explicitly forbid recommendation or architecture design outputs",
    )


def case_pr_006() -> CaseResult:
    return run_prompt_case(
        "PR-006",
        "Blocked wording quality contract",
        "Implementation prompt should keep blocked criteria explicit and avoid optimistic ambiguity",
    )


def case_pr_007() -> CaseResult:
    return run_prompt_case(
        "PR-007",
        "Premortem enforcement contract",
        "Implementation prompt should enforce premortem quality before coding",
    )


def case_pr_008() -> CaseResult:
    return run_prompt_case(
        "PR-008",
        "Artifact-only truth and completion contract",
        "Claude prompt should rely only on artifacts and reject completion without artifacts, verification, and evidence",
    )


def case_pr_009() -> CaseResult:
    return run_prompt_case(
        "PR-009",
        "Workflow sync completeness contract",
        "Workflow prompt should require root/template sync, placeholder generalization, and README/Obsidian updates for workflow changes",
    )


def case_pr_010() -> CaseResult:
    return run_prompt_case(
        "PR-010",
        "Research blocked preconditions contract",
        "Gemini prompt should block free-form research when task scope, query scope, or source credibility is missing",
    )


def case_pr_011() -> CaseResult:
    return run_prompt_case(
        "PR-011",
        "Implementation summary discipline contract",
        "Codex prompt should preserve approved-plan discipline, summary artifacts, and single-writer behavior",
    )


def case_pr_012() -> CaseResult:
    return run_prompt_case(
        "PR-012",
        "Conflict to decision routing contract",
        "Workflow contract should route conflicts into a recorded decision log before progress continues",
    )


def case_pr_013() -> CaseResult:
    return run_prompt_case(
        "PR-013",
        "Decision artifact trigger matrix contract",
        "Workflow contract should define when a decision artifact is mandatory for conflicts, tradeoffs, and validation failures",
    )


def case_pr_014() -> CaseResult:
    return run_prompt_case(
        "PR-014",
        "Decision artifact schema completeness contract",
        "Decision artifacts should preserve the chain from issue to follow-up rather than a single conclusion",
    )


def case_pr_015() -> CaseResult:
    return run_prompt_case(
        "PR-015",
        "External failure stop contract",
        "Claude prompt should stop and record external environment, build, or test failures without expanding scope",
    )


def case_pr_016() -> CaseResult:
    return run_prompt_case(
        "PR-016",
        "Decision-gated scope waiver contract",
        "Workflow contract should require an explicit decision waiver before --allow-scope-drift can downgrade failures",
    )


def case_pr_017() -> CaseResult:
    return run_prompt_case(
        "PR-017",
        "Historical diff evidence contract",
        "Workflow contract should define commit-range diff evidence for clean-task historical reconstruction",
    )


def case_pr_018() -> CaseResult:
    return run_prompt_case(
        "PR-018",
        "Pinned diff evidence integrity contract",
        "Workflow contract should require pinned commits plus snapshot checksum for immutable historical replay",
    )


def case_pr_019() -> CaseResult:
    return run_prompt_case(
        "PR-019",
        "GitHub provider-backed diff evidence contract",
        "Workflow contract should define GitHub PR files evidence, API base override, and token boundary for provider-backed replay",
    )


def case_pr_020() -> CaseResult:
    return run_prompt_case(
        "PR-020",
        "Archive retention fallback contract",
        "Workflow contract should define archive-backed fallback and archive integrity checks when git objects are no longer available",
    )


def build_cases() -> List[CaseDefinition]:
    return [
        CaseDefinition("RT-001", "static", "Research artifact contains Recommendation", "fail", case_rt_001),
        CaseDefinition("RT-002", "static", "Confirmed Facts missing citation", "fail", case_rt_002),
        CaseDefinition("RT-003", "static", "Uncertain Items missing UNVERIFIED marker", "fail", case_rt_003),
        CaseDefinition("RT-004", "static", "High-risk premortem without blocking risk", "fail", case_rt_004),
        CaseDefinition("RT-005", "static", "Blocked resume without improvement artifact", "fail", case_rt_005),
        CaseDefinition("RT-006", "static", "Blocked resume with non-applied improvement", "fail", case_rt_006),
        CaseDefinition("RT-007", "static", "Contract drift between root and template", "fail", case_rt_007),
        CaseDefinition("RT-008", "static", "Obsidian drift", "fail", case_rt_008),
        CaseDefinition("RT-009", "static", "Bootstrap missing contract guard", "fail", case_rt_009),
        CaseDefinition("RT-010", "static", "Git-backed scope drift auto-guard", "fail", case_rt_010),
        CaseDefinition("RT-011", "static", "Historical commit-range diff reconstruction", "fail", case_rt_011),
        CaseDefinition("RT-012", "static", "allow-scope-drift without decision waiver", "fail", case_rt_012),
        CaseDefinition("RT-013", "static", "allow-scope-drift with explicit decision waiver", "pass", case_rt_013),
        CaseDefinition("RT-014", "static", "Historical diff evidence checksum corruption", "fail", case_rt_014),
        CaseDefinition("RT-015", "static", "GitHub provider-backed PR diff reconstruction", "fail", case_rt_015),
        CaseDefinition("RT-016", "static", "Historical diff archive fallback reconstruction", "fail", case_rt_016),
        CaseDefinition("RT-017", "static", "Historical diff archive corruption", "fail", case_rt_017),
        CaseDefinition("RT-LIVE-950", "live", "Role boundary live drill", "pass", case_live_950),
        CaseDefinition("RT-LIVE-951", "live", "Blocked / PDCA / resume live drill", "pass", case_live_951),
        CaseDefinition("PR-001", "prompt", "Violation input handling contract", "pass", case_pr_001),
        CaseDefinition("PR-002", "prompt", "Role boundary contract", "pass", case_pr_002),
        CaseDefinition("PR-003", "prompt", "Fake citation defense contract", "pass", case_pr_003),
        CaseDefinition("PR-004", "prompt", "Mixed truth-source isolation contract", "pass", case_pr_004),
        CaseDefinition("PR-005", "prompt", "Research recommendation boundary", "pass", case_pr_005),
        CaseDefinition("PR-006", "prompt", "Blocked wording quality contract", "pass", case_pr_006),
        CaseDefinition("PR-007", "prompt", "Premortem enforcement contract", "pass", case_pr_007),
        CaseDefinition("PR-008", "prompt", "Artifact-only truth and completion contract", "pass", case_pr_008),
        CaseDefinition("PR-009", "prompt", "Workflow sync completeness contract", "pass", case_pr_009),
        CaseDefinition("PR-010", "prompt", "Research blocked preconditions contract", "pass", case_pr_010),
        CaseDefinition("PR-011", "prompt", "Implementation summary discipline contract", "pass", case_pr_011),
        CaseDefinition("PR-012", "prompt", "Conflict to decision routing contract", "pass", case_pr_012),
        CaseDefinition("PR-013", "prompt", "Decision artifact trigger matrix contract", "pass", case_pr_013),
        CaseDefinition("PR-014", "prompt", "Decision artifact schema completeness contract", "pass", case_pr_014),
        CaseDefinition("PR-015", "prompt", "External failure stop contract", "pass", case_pr_015),
        CaseDefinition("PR-016", "prompt", "Decision-gated scope waiver contract", "pass", case_pr_016),
        CaseDefinition("PR-017", "prompt", "Historical diff evidence contract", "pass", case_pr_017),
        CaseDefinition("PR-018", "prompt", "Pinned diff evidence integrity contract", "pass", case_pr_018),
        CaseDefinition("PR-019", "prompt", "GitHub provider-backed diff evidence contract", "pass", case_pr_019),
        CaseDefinition("PR-020", "prompt", "Archive retention fallback contract", "pass", case_pr_020),
    ]


def render_markdown(results: Iterable[CaseResult]) -> str:
    lines = [
        "# Red Team Suite Report",
        "",
        "| Case | Phase | Expected | Outcome | Exit Code | Evidence | Notes |",
        "|---|---|---|---|---:|---|---|",
    ]
    for result in results:
        outcome = "pass" if result.passed else "fail"
        lines.append(f"| `{result.case_id}` | {result.phase} | {result.expected} | {outcome} | {result.exit_code} | `{result.evidence}` | {result.notes} |")
    return "\n".join(lines) + "\n"


def parse_args(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run built-in red-team exercises for the artifact-first workflow.")
    parser.add_argument("--phase", choices=("static", "live", "prompt", "all"), default="all", help="Which phase to run. Default: all")
    parser.add_argument("--output", help="Optional path to write the markdown report")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_args(argv)
    selected = [case for case in build_cases() if args.phase in ("all", case.phase)]
    results = [case.runner() for case in selected]
    report = render_markdown(results)
    print(report, end="")
    if args.output:
        output_path = Path(args.output)
        ensure_parent(output_path)
        output_path.write_text(report, encoding="utf-8")
    return 0 if all(result.passed for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
