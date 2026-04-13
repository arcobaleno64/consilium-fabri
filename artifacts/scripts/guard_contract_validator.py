#!/usr/bin/env python3
from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Sequence

EXACT_SYNC_FILES = [
    "AGENTS.md",
    "BOOTSTRAP_PROMPT.md",
    "CODEX.md",
    "GEMINI.md",
    "artifacts/scripts/guard_contract_validator.py",
    "artifacts/scripts/prompt_regression_validator.py",
    "artifacts/scripts/run_red_team_suite.py",
    "artifacts/scripts/drills/prompt_regression_cases.json",
    "artifacts/scripts/guard_status_validator.py",
    "docs/artifact_schema.md",
    "docs/lightweight_mode_rules.md",
    "docs/orchestration.md",
    "docs/premortem_rules.md",
    "docs/red_team_backlog.md",
    "docs/red_team_runbook.md",
    "docs/red_team_scorecard.md",
    "docs/subagent_roles.md",
    "docs/subagent_task_templates.md",
    "docs/workflow_state_machine.md",
]

REQUIRED_PHRASES: Dict[str, Sequence[str]] = {
    "BOOTSTRAP_PROMPT.md": (
        "guard_contract_validator.py",
        "template/OBSIDIAN.md",
        "prompt_regression_validator.py",
    ),
    "template/BOOTSTRAP_PROMPT.md": (
        "guard_contract_validator.py",
        "template/OBSIDIAN.md",
        "prompt_regression_validator.py",
    ),
    "CLAUDE.md": (
        "guard_contract_validator.py",
        "OBSIDIAN.md",
        "template/OBSIDIAN.md",
        "任一同步缺漏（包含 Obsidian 入口）都視為 workflow 變更未完成。",
    ),
    "template/CLAUDE.md": (
        "guard_contract_validator.py",
        "OBSIDIAN.md",
        "template/OBSIDIAN.md",
        "任一同步缺漏（包含 Obsidian 入口）都視為 workflow 變更未完成。",
    ),
    "OBSIDIAN.md": (
        "Research artifact 是 fact-only 契約",
        "Status: applied",
        "contract guard",
        "run_red_team_suite.py",
        "prompt_regression_validator.py",
    ),
    "template/OBSIDIAN.md": (
        "Research artifact 是 fact-only 契約",
        "Status: applied",
        "contract guard",
        "run_red_team_suite.py",
        "prompt_regression_validator.py",
    ),
    "README.md": (
        "guard_status_validator.py",
        "guard_contract_validator.py",
        "Obsidian",
        "run_red_team_suite.py",
        "prompt_regression_validator.py",
    ),
    "README.zh-TW.md": (
        "guard_status_validator.py",
        "guard_contract_validator.py",
        "Obsidian",
        "run_red_team_suite.py",
        "prompt_regression_validator.py",
    ),
    "template/README.md": (
        "guard_status_validator.py",
        "guard_contract_validator.py",
        "Obsidian",
        "run_red_team_suite.py",
        "prompt_regression_validator.py",
    ),
    "template/README.zh-TW.md": (
        "guard_status_validator.py",
        "guard_contract_validator.py",
        "Obsidian",
        "run_red_team_suite.py",
        "prompt_regression_validator.py",
    ),
}

PLACEHOLDER_PATTERNS = (
    (r"\{\{PROJECT_NAME\}\}", "__PROJECT__"),
    (r"\{\{REPO_NAME\}\}", "__REPO__"),
    (r"\{\{UPSTREAM_ORG\}\}", "__ORG__"),
)

PROMPT_ENTRY_FILES = {
    "CLAUDE.md",
    "GEMINI.md",
    "CODEX.md",
    "template/CLAUDE.md",
    "template/GEMINI.md",
    "template/CODEX.md",
}

PROMPT_REGRESSION_FILES = {
    "artifacts/scripts/drills/prompt_regression_cases.json",
    "template/artifacts/scripts/drills/prompt_regression_cases.json",
}


def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    for pattern, replacement in PLACEHOLDER_PATTERNS:
        normalized = re.sub(pattern, replacement, normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def validate_exact_sync(root: Path) -> List[str]:
    errors: List[str] = []
    for relative in EXACT_SYNC_FILES:
        root_path = root / relative
        template_path = root / "template" / relative
        if not root_path.exists():
            errors.append(f"Missing root file: {relative}")
            continue
        if not template_path.exists():
            errors.append(f"Missing template file: template/{relative}")
            continue
        if normalize_text(load_text(root_path)) != normalize_text(load_text(template_path)):
            errors.append(f"Contract drift detected between {relative} and template/{relative}")
    return errors


def validate_required_phrases(root: Path) -> List[str]:
    errors: List[str] = []
    for relative, phrases in REQUIRED_PHRASES.items():
        path = root / relative
        if not path.exists():
            errors.append(f"Missing required file: {relative}")
            continue
        text = load_text(path)
        for phrase in phrases:
            if phrase not in text:
                errors.append(f"{relative} missing required phrase: {phrase}")
    return errors


def detect_changed_files(root: Path) -> tuple[bool, set[str]]:
    commands = [
        ["git", "-C", str(root), "diff", "--name-only", "HEAD"],
        ["git", "-C", str(root), "diff", "--name-only", "--cached"],
        ["git", "-C", str(root), "ls-files", "--others", "--exclude-standard"],
    ]
    available = False
    changed: set[str] = set()
    for command in commands:
        try:
            result = subprocess.run(command, capture_output=True, text=True, check=False, encoding="utf-8")
        except FileNotFoundError:
            return False, set()
        if result.returncode != 0:
            continue
        available = True
        for line in result.stdout.splitlines():
            token = line.strip().replace("\\", "/")
            if token:
                changed.add(token)
    return available, changed


def validate_prompt_case_sync(root: Path) -> List[str]:
    available, changed = detect_changed_files(root)
    if not available or not changed:
        return []
    if changed.intersection(PROMPT_ENTRY_FILES) and not changed.intersection(PROMPT_REGRESSION_FILES):
        return [
            "Prompt contract changed but prompt regression cases were not updated. "
            "When modifying CLAUDE/GEMINI/CODEX prompts, also update artifacts/scripts/drills/prompt_regression_cases.json"
        ]
    return []


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate workflow contract sync across root, template, and Obsidian docs.")
    parser.add_argument("--root", default=".", help="Repository root. Default: current directory")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    errors = validate_exact_sync(root)
    errors.extend(validate_required_phrases(root))
    errors.extend(validate_prompt_case_sync(root))

    if errors:
        print("[ERROR] Contract validation failed")
        for error in errors:
            print(f"[FAIL] {error}")
        return 1

    print("[OK] Contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
