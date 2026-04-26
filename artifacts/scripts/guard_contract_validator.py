#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import subprocess
from pathlib import Path
from typing import Dict, List, Sequence

import guard_status_validator as gsv
from workflow_constants import REQUIRED_TOPICS, TOPIC_PATTERN, validate_workflow_rule_tables

SOURCE_REPO_SENTINEL = ".consilium-source-repo"
SOURCE_REPO_MODE = "source"
DOWNSTREAM_REPO_MODE = "downstream"

EXACT_SYNC_FILES = [
    "AGENTS.md",
    "BOOTSTRAP_PROMPT.md",
    "CODEX.md",
    "GEMINI.md",
    "START_HERE.md",
    "requirements-dev.txt",
    "artifacts/scripts/build_decision_registry.py",
    "artifacts/scripts/guard_contract_validator.py",
    "artifacts/scripts/prompt_regression_validator.py",
    "artifacts/scripts/run_red_team_suite.py",
    "artifacts/scripts/drills/prompt_regression_cases.json",
    "artifacts/scripts/guard_status_validator.py",
    "artifacts/scripts/migrate_artifact_schema.py",
    "artifacts/scripts/update_repository_profile.py",
    "artifacts/scripts/workflow_constants.py",
    "docs/artifact_schema.md",
    "docs/agentic_execution_layer.md",
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

COMMON_REQUIRED_PHRASES: Dict[str, Sequence[str]] = {
    "BOOTSTRAP_PROMPT.md": (
        "guard_contract_validator.py",
        "prompt_regression_validator.py",
        "update_repository_profile.py",
        "downstream terminal repo",
    ),
    "template/BOOTSTRAP_PROMPT.md": (
        "guard_contract_validator.py",
        "prompt_regression_validator.py",
        "update_repository_profile.py",
        "downstream terminal repo",
    ),
}

SOURCE_REQUIRED_PHRASES: Dict[str, Sequence[str]] = {
    "CLAUDE.md": (
        "guard_contract_validator.py",
        "OBSIDIAN.md",
        "template/OBSIDIAN.md",
        ".consilium-source-repo",
        "source template repo",
        "任一同步缺漏（包含 Obsidian 入口）都視為 workflow 變更未完成。",
    ),
    "template/CLAUDE.md": (
        "downstream terminal repo",
        "不得再建立新的 `template/`",
        "只維護 root 文件",
        "guard_contract_validator.py",
    ),
}

DOWNSTREAM_REQUIRED_PHRASES: Dict[str, Sequence[str]] = {
    "CLAUDE.md": (
        "downstream terminal repo",
        "不得再建立新的 `template/`",
        "只維護 root 文件",
        "guard_contract_validator.py",
        "OBSIDIAN.md",
        "不再建立新的 `template/`",
    ),
}

# Backward-compatible alias for tests and external imports that only need the
# source-repo map shape.
REQUIRED_PHRASES = {**COMMON_REQUIRED_PHRASES, **SOURCE_REQUIRED_PHRASES}

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

REPOSITORY_PROFILE_FILES = (
    ".github/repository-profile.json",
    "template/.github/repository-profile.json",
)

ACTIVE_GEMINI_POLICY_FILES = (
    "CLAUDE.md",
    "BOOTSTRAP_PROMPT.md",
    "docs/subagent_roles.md",
    "artifacts/scripts/Invoke-GeminiAgent.ps1",
    "template/CLAUDE.md",
    "template/BOOTSTRAP_PROMPT.md",
    "template/docs/subagent_roles.md",
    "template/artifacts/scripts/Invoke-GeminiAgent.ps1",
)

ALLOWED_GEMINI_MODELS = {
    "gemini-3.1-flash-lite-preview",
    "gemini-3-flash-preview",
    "gemini-3.1-pro-preview",
}

DISALLOWED_GEMINI_FRAGMENTS = (
    "gemini-2.0",
    "gemini-2.5",
    "gemini 2.0",
    "gemini 2.5",
    "2.0-flash",
    "2.5-flash",
)

README_HEADERS_EN = [
    "Start Here",
    "Product Positioning",
    "Why This Project Exists",
    "Core Capabilities",
    "Product Highlights",
    "Use Cases",
    "Workflow Overview",
    "Architecture Snapshot",
    "Getting Started",
    "Repository Structure",
    "Validator Commands",
    "Security And Supply-Chain Hardening",
    "Operational Notes",
    "Context System",
    "Contributing",
    "License",
]

README_HEADERS_ZH = [
    "從這裡開始",
    "產品定位",
    "為什麼是這個專案",
    "核心能力",
    "產品特色",
    "適用情境",
    "工作流總覽",
    "架構速覽",
    "開始使用",
    "儲存庫結構",
    "驗證指令",
    "安全與供應鏈強化",
    "操作備註",
    "上下文管理系統",
    "貢獻指引",
    "授權條款",
]

OBSIDIAN_HEADERS = [
    "文件語言規範",
    "建議閱讀順序",
    "導覽目錄",
    "同步範圍",
    "Workflow 摘要",
    "Decision Registry",
    "GitHub / Template 對應",
]

README_CONTRACTS: Dict[str, Dict[str, dict[str, object]]] = {
    SOURCE_REPO_MODE: {
        "README.md": {
            "headers": README_HEADERS_EN,
            "sections": {
                "Architecture Snapshot": {
                    "required": ("template/ + .github/ + OBSIDIAN.md + external/",),
                },
                "Getting Started": {
                    "required": ("source template repo", ".consilium-source-repo", "downstream terminal repo"),
                },
                "Validator Commands": {
                    "required": ("source mode checks root ↔ template ↔ Obsidian",),
                },
            },
        },
        "README.zh-TW.md": {
            "headers": README_HEADERS_ZH,
            "sections": {
                "架構速覽": {
                    "required": ("template/ + .github/ + OBSIDIAN.md + external/",),
                },
                "開始使用": {
                    "required": ("source template repo", ".consilium-source-repo", "downstream terminal repo"),
                },
                "驗證指令": {
                    "required": ("source mode 檢查 root ↔ template ↔ Obsidian",),
                },
            },
        },
        "template/README.md": {
            "headers": README_HEADERS_EN,
            "sections": {
                "Architecture Snapshot": {
                    "required": (".github/ + OBSIDIAN.md + external/",),
                    "forbidden": ("template/ + .github/ + OBSIDIAN.md + external/",),
                },
                "Getting Started": {
                    "required": ("downstream terminal repo", "nested `template/`"),
                    "forbidden": (".consilium-source-repo",),
                },
                "Validator Commands": {
                    "required": ("downstream mode checks root ↔ Obsidian",),
                },
            },
        },
        "template/README.zh-TW.md": {
            "headers": README_HEADERS_ZH,
            "sections": {
                "架構速覽": {
                    "required": (".github/ + OBSIDIAN.md + external/",),
                    "forbidden": ("template/ + .github/ + OBSIDIAN.md + external/",),
                },
                "開始使用": {
                    "required": ("downstream terminal repo", "nested `template/`"),
                    "forbidden": (".consilium-source-repo",),
                },
                "驗證指令": {
                    "required": ("downstream mode 檢查 root ↔ Obsidian",),
                },
            },
        },
    },
    DOWNSTREAM_REPO_MODE: {
        "README.md": {
            "headers": README_HEADERS_EN,
            "sections": {
                "Architecture Snapshot": {
                    "required": (".github/ + OBSIDIAN.md + external/",),
                    "forbidden": ("template/ + .github/ + OBSIDIAN.md + external/",),
                },
                "Getting Started": {
                    "required": ("downstream terminal repo", "nested `template/`"),
                    "forbidden": (".consilium-source-repo",),
                },
                "Validator Commands": {
                    "required": ("downstream mode checks root ↔ Obsidian",),
                    "forbidden": ("source mode checks root ↔ template ↔ Obsidian",),
                },
            },
        },
        "README.zh-TW.md": {
            "headers": README_HEADERS_ZH,
            "sections": {
                "架構速覽": {
                    "required": (".github/ + OBSIDIAN.md + external/",),
                    "forbidden": ("template/ + .github/ + OBSIDIAN.md + external/",),
                },
                "開始使用": {
                    "required": ("downstream terminal repo", "nested `template/`"),
                    "forbidden": (".consilium-source-repo",),
                },
                "驗證指令": {
                    "required": ("downstream mode 檢查 root ↔ Obsidian",),
                    "forbidden": ("source mode 檢查 root ↔ template ↔ Obsidian",),
                },
            },
        },
    },
}

OBSIDIAN_CONTRACTS: Dict[str, Dict[str, dict[str, object]]] = {
    SOURCE_REPO_MODE: {
        "OBSIDIAN.md": {
            "headers": OBSIDIAN_HEADERS,
            "sections": {
                "同步範圍": {
                    "required": ("source template repo", "template 對應文件", "downstream terminal repo"),
                },
                "Workflow 摘要": {
                    "required": (
                        "source template repo 的 workflow 規則變更後，必須同步更新 root、`template/` 與 Obsidian 入口，並通過 contract guard。",
                        "downstream terminal repo 的 workflow 規則變更後，只維護 root 文件與 `OBSIDIAN.md`，並通過 contract guard。",
                    ),
                },
                "GitHub / Template 對應": {
                    "required": ("template/START_HERE.md", "template/OBSIDIAN.md"),
                },
            },
        },
        "template/OBSIDIAN.md": {
            "headers": OBSIDIAN_HEADERS,
            "sections": {
                "同步範圍": {
                    "required": ("只維護 root 文件與 `OBSIDIAN.md`", "不再建立新的 `template/`"),
                    "forbidden": ("template 對應文件",),
                },
                "Workflow 摘要": {
                    "required": ("downstream terminal repo 的 workflow 規則變更後，只維護 root 文件與 `OBSIDIAN.md`，並通過 contract guard。",),
                    "forbidden": ("必須同步更新 root、`template/` 與 Obsidian 入口",),
                },
                "GitHub / Template 對應": {
                    "required": ("本 repo 不建立 nested `template/`",),
                    "forbidden": ("template/START_HERE.md", "template/OBSIDIAN.md"),
                },
            },
        },
    },
    DOWNSTREAM_REPO_MODE: {
        "OBSIDIAN.md": {
            "headers": OBSIDIAN_HEADERS,
            "sections": {
                "同步範圍": {
                    "required": ("只維護 root 文件與 `OBSIDIAN.md`", "不再建立新的 `template/`"),
                    "forbidden": ("template 對應文件",),
                },
                "Workflow 摘要": {
                    "required": ("downstream terminal repo 的 workflow 規則變更後，只維護 root 文件與 `OBSIDIAN.md`，並通過 contract guard。",),
                    "forbidden": ("必須同步更新 root、`template/` 與 Obsidian 入口",),
                },
                "GitHub / Template 對應": {
                    "required": ("本 repo 不建立 nested `template/`",),
                    "forbidden": ("template/START_HERE.md", "template/OBSIDIAN.md"),
                },
            },
        },
    },
}

def load_text(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def normalize_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n")
    for pattern, replacement in PLACEHOLDER_PATTERNS:
        normalized = re.sub(pattern, replacement, normalized)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    return normalized.strip()


def detect_repo_mode(root: Path) -> str:
    sentinel_path = root / SOURCE_REPO_SENTINEL
    return SOURCE_REPO_MODE if sentinel_path.exists() else DOWNSTREAM_REPO_MODE


def required_phrases_for_mode(mode: str) -> Dict[str, Sequence[str]]:
    if mode == SOURCE_REPO_MODE:
        return {**COMMON_REQUIRED_PHRASES, **SOURCE_REQUIRED_PHRASES}
    return {
        **{
            rel: phrases
            for rel, phrases in COMMON_REQUIRED_PHRASES.items()
            if not rel.startswith("template/")
        },
        **DOWNSTREAM_REQUIRED_PHRASES,
    }


def validate_exact_sync(root: Path) -> List[str]:
    if detect_repo_mode(root) == DOWNSTREAM_REPO_MODE:
        return []
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
    phrase_map = required_phrases_for_mode(detect_repo_mode(root))
    errors: List[str] = []
    for relative, phrases in phrase_map.items():
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


def validate_repository_profile(root: Path) -> List[str]:
    mode = detect_repo_mode(root)
    errors: List[str] = []
    profile_files = (
        REPOSITORY_PROFILE_FILES
        if mode == SOURCE_REPO_MODE
        else (".github/repository-profile.json",)
    )
    for relative in profile_files:
        path = root / relative
        if not path.exists():
            errors.append(f"Missing required repository profile: {relative}")
            continue
        try:
            profile = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            errors.append(f"{relative} is not valid JSON: {exc}")
            continue

        about = profile.get("about")
        topics = profile.get("topics")

        if not isinstance(about, str) or not about.strip():
            errors.append(f"{relative} must define non-empty string field 'about'")
        else:
            about_len = len(about.strip())
            if about_len < 80 or about_len > 200:
                errors.append(f"{relative} field 'about' must be 80-200 chars, got {about_len}")

        if not isinstance(topics, list):
            errors.append(f"{relative} must define list field 'topics'")
            continue
        normalized_topics = [str(topic).strip() for topic in topics]
        if len(normalized_topics) < 6 or len(normalized_topics) > 12:
            errors.append(f"{relative} field 'topics' must contain 6-12 items, got {len(normalized_topics)}")
        if len(set(normalized_topics)) != len(normalized_topics):
            errors.append(f"{relative} field 'topics' must not contain duplicates")
        invalid_topics = [topic for topic in normalized_topics if not TOPIC_PATTERN.match(topic)]
        if invalid_topics:
            errors.append(f"{relative} has invalid topics (must be lowercase-kebab-case): {invalid_topics}")
        missing_required_topics = sorted(REQUIRED_TOPICS - set(normalized_topics))
        if missing_required_topics:
            errors.append(f"{relative} missing required topics: {missing_required_topics}")
    return errors


def extract_h2_headers(text: str) -> list[str]:
    """Extract all H2 headers (lines starting with ##) from markdown text."""
    return [title for title, _ in parse_h2_sections(text)]


def parse_h2_sections(text: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    current_title: str | None = None
    current_body: list[str] = []
    in_code_fence = False

    for line in text.replace("\r\n", "\n").split("\n"):
        if line.startswith("```"):
            in_code_fence = not in_code_fence
        if not in_code_fence and line.startswith("## "):
            if current_title is not None:
                sections.append((current_title, "\n".join(current_body).strip()))
            current_title = line[3:].strip()
            current_body = []
            continue
        if current_title is not None:
            current_body.append(line)

    if current_title is not None:
        sections.append((current_title, "\n".join(current_body).strip()))
    return sections


def squeeze_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def contains_phrase(text: str, phrase: str) -> bool:
    return squeeze_whitespace(phrase) in squeeze_whitespace(text)


def validate_section_contract(
    relative: str,
    text: str,
    expected_headers: Sequence[str],
    section_rules: dict[str, object],
) -> List[str]:
    errors: List[str] = []
    sections = parse_h2_sections(text)
    actual_headers = [title for title, _ in sections]
    if actual_headers != list(expected_headers):
        errors.append(f"{relative} H2 order mismatch: expected {list(expected_headers)}, got {actual_headers}")

    section_map = {title: body for title, body in sections}
    for section_name, raw_rule in section_rules.items():
        body = section_map.get(section_name)
        if body is None:
            errors.append(f"{relative} missing required section: {section_name}")
            continue
        rules = raw_rule if isinstance(raw_rule, dict) else {}
        for phrase in rules.get("required", ()):
            if not contains_phrase(body, phrase):
                errors.append(f"{relative} section '{section_name}' missing required phrase: {phrase}")
        for phrase in rules.get("forbidden", ()):
            if contains_phrase(body, phrase):
                errors.append(f"{relative} section '{section_name}' contains forbidden phrase: {phrase}")
    return errors


def validate_markdown_contracts(root: Path) -> List[str]:
    mode = detect_repo_mode(root)
    errors: List[str] = []

    for contract_group in (README_CONTRACTS[mode], OBSIDIAN_CONTRACTS[mode]):
        for relative, contract in contract_group.items():
            path = root / relative
            if not path.exists():
                errors.append(f"Missing required file: {relative}")
                continue
            text = load_text(path)
            headers = contract.get("headers", [])
            section_rules = contract.get("sections", {})
            errors.extend(
                validate_section_contract(
                    relative,
                    text,
                    headers if isinstance(headers, list) else [],
                    section_rules if isinstance(section_rules, dict) else {},
                )
            )
    return errors


def validate_readme_structure(root: Path) -> List[str]:
    """Validate README bilingual structure alongside the section-level contract."""
    mode = detect_repo_mode(root)
    errors: List[str] = []

    readme_en = root / "README.md"
    readme_zh = root / "README.zh-TW.md"

    if not readme_en.exists():
        errors.append("Missing README.md in root")
    if not readme_zh.exists():
        errors.append("Missing README.zh-TW.md in root")

    if readme_en.exists() and readme_zh.exists():
        en_headers = extract_h2_headers(readme_en.read_text(encoding="utf-8"))
        zh_headers = extract_h2_headers(readme_zh.read_text(encoding="utf-8"))
        if len(en_headers) != len(zh_headers):
            errors.append(
                f"README structure mismatch in root: EN has {len(en_headers)} sections vs ZH has {len(zh_headers)} sections"
            )

    if mode == SOURCE_REPO_MODE:
        template_readme_en = root / "template" / "README.md"
        template_readme_zh = root / "template" / "README.zh-TW.md"

        if not template_readme_en.exists():
            errors.append("Missing README.md in template")
        if not template_readme_zh.exists():
            errors.append("Missing README.zh-TW.md in template")

        if template_readme_en.exists() and template_readme_zh.exists():
            template_en_headers = extract_h2_headers(template_readme_en.read_text(encoding="utf-8"))
            template_zh_headers = extract_h2_headers(template_readme_zh.read_text(encoding="utf-8"))
            if len(template_en_headers) != len(template_zh_headers):
                errors.append(
                    f"README structure mismatch in template: EN has {len(template_en_headers)} sections vs ZH has {len(template_zh_headers)} sections"
                )

    return errors


def validate_allowed_gemini_models(root: Path) -> List[str]:
    errors: List[str] = []
    model_pattern = re.compile(r"\bgemini-[a-z0-9.\-]+\b", re.IGNORECASE)

    for relative in ACTIVE_GEMINI_POLICY_FILES:
        path = root / relative
        if not path.exists():
            continue
        text = load_text(path)
        lowered = text.lower()
        for fragment in DISALLOWED_GEMINI_FRAGMENTS:
            if fragment in lowered:
                errors.append(f"{relative} contains disallowed Gemini model fragment: {fragment}")
        referenced_models = {match.group(0).lower() for match in model_pattern.finditer(text)}
        for model in sorted(referenced_models):
            if model not in ALLOWED_GEMINI_MODELS:
                errors.append(f"{relative} contains unsupported Gemini model reference: {model}")

    return errors


def validate_workflow_policy_contract() -> List[str]:
    return validate_workflow_rule_tables()


def validate_root_artifact_strictness(root: Path) -> List[str]:
    errors: List[str] = []
    artifact_roots = {
        "task": root / "artifacts" / "tasks",
        "decision": root / "artifacts" / "decisions",
        "improvement": root / "artifacts" / "improvement",
        "verify": root / "artifacts" / "verify",
    }
    for artifact_type, directory in artifact_roots.items():
        if not directory.exists():
            continue
        for path in sorted(directory.glob("TASK-*.*.md")):
            task_id = path.name.split(".", 1)[0]
            result = gsv.validate_markdown_artifact(path, artifact_type, task_id)
            for error in result.errors:
                errors.append(f"{path.relative_to(root).as_posix()}: {error}")
            for warning in result.warnings:
                errors.append(f"{path.relative_to(root).as_posix()}: root strictness forbids warning: {warning}")

    status_dir = root / "artifacts" / "status"
    if status_dir.exists():
        for path in sorted(status_dir.glob("TASK-*.status.json")):
            task_id = path.name.split(".", 1)[0]
            payload = json.loads(path.read_text(encoding="utf-8"))
            result = gsv.validate_status_schema(payload, task_id)
            for error in result.errors:
                errors.append(f"{path.relative_to(root).as_posix()}: {error}")
            for warning in result.warnings:
                errors.append(f"{path.relative_to(root).as_posix()}: root strictness forbids warning: {warning}")
    return errors


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate workflow sync contracts across README, Obsidian, root, and template docs.")
    parser.add_argument("--root", default=".", help="Repository root. Default: current directory")
    parser.add_argument("--check-readme", action="store_true", help="Validate README section contract plus bilingual H2 structure consistency")
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    errors = validate_exact_sync(root)
    errors.extend(validate_required_phrases(root))
    errors.extend(validate_markdown_contracts(root))
    errors.extend(validate_prompt_case_sync(root))
    errors.extend(validate_repository_profile(root))
    errors.extend(validate_allowed_gemini_models(root))
    errors.extend(validate_workflow_policy_contract())
    errors.extend(validate_root_artifact_strictness(root))
    
    if args.check_readme:
        errors.extend(validate_readme_structure(root))

    if errors:
        print("[ERROR] Contract validation failed")
        for error in errors:
            print(f"[FAIL] {error}")
        return 1

    print("[OK] Contract validation passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
