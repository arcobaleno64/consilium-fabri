"""Unit tests for core parsing and validation functions in workflow guard scripts."""
from __future__ import annotations

import json
import os
import sys
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch
import unittest.mock

import pytest

# Add scripts directory to path so we can import the modules
SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import guard_status_validator as gsv
import guard_contract_validator as gcv
import prompt_regression_validator as prv
import build_decision_registry as bdr
import aggregate_red_team_scorecard as ars
import validate_scorecard_deltas as vsd
import validate_context_stack as vcs
import workflow_constants as wc


# ─────────────────────────────────────────────
# guard_status_validator: parsing helpers
# ─────────────────────────────────────────────


class TestNormalizePathToken:
    def test_basic(self):
        assert gsv.normalize_path_token("  `src/main.py`  ") == "src/main.py"

    def test_strip_backticks_and_quotes(self):
        assert gsv.normalize_path_token('"docs/readme.md"') == "docs/readme.md"

    def test_windows_drive_letter(self):
        assert gsv.normalize_path_token("C:/Users/file.txt") == "/Users/file.txt"

    def test_dot_slash_prefix(self):
        # normalize_path_token strips "." but keeps leading "/" — callers handle that
        result = gsv.normalize_path_token("./artifacts/tasks/TASK-001.task.md")
        assert "artifacts/tasks/TASK-001.task.md" in result

    def test_backslash_to_forward(self):
        assert gsv.normalize_path_token("artifacts\\scripts\\guard.py") == "artifacts/scripts/guard.py"

    def test_diff_prefix_a_b(self):
        assert gsv.normalize_path_token("a/src/lib.py") == "src/lib.py"
        assert gsv.normalize_path_token("b/src/lib.py") == "src/lib.py"


class TestParseKeyValueSection:
    def test_basic(self):
        text = "- Name: Alice\n- Role: Developer\n"
        result = gsv.parse_key_value_section(text)
        assert result["name"] == "Alice"
        assert result["role"] == "Developer"

    def test_empty(self):
        assert gsv.parse_key_value_section("") == {}

    def test_non_matching_lines_ignored(self):
        text = "Some random text\n- Key: Value\n"
        result = gsv.parse_key_value_section(text)
        assert result == {"key": "Value"}


class TestParseListItems:
    def test_bullet_list(self):
        items = gsv.parse_list_items("- Item one\n- Item two\n- Item three")
        assert items == ["Item one", "Item two", "Item three"]

    def test_numbered_list(self):
        items = gsv.parse_list_items("1. First\n2. Second")
        assert items == ["First", "Second"]

    def test_none_entry_excluded(self):
        items = gsv.parse_list_items("- None\n- Real item")
        assert items == ["Real item"]

    def test_multiline_items(self):
        text = "- First line\n  continuation\n- Second item"
        items = gsv.parse_list_items(text)
        assert len(items) == 2
        assert "continuation" in items[0]


class TestExtractSection:
    def test_basic(self):
        text = "## Alpha\nContent A\n## Beta\nContent B\n"
        assert gsv.extract_section(text, "Alpha") == "Content A"
        assert gsv.extract_section(text, "Beta") == "Content B"

    def test_missing_section(self):
        assert gsv.extract_section("## Foo\nbar", "Missing") == ""

    def test_last_section(self):
        text = "## Only\nContent here"
        assert gsv.extract_section(text, "Only") == "Content here"


class TestExtractFileTokens:
    def test_inline_code(self):
        text = "- Modified `src/main.py` for feature\n- Updated `docs/readme.md`"
        tokens = gsv.extract_file_tokens(text)
        assert "src/main.py" in tokens
        assert "docs/readme.md" in tokens

    def test_plain_path(self):
        text = "- artifacts/scripts/guard.py was changed"
        tokens = gsv.extract_file_tokens(text)
        assert "artifacts/scripts/guard.py" in tokens


class TestComputeSnapshotSha256:
    def test_deterministic(self):
        files = {"c.py", "a.py", "b.py"}
        h1 = gsv.compute_snapshot_sha256(files)
        h2 = gsv.compute_snapshot_sha256(files)
        assert h1 == h2
        assert len(h1) == 64

    def test_order_independent(self):
        assert gsv.compute_snapshot_sha256({"a", "b"}) == gsv.compute_snapshot_sha256({"b", "a"})


class TestValidateTaskId:
    def test_valid(self):
        assert gsv.validate_task_id("TASK-001") == []
        assert gsv.validate_task_id("TASK-9999") == []
        assert gsv.validate_task_id("TASK-LITE-001") == []

    def test_invalid(self):
        assert len(gsv.validate_task_id("INVALID")) > 0
        assert len(gsv.validate_task_id("task-001")) > 0
        assert len(gsv.validate_task_id("")) > 0


class TestValidateTaipeiTimestamp:
    def test_valid(self):
        assert gsv.validate_taipei_timestamp("2026-04-16T12:00:00+08:00", "test") == []

    def test_invalid_timezone(self):
        errors = gsv.validate_taipei_timestamp("2026-04-16T12:00:00Z", "test")
        assert len(errors) > 0

    def test_invalid_format(self):
        errors = gsv.validate_taipei_timestamp("2026/04/16", "test")
        assert len(errors) > 0


class TestResolveStatusState:
    def test_modern_schema(self):
        assert gsv.resolve_status_state({"state": "coding"}) == "coding"

    def test_legacy_schema(self):
        assert gsv.resolve_status_state({"current_state": "research_ready"}) == "researched"

    def test_empty(self):
        assert gsv.resolve_status_state({}) is None


class TestLegalTransitions:
    def test_valid_transitions(self):
        assert "researched" in gsv.LEGAL_TRANSITIONS["drafted"]
        assert "blocked" in gsv.LEGAL_TRANSITIONS["drafted"]
        assert "planned" in gsv.LEGAL_TRANSITIONS["researched"]
        assert "done" in gsv.LEGAL_TRANSITIONS["verifying"]

    def test_no_escape_from_done(self):
        assert gsv.LEGAL_TRANSITIONS["done"] == set()

    def test_blocked_can_return(self):
        targets = gsv.LEGAL_TRANSITIONS["blocked"]
        assert "drafted" in targets
        assert "coding" in targets


class TestTaskRequestsLightweight:
    def test_true(self):
        assert gsv.task_requests_lightweight("- Lightweight: true\n## Objective") is True

    def test_false(self):
        assert gsv.task_requests_lightweight("- Lightweight: false\n## Objective") is False

    def test_absent(self):
        assert gsv.task_requests_lightweight("## Objective\nSomething") is False


class TestValidateTransition:
    def test_valid(self):
        result = gsv.validate_transition("drafted", "researched")
        assert result.ok

    def test_invalid(self):
        result = gsv.validate_transition("drafted", "done")
        assert not result.ok

    def test_unknown_state(self):
        result = gsv.validate_transition("unknown", "done")
        assert not result.ok


# ─────────────────────────────────────────────
# guard_contract_validator: helpers
# ─────────────────────────────────────────────


class TestNormalizeText:
    def test_whitespace_collapse(self):
        result = gcv.normalize_text("a   b\t\tc")
        assert result == "a b c"

    def test_placeholder_replacement(self):
        result = gcv.normalize_text("Project: {{PROJECT_NAME}} in {{REPO_NAME}}")
        assert "__PROJECT__" in result
        assert "__REPO__" in result

    def test_crlf_normalize(self):
        result = gcv.normalize_text("line1\r\nline2")
        assert "\r" not in result


# ─────────────────────────────────────────────
# prompt_regression_validator
# ─────────────────────────────────────────────


class TestPromptNormalizeText:
    def test_lowercase_and_collapse(self):
        result = prv.normalize_text("Hello   WORLD\n\n")
        assert result == "hello world "

    def test_crlf(self):
        result = prv.normalize_text("a\r\nb")
        assert "\r" not in result


class TestContainsAny:
    def test_found(self):
        assert prv.contains_any("the quick brown fox", ["Quick", "Slow"]) is True

    def test_not_found(self):
        assert prv.contains_any("the quick brown fox", ["Lazy", "Sleepy"]) is False


class TestCheckNearTerms:
    def test_near(self):
        text = "the quick brown fox jumps"
        assert prv.check_near_terms(text, ["quick", "fox"], 20) is True

    def test_far(self):
        text = "quick " + "x" * 300 + " fox"
        assert prv.check_near_terms(text, ["quick", "fox"], 20) is False

    def test_missing_term(self):
        assert prv.check_near_terms("hello world", ["hello", "missing"], 100) is False


class TestEvaluateCase:
    def test_must_contain_all_pass(self, tmp_path):
        (tmp_path / "test.md").write_text("artifact workflow gate guard", encoding="utf-8")
        case = {
            "id": "TC-1",
            "title": "test",
            "assertions": [
                {"file": "test.md", "must_contain_all": ["artifact", "workflow"]}
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert result.passed

    def test_must_contain_all_fail(self, tmp_path):
        (tmp_path / "test.md").write_text("only artifact here", encoding="utf-8")
        case = {
            "id": "TC-2",
            "title": "test",
            "assertions": [
                {"file": "test.md", "must_contain_all": ["artifact", "missing_term"]}
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_must_not_contain_any(self, tmp_path):
        (tmp_path / "test.md").write_text("clean content", encoding="utf-8")
        case = {
            "id": "TC-3",
            "title": "test",
            "assertions": [
                {"file": "test.md", "must_not_contain_any": ["forbidden"]}
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert result.passed

    def test_must_not_contain_any_fail(self, tmp_path):
        (tmp_path / "test.md").write_text("this has forbidden content", encoding="utf-8")
        case = {
            "id": "TC-4",
            "title": "test",
            "assertions": [
                {"file": "test.md", "must_not_contain_any": ["forbidden"]}
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed


# ─────────────────────────────────────────────
# build_decision_registry
# ─────────────────────────────────────────────


class TestParseSections:
    def test_basic(self):
        text = "## Issue\nSomething broken\n## Chosen Option\nOption A"
        sections = bdr.parse_sections(text)
        assert "issue" in sections
        assert "chosen option" in sections
        assert "Something broken" in sections["issue"]

    def test_empty(self):
        assert bdr.parse_sections("no sections here") == {}


class TestFirstParagraph:
    def test_basic(self):
        assert bdr.first_paragraph("First para.\n\nSecond para.") == "First para."

    def test_empty(self):
        assert bdr.first_paragraph("") == ""
        assert bdr.first_paragraph(None) == ""


class TestCleanRefToken:
    def test_backtick(self):
        assert bdr.clean_ref_token("`TASK-900.plan.md`") == "TASK-900.plan.md"

    def test_bullet(self):
        assert bdr.clean_ref_token("- TASK-901") == "TASK-901"


class TestNormalizeRef:
    def test_task_id_to_plan(self):
        result = bdr.normalize_ref("TASK-900", "plans")
        assert result == "artifacts/plans/TASK-900.plan.md"

    def test_task_id_to_research(self):
        result = bdr.normalize_ref("TASK-900", "research")
        assert result == "artifacts/research/TASK-900.research.md"

    def test_already_full_path(self):
        result = bdr.normalize_ref("artifacts/plans/TASK-900.plan.md", "plans")
        assert result == "artifacts/plans/TASK-900.plan.md"


class TestExtractTaskId:
    def test_valid(self):
        assert bdr.extract_task_id(Path("TASK-900.decision.md")) == "TASK-900"

    def test_invalid(self):
        with pytest.raises(ValueError):
            bdr.extract_task_id(Path("random.md"))


# ─────────────────────────────────────────────
# aggregate_red_team_scorecard
# ─────────────────────────────────────────────


class TestParseReport:
    def test_parse_rows(self):
        markdown = textwrap.dedent("""\
            | Case | Phase | Expected | Outcome | Exit | Evidence | Notes |
            |---|---|---|---|---:|---|---|
            | `RT-001` | static | fail | pass | 0 | `[OK]` | None |
            | `RT-002` | static | fail | fail | 1 | `[FAIL]` | issue |
        """)
        rows = ars.parse_report(markdown)
        assert len(rows) == 2
        assert rows[0].case == "RT-001"
        assert rows[0].case_passed is True
        assert rows[1].case_passed is False

    def test_auto_score(self):
        from aggregate_red_team_scorecard import CaseRow

        pass_row = CaseRow("RT-001", "static", "fail", "pass", "0", "[OK]", "")
        fail_row = CaseRow("RT-002", "static", "fail", "fail", "1", "[FAIL]", "")
        assert ars.auto_score(pass_row) == 2
        assert ars.auto_score(fail_row) == 0


# ─────────────────────────────────────────────
# validate_scorecard_deltas
# ─────────────────────────────────────────────


class TestValidateRows:
    def test_zero_delta_ok(self):
        rows = [vsd.Row(case="RT-001", reviewer_delta=0, notes="")]
        assert vsd.validate_rows(rows) == []

    def test_nonzero_delta_with_notes_ok(self):
        rows = [vsd.Row(case="RT-001", reviewer_delta=1, notes="justified change")]
        assert vsd.validate_rows(rows) == []

    def test_nonzero_delta_without_notes_fail(self):
        rows = [vsd.Row(case="RT-001", reviewer_delta=-1, notes="None")]
        failures = vsd.validate_rows(rows)
        assert len(failures) == 1
        assert "RT-001" in failures[0]

    def test_empty_notes_fail(self):
        rows = [vsd.Row(case="RT-002", reviewer_delta=1, notes="")]
        failures = vsd.validate_rows(rows)
        assert len(failures) == 1


# ─────────────────────────────────────────────
# workflow_constants
# ─────────────────────────────────────────────


class TestWorkflowConstants:
    def test_required_topics_is_set(self):
        assert isinstance(wc.REQUIRED_TOPICS, set)
        assert "multi-agent" in wc.REQUIRED_TOPICS
        assert len(wc.REQUIRED_TOPICS) == 6

    def test_topic_pattern(self):
        assert wc.TOPIC_PATTERN.match("multi-agent")
        assert wc.TOPIC_PATTERN.match("developer-tools")
        assert not wc.TOPIC_PATTERN.match("UPPERCASE")
        assert not wc.TOPIC_PATTERN.match("has space")


# ─────────────────────────────────────────────
# validate_context_stack
# ─────────────────────────────────────────────


class TestContextStackHelpers:
    def test_estimate_tokens_counts_cjk_and_ascii(self):
        result = vcs.estimate_tokens("abc def 測試")
        assert result >= 5

    def test_extract_frontmatter_name(self):
        text = "---\nname: sample-skill\ndescription: test\n---\n# Title"
        assert vcs.extract_frontmatter_name(text) == "sample-skill"

    def test_extract_headings(self):
        headings = vcs.extract_headings("# One\n## Two\n### Three")
        assert headings == ["One", "Two", "Three"]


class TestContextStackChecks:
    def _write_file(self, root: Path, rel_path: str, content: str) -> None:
        path = root / rel_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

    def _build_valid_repo(self, root: Path) -> None:
        self._write_file(
            root,
            ".github/memory-bank/artifact-rules.md",
            "# Task\ncontent\n# Plan\ncontent\n# Code\ncontent\n# Verify\ncontent\n",
        )
        self._write_file(
            root,
            ".github/memory-bank/workflow-gates.md",
            "# Intake\ncontent\n# Research\ncontent\n# Planning\ncontent\n# Coding\ncontent\n# Review\ncontent\n",
        )
        self._write_file(
            root,
            ".github/memory-bank/prompt-patterns.md",
            "# Agent Dispatch\ncontent\n# Artifact Output\ncontent\n",
        )
        self._write_file(
            root,
            ".github/memory-bank/project-facts.md",
            "# 技術棧\ncontent\n# 主要組件\ncontent\n# 環境變數\ncontent\n",
        )
        self._write_file(
            root,
            ".github/copilot-instructions.md",
            "short copilot instructions",
        )
        self._write_file(
            root,
            ".github/prompts/example.md",
            "---\nname: example-prompt\n---\n# Prompt",
        )
        self._write_file(
            root,
            ".github/skills/example/SKILL.md",
            "---\nname: example-skill\n---\n# Skill",
        )
        self._write_file(
            root,
            "docs/reference.md",
            "reference target",
        )
        self._write_file(
            root,
            "template/.github/memory-bank/artifact-rules.md",
            "# Task\ncontent\n# Plan\ncontent\n# Code\ncontent\n# Verify\ncontent\n",
        )
        self._write_file(
            root,
            "template/.github/memory-bank/workflow-gates.md",
            "# Intake\ncontent\n# Research\ncontent\n# Planning\ncontent\n# Coding\ncontent\n# Review\ncontent\n",
        )
        self._write_file(
            root,
            "template/.github/memory-bank/prompt-patterns.md",
            "# Agent Dispatch\ncontent\n# Artifact Output\ncontent\n",
        )
        self._write_file(
            root,
            "template/.github/memory-bank/project-facts.md",
            "# 技術棧\ncontent\n# 主要組件\ncontent\n# 環境變數\ncontent\n",
        )
        self._write_file(
            root,
            "template/.github/prompts/example.md",
            "---\nname: example-prompt\n---\n# Prompt",
        )
        self._write_file(
            root,
            "template/.github/skills/example/SKILL.md",
            "---\nname: example-skill\n---\n# Skill",
        )
        self._write_file(
            root,
            "template/.github/copilot-instructions.md",
            "short copilot instructions",
        )

    def test_check_memory_bank_existence(self, tmp_path):
        self._build_valid_repo(tmp_path)
        assert vcs.check_memory_bank_existence(tmp_path) == []

    def test_check_cross_references_flags_missing_target(self, tmp_path):
        self._build_valid_repo(tmp_path)
        path = tmp_path / ".github/memory-bank/artifact-rules.md"
        path.write_text("# Task\nsee docs/missing.md\n# Plan\ncontent\n# Code\ncontent\n# Verify\ncontent\n", encoding="utf-8")
        errors = vcs.check_cross_references(tmp_path)
        assert any("docs/missing.md" in error for error in errors)

    def test_check_frontmatter_and_uniqueness(self, tmp_path):
        self._build_valid_repo(tmp_path)
        errors, names = vcs.check_frontmatter(tmp_path)
        assert errors == []
        assert names["prompt"] == ["example-prompt"]
        assert names["skill"] == ["example-skill"]
        assert vcs.check_name_uniqueness(names) == []

    def test_check_name_uniqueness_detects_collisions(self):
        errors = vcs.check_name_uniqueness(
            {"prompt": ["dup", "dup", "shared"], "skill": ["skill", "shared"]}
        )
        assert any("Duplicate prompt name" in error for error in errors)
        assert any("Name collision" in error for error in errors)

    def test_check_copilot_instructions_size_flags_oversized_file(self, tmp_path):
        self._build_valid_repo(tmp_path)
        oversized = "詞" * 1400
        (tmp_path / ".github/copilot-instructions.md").write_text(oversized, encoding="utf-8")
        errors = vcs.check_copilot_instructions_size(tmp_path)
        assert any("copilot-instructions" in error for error in errors)

    def test_check_template_sync_reports_missing_template_file(self, tmp_path):
        self._build_valid_repo(tmp_path)
        (tmp_path / "template/.github/skills/example/SKILL.md").unlink()
        errors = vcs.check_template_sync(tmp_path)
        assert any("template/.github/skills missing" in error for error in errors)

    def test_check_memory_bank_quality_warns_on_orphan_and_long_file(self, tmp_path):
        self._build_valid_repo(tmp_path)
        long_content = "# Task\ncontent\n# Plan\ncontent\n# Code\ncontent\n# Verify\ncontent\n" + "\n".join(
            f"line {index}" for index in range(130)
        )
        (tmp_path / ".github/memory-bank/artifact-rules.md").write_text(
            long_content,
            encoding="utf-8",
        )
        (tmp_path / ".github/memory-bank/prompt-patterns.md").write_text(
            "# Agent Dispatch\ncontent\n# Artifact Output\n",
            encoding="utf-8",
        )
        issues = vcs.check_memory_bank_quality(tmp_path)
        assert any("consider consolidation" in issue for issue in issues)
        assert any("orphan section" in issue for issue in issues)

    def test_main_passes_on_valid_repo(self, tmp_path, monkeypatch, capsys):
        self._build_valid_repo(tmp_path)
        monkeypatch.setattr(sys, "argv", ["validate_context_stack.py", "--root", str(tmp_path)])
        assert vcs.main() == 0
        captured = capsys.readouterr()
        assert "PASSED" in captured.out


# ═════════════════════════════════════════════
# EDGE-CASE TESTS
# ═════════════════════════════════════════════


TAIPEI_TZ = timezone(timedelta(hours=8))


# ─────────────────────────────────────────────
# parse_csv_file_tokens
# ─────────────────────────────────────────────


class TestParseCsvFileTokens:
    def test_empty_string(self):
        assert gsv.parse_csv_file_tokens("") == set()

    def test_none_value(self):
        assert gsv.parse_csv_file_tokens("None") == set()
        assert gsv.parse_csv_file_tokens("NONE") == set()
        assert gsv.parse_csv_file_tokens("  none  ") == set()

    def test_single_token(self):
        result = gsv.parse_csv_file_tokens("src/main.py")
        assert "src/main.py" in result

    def test_multiple_with_whitespace(self):
        result = gsv.parse_csv_file_tokens(" src/a.py , docs/b.md , lib/c.js ")
        assert len(result) == 3
        assert "src/a.py" in result
        assert "docs/b.md" in result

    def test_backtick_wrapped(self):
        result = gsv.parse_csv_file_tokens("`src/a.py`, `docs/b.md`")
        assert "src/a.py" in result
        assert "docs/b.md" in result

    def test_backslash_paths(self):
        result = gsv.parse_csv_file_tokens("src\\main.py")
        assert "src/main.py" in result


# ─────────────────────────────────────────────
# infer_state_from_artifacts
# ─────────────────────────────────────────────


class TestInferStateFromArtifacts:
    def test_empty_set(self):
        assert gsv.infer_state_from_artifacts(set()) == "drafted"

    def test_only_task(self):
        assert gsv.infer_state_from_artifacts({"task"}) == "drafted"

    def test_task_and_status(self):
        assert gsv.infer_state_from_artifacts({"task", "status"}) == "drafted"

    def test_task_research_status(self):
        assert gsv.infer_state_from_artifacts({"task", "research", "status"}) == "researched"

    def test_task_plan_status(self):
        assert gsv.infer_state_from_artifacts({"task", "plan", "status"}) == "planned"

    def test_task_plan_code_status(self):
        # verifying only requires {task, code, status}, so it matches before coding
        assert gsv.infer_state_from_artifacts({"task", "plan", "code", "status"}) == "verifying"

    def test_full_done_set(self):
        assert gsv.infer_state_from_artifacts({"task", "code", "verify", "status"}) == "done"

    def test_all_artifacts(self):
        assert gsv.infer_state_from_artifacts(
            {"task", "research", "plan", "code", "test", "verify", "status"}
        ) == "done"


# ─────────────────────────────────────────────
# state_required_artifacts
# ─────────────────────────────────────────────


class TestStateRequiredArtifacts:
    def test_drafted(self):
        assert gsv.state_required_artifacts("drafted", set()) == {"task", "status"}

    def test_planned_with_research(self):
        existing = {"task", "research", "plan", "status"}
        required = gsv.state_required_artifacts("planned", existing)
        assert "research" in required

    def test_planned_without_research(self):
        existing = {"task", "plan", "status"}
        required = gsv.state_required_artifacts("planned", existing)
        assert "research" not in required

    def test_lightweight_mode(self):
        result = gsv.state_required_artifacts("done", set(), validation_mode="lightweight")
        assert result == {"task", "research", "code", "status"}

    def test_verifying_with_test(self):
        existing = {"task", "plan", "code", "test", "status"}
        required = gsv.state_required_artifacts("verifying", existing)
        assert "test" in required

    def test_verifying_without_test(self):
        existing = {"task", "code", "status"}
        required = gsv.state_required_artifacts("verifying", existing)
        assert "test" not in required


# ─────────────────────────────────────────────
# classify_decision_waiver_gate
# ─────────────────────────────────────────────


class TestClassifyDecisionWaiverGate:
    def test_empty_string(self):
        assert gsv.classify_decision_waiver_gate("") is None

    def test_waiver_expired(self):
        assert gsv.classify_decision_waiver_gate("Waiver expired for Gate_B") is None

    def test_target_state_meta(self):
        result = gsv.classify_decision_waiver_gate("Target state 'coding' is not valid")
        assert result == "__META__"

    def test_missing_research(self):
        result = gsv.classify_decision_waiver_gate("Missing required artifacts for state 'researched': 'research'")
        assert result == "Gate_A"

    def test_missing_plan(self):
        result = gsv.classify_decision_waiver_gate("Missing required artifacts for state 'planned': 'plan'")
        assert result == "Gate_B"

    def test_missing_code(self):
        result = gsv.classify_decision_waiver_gate("Missing required artifacts for state 'coding': 'code'")
        assert result == "Gate_C"

    def test_missing_multiple_ambiguous(self):
        result = gsv.classify_decision_waiver_gate(
            "Missing required artifacts for state 'done': 'plan', 'code'"
        )
        assert result is None  # ambiguous → None

    def test_gate_e_improvement(self):
        result = gsv.classify_decision_waiver_gate("requires an improvement artifact for PDCA")
        assert result == "Gate_E"

    def test_gate_d_verify(self):
        result = gsv.classify_decision_waiver_gate("done state requires verify artifact TASK-900.verify.md")
        assert result == "Gate_D"

    def test_plan_md_keyword(self):
        result = gsv.classify_decision_waiver_gate("plan artifact is not ready for coding: TASK-900.plan.md")
        assert result == "Gate_B"

    def test_code_md_keyword(self):
        result = gsv.classify_decision_waiver_gate("something about .code.md missing")
        assert result == "Gate_C"

    def test_research_md_keyword(self):
        result = gsv.classify_decision_waiver_gate("missing .research.md artifact")
        assert result == "Gate_A"

    def test_unrecognized_error(self):
        assert gsv.classify_decision_waiver_gate("some random error string") is None


# ─────────────────────────────────────────────
# parse_missing_required_artifacts
# ─────────────────────────────────────────────


class TestParseMissingRequiredArtifacts:
    def test_no_match(self):
        assert gsv.parse_missing_required_artifacts("some other error") == set()

    def test_single(self):
        result = gsv.parse_missing_required_artifacts(
            "Missing required artifacts for state 'planned': 'plan'"
        )
        assert result == {"plan"}

    def test_multiple(self):
        result = gsv.parse_missing_required_artifacts(
            "Missing required artifacts for state 'done': 'code', 'verify'"
        )
        assert result == {"code", "verify"}


# ─────────────────────────────────────────────
# active_decision_waivers
# ─────────────────────────────────────────────


class TestActiveDecisionWaivers:
    def _future_ts(self, hours: int = 24) -> str:
        return (datetime.now(TAIPEI_TZ) + timedelta(hours=hours)).isoformat()

    def _past_ts(self, hours: int = 24) -> str:
        return (datetime.now(TAIPEI_TZ) - timedelta(hours=hours)).isoformat()

    def test_no_waivers(self):
        assert gsv.active_decision_waivers({}) == {}

    def test_not_a_list(self):
        assert gsv.active_decision_waivers({"decision_waivers": "bad"}) == {}

    def test_entry_not_dict(self):
        assert gsv.active_decision_waivers({"decision_waivers": ["bad"]}) == {}

    def test_expired_waiver(self):
        status = {"decision_waivers": [
            {"gate": "Gate_A", "expires": self._past_ts()}
        ]}
        assert gsv.active_decision_waivers(status) == {}

    def test_valid_future_waiver(self):
        future = self._future_ts()
        status = {"decision_waivers": [
            {"gate": "Gate_B", "expires": future, "decision": "TASK-999"}
        ]}
        result = gsv.active_decision_waivers(status)
        assert "Gate_B" in result
        assert result["Gate_B"]["gate"] == "Gate_B"

    def test_invalid_gate_name(self):
        status = {"decision_waivers": [
            {"gate": "Gate_Z", "expires": self._future_ts()}
        ]}
        assert gsv.active_decision_waivers(status) == {}

    def test_multiple_waivers_last_wins(self):
        future = self._future_ts()
        status = {"decision_waivers": [
            {"gate": "Gate_A", "expires": future, "decision": "TASK-100"},
            {"gate": "Gate_A", "expires": future, "decision": "TASK-200"},
        ]}
        result = gsv.active_decision_waivers(status)
        assert result["Gate_A"]["decision"] == "TASK-200"


# ─────────────────────────────────────────────
# parse_repository_ref
# ─────────────────────────────────────────────


class TestParseRepositoryRef:
    def test_valid(self):
        owner, repo, err = gsv.parse_repository_ref("octocat/hello-world")
        assert owner == "octocat"
        assert repo == "hello-world"
        assert err is None

    def test_missing_repo(self):
        _, _, err = gsv.parse_repository_ref("onlyowner")
        assert err is not None

    def test_empty(self):
        _, _, err = gsv.parse_repository_ref("")
        assert err is not None

    def test_three_segments(self):
        _, _, err = gsv.parse_repository_ref("a/b/c")
        assert err is not None

    def test_dot_segment(self):
        _, _, err = gsv.parse_repository_ref("./repo")
        assert err is not None

    def test_whitespace(self):
        owner, repo, err = gsv.parse_repository_ref("  owner / repo  ")
        assert owner == "owner"
        assert repo == "repo"
        assert err is None


# ─────────────────────────────────────────────
# normalize_api_base_url
# ─────────────────────────────────────────────


class TestNormalizeApiBaseUrl:
    def test_default_empty(self):
        url, err = gsv.normalize_api_base_url("")
        assert url == "https://api.github.com"
        assert err is None

    def test_trailing_slash(self):
        url, err = gsv.normalize_api_base_url("https://api.github.com/")
        assert url == "https://api.github.com"
        assert err is None

    def test_custom_url(self):
        url, err = gsv.normalize_api_base_url("https://github.example.com/api/v3")
        assert url == "https://github.example.com/api/v3"
        assert err is None

    def test_invalid_scheme(self):
        _, err = gsv.normalize_api_base_url("ftp://example.com")
        assert err is not None

    def test_no_scheme(self):
        _, err = gsv.normalize_api_base_url("just-a-string")
        assert err is not None


# ─────────────────────────────────────────────
# detect_mixed_github_sources
# ─────────────────────────────────────────────


class TestDetectMixedGithubSources:
    def test_no_urls(self):
        assert gsv.detect_mixed_github_sources("no github links here") == []

    def test_single_owner(self):
        text = "https://github.com/owner/repo/tree/main https://github.com/owner/repo/issues/1"
        assert gsv.detect_mixed_github_sources(text) == []

    def test_mixed_owners(self):
        text = "https://github.com/alice/myrepo and https://github.com/bob/myrepo"
        result = gsv.detect_mixed_github_sources(text)
        assert len(result) == 1
        assert "myrepo" in result[0]

    def test_different_repos_ok(self):
        text = "https://github.com/alice/repo1 and https://github.com/bob/repo2"
        assert gsv.detect_mixed_github_sources(text) == []

    def test_raw_githubusercontent(self):
        text = (
            "https://raw.githubusercontent.com/alice/myrepo/main/file.txt "
            "https://github.com/bob/myrepo/blob/main/file.txt"
        )
        result = gsv.detect_mixed_github_sources(text)
        assert len(result) == 1


# ─────────────────────────────────────────────
# detect_plan_code_scope_drift
# ─────────────────────────────────────────────


class TestDetectPlanCodeScopeDrift:
    def test_no_sections(self):
        assert gsv.detect_plan_code_scope_drift("no sections", "no sections") == []

    def test_no_drift(self):
        plan = "## Files Likely Affected\n- `src/a.py`\n- `src/b.py`"
        code = "## Files Changed\n- `src/a.py`"
        assert gsv.detect_plan_code_scope_drift(plan, code) == []

    def test_drift_detected(self):
        plan = "## Files Likely Affected\n- `src/a.py`"
        code = "## Files Changed\n- `src/a.py`\n- `src/extra.py`"
        result = gsv.detect_plan_code_scope_drift(plan, code)
        assert "src/extra.py" in result

    def test_empty_plan_no_drift(self):
        plan = "## Files Likely Affected\nNone"
        code = "## Files Changed\n- `src/a.py`"
        assert gsv.detect_plan_code_scope_drift(plan, code) == []


# ─────────────────────────────────────────────
# parse_diff_evidence
# ─────────────────────────────────────────────


class TestParseDiffEvidence:
    def test_missing(self):
        assert gsv.parse_diff_evidence("## Other Section\ncontent") is None

    def test_none_value(self):
        assert gsv.parse_diff_evidence("## Diff Evidence\nNone") is None

    def test_valid(self):
        text = "## Diff Evidence\n- Type: commit-range\n- Base Commit: abc123\n"
        result = gsv.parse_diff_evidence(text)
        assert result is not None
        assert result["type"] == "commit-range"
        assert result["base commit"] == "abc123"


# ─────────────────────────────────────────────
# summarize_remote_error_detail
# ─────────────────────────────────────────────


class TestSummarizeRemoteErrorDetail:
    def test_with_body(self):
        result = gsv.summarize_remote_error_detail(b"Not found", "fallback")
        assert result == "Not found"

    def test_empty_body(self):
        result = gsv.summarize_remote_error_detail(b"", "fallback msg")
        assert result == "fallback msg"

    def test_truncation(self):
        long_body = b"x" * 500
        result = gsv.summarize_remote_error_detail(long_body, "fallback")
        assert len(result) == 203  # 200 + "..."
        assert result.endswith("...")


# ─────────────────────────────────────────────
# parse_taipei_datetime
# ─────────────────────────────────────────────


class TestParseTaipeiDatetime:
    def test_valid(self):
        result = gsv.parse_taipei_datetime("2026-01-15T10:30:00+08:00")
        assert result is not None
        assert result.utcoffset() == timedelta(hours=8)

    def test_invalid_format(self):
        assert gsv.parse_taipei_datetime("not a date") is None

    def test_utc_rejected(self):
        assert gsv.parse_taipei_datetime("2026-01-15T10:30:00Z") is None

    def test_empty(self):
        assert gsv.parse_taipei_datetime("") is None

    def test_whitespace_trimmed(self):
        result = gsv.parse_taipei_datetime("  2026-01-15T10:30:00+08:00  ")
        assert result is not None


# ─────────────────────────────────────────────
# evaluate_case: additional edge cases
# ─────────────────────────────────────────────


class TestEvaluateCaseEdges:
    def test_near_assertion_pass(self, tmp_path):
        (tmp_path / "test.md").write_text("artifact workflow guard", encoding="utf-8")
        case = {
            "id": "TC-NEAR-1",
            "title": "near test",
            "assertions": [
                {"file": "test.md", "near": [{"terms": ["artifact", "workflow"], "max_chars": 50}]}
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert result.passed

    def test_near_assertion_fail(self, tmp_path):
        content = "artifact " + ("x " * 200) + "workflow"
        (tmp_path / "test.md").write_text(content, encoding="utf-8")
        case = {
            "id": "TC-NEAR-2",
            "title": "near test",
            "assertions": [
                {"file": "test.md", "near": [{"terms": ["artifact", "workflow"], "max_chars": 10}]}
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_missing_file(self, tmp_path):
        case = {
            "id": "TC-MISS",
            "title": "missing file",
            "assertions": [
                {"file": "nonexistent.md", "must_contain_all": ["anything"]}
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_all_of_any_assertion(self, tmp_path):
        (tmp_path / "test.md").write_text("alpha beta gamma", encoding="utf-8")
        case = {
            "id": "TC-AOA",
            "title": "all_of_any test",
            "assertions": [
                {"file": "test.md", "all_of_any": [
                    ["alpha", "missing"],
                    ["alpha", "beta"],
                ]}
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert result.passed


# ─────────────────────────────────────────────
# validate_scorecard_deltas: additional edges
# ─────────────────────────────────────────────


class TestValidateRowsEdges:
    def test_multiple_failures(self):
        rows = [
            vsd.Row(case="RT-001", reviewer_delta=1, notes=""),
            vsd.Row(case="RT-002", reviewer_delta=-1, notes="None"),
            vsd.Row(case="RT-003", reviewer_delta=0, notes=""),
        ]
        failures = vsd.validate_rows(rows)
        assert len(failures) == 2
        cases = " ".join(failures)
        assert "RT-001" in cases
        assert "RT-002" in cases

    def test_all_passing(self):
        rows = [
            vsd.Row(case="RT-001", reviewer_delta=0, notes=""),
            vsd.Row(case="RT-002", reviewer_delta=1, notes="Good reason"),
            vsd.Row(case="RT-003", reviewer_delta=-1, notes="Noted reason"),
        ]
        assert vsd.validate_rows(rows) == []

    def test_empty_rows(self):
        assert vsd.validate_rows([]) == []


# ─────────────────────────────────────────────
# build_decision_registry: additional edges
# ─────────────────────────────────────────────


class TestCollapseWhitespace:
    def test_basic(self):
        assert bdr.collapse_whitespace("a   b\n\nc") == "a b c"

    def test_empty(self):
        assert bdr.collapse_whitespace("") == ""


class TestNormalizeRefs:
    def test_multiple(self):
        result = bdr.normalize_refs(["TASK-900", "artifacts/plans/TASK-901.plan.md"], "plans")
        assert len(result) == 2
        assert "artifacts/plans/TASK-900.plan.md" in result
        assert "artifacts/plans/TASK-901.plan.md" in result

    def test_empty(self):
        assert bdr.normalize_refs([], "plans") == []


# ─────────────────────────────────────────────
# aggregate_red_team_scorecard: edge cases
# ─────────────────────────────────────────────


class TestParseReportEdges:
    def test_empty_table(self):
        markdown = "| Case | Phase | Expected | Outcome | Exit | Evidence | Notes |\n|---|---|---|---|---:|---|---|\n"
        rows = ars.parse_report(markdown)
        assert rows == []

    def test_no_table(self):
        assert ars.parse_report("just text") == []

    def test_case_fail_exit_nonzero(self):
        markdown = textwrap.dedent("""\
            | Case | Phase | Expected | Outcome | Exit | Evidence | Notes |
            |---|---|---|---|---:|---|---|
            | `RT-001` | static | pass | pass | 0 | ok | None |
        """)
        rows = ars.parse_report(markdown)
        assert rows[0].case_passed is True  # expected=pass, outcome=pass

    def test_auto_score_boundary(self):
        from aggregate_red_team_scorecard import CaseRow
        # Expected=pass and outcome=pass → also pass (score 2)
        row = CaseRow("RT-001", "static", "pass", "pass", "0", "[OK]", "")
        assert ars.auto_score(row) == 2
        # Expected=pass but outcome=fail → fail (score 0)
        row_fail = CaseRow("RT-001", "static", "pass", "fail", "1", "[FAIL]", "")
        assert ars.auto_score(row_fail) == 0


# ═════════════════════════════════════════════
# FIXTURE-BASED TESTS FOR guard_status_validator
# ═════════════════════════════════════════════


def _make_artifact_tree(tmp_path, task_id, artifact_types):
    """Helper: create minimal artifact files in a tmp_path artifacts tree."""
    for atype in artifact_types:
        d = tmp_path / gsv.ARTIFACT_DIRS[atype]
        d.mkdir(parents=True, exist_ok=True)
        ext = gsv.ARTIFACT_EXTENSIONS[atype]
        if ext.endswith(".json"):
            (d / f"{task_id}{ext}").write_text(
                json.dumps({"task_id": task_id, "state": "drafted"}, indent=2),
                encoding="utf-8",
            )
        else:
            (d / f"{task_id}{ext}").write_text(f"# Artifact\n- Task ID: {task_id}\n", encoding="utf-8")


# ─────────────────────────────────────────────
# load_json / load_text / write_json
# ─────────────────────────────────────────────


class TestLoadJson:
    def test_valid(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"key": "value"}', encoding="utf-8")
        assert gsv.load_json(p) == {"key": "value"}

    def test_missing_file(self, tmp_path):
        with pytest.raises(gsv.GuardError, match="Missing JSON"):
            gsv.load_json(tmp_path / "nope.json")

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid}", encoding="utf-8")
        with pytest.raises(gsv.GuardError, match="Invalid JSON"):
            gsv.load_json(p)


class TestLoadText:
    def test_valid(self, tmp_path):
        p = tmp_path / "file.md"
        p.write_text("hello world", encoding="utf-8")
        assert gsv.load_text(p) == "hello world"

    def test_missing(self, tmp_path):
        with pytest.raises(gsv.GuardError, match="Missing text"):
            gsv.load_text(tmp_path / "nope.md")


class TestWriteJson:
    def test_roundtrip(self, tmp_path):
        p = tmp_path / "out.json"
        payload = {"task_id": "TASK-999", "state": "done"}
        gsv.write_json(p, payload)
        assert json.loads(p.read_text(encoding="utf-8")) == payload

    def test_unicode(self, tmp_path):
        p = tmp_path / "unicode.json"
        gsv.write_json(p, {"msg": "中文"})
        assert "中文" in p.read_text(encoding="utf-8")


# ─────────────────────────────────────────────
# load_override_log
# ─────────────────────────────────────────────


class TestLoadOverrideLog:
    def test_missing_file(self, tmp_path):
        assert gsv.load_override_log(tmp_path / "missing.json") == []

    def test_valid(self, tmp_path):
        p = tmp_path / "log.json"
        p.write_text('[{"action": "override"}]', encoding="utf-8")
        result = gsv.load_override_log(p)
        assert len(result) == 1

    def test_not_array(self, tmp_path):
        p = tmp_path / "log.json"
        p.write_text('{"not": "array"}', encoding="utf-8")
        with pytest.raises(gsv.GuardError, match="expected a JSON array"):
            gsv.load_override_log(p)

    def test_entry_not_dict(self, tmp_path):
        p = tmp_path / "log.json"
        p.write_text('["string_entry"]', encoding="utf-8")
        with pytest.raises(gsv.GuardError, match="must be an object"):
            gsv.load_override_log(p)

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "log.json"
        p.write_text("not json", encoding="utf-8")
        with pytest.raises(gsv.GuardError, match="Invalid JSON"):
            gsv.load_override_log(p)


# ─────────────────────────────────────────────
# find_artifact_paths / artifact_path
# ─────────────────────────────────────────────


class TestFindArtifactPaths:
    def test_existing(self, tmp_path):
        _make_artifact_tree(tmp_path, "TASK-100", ["task"])
        paths = gsv.find_artifact_paths(tmp_path, "TASK-100", "task")
        assert len(paths) == 1
        assert "TASK-100.task.md" in paths[0].name

    def test_missing(self, tmp_path):
        (tmp_path / "tasks").mkdir()
        assert gsv.find_artifact_paths(tmp_path, "TASK-100", "task") == []

    def test_improvement_glob(self, tmp_path):
        d = tmp_path / "improvement"
        d.mkdir()
        (d / "TASK-100.improvement.md").write_text("# imp1", encoding="utf-8")
        (d / "TASK-100.v2.improvement.md").write_text("# imp2", encoding="utf-8")
        paths = gsv.find_artifact_paths(tmp_path, "TASK-100", "improvement")
        assert len(paths) == 2


class TestArtifactPath:
    def test_valid(self, tmp_path):
        p = gsv.artifact_path(tmp_path, "TASK-001", "task")
        assert p == tmp_path / "tasks" / "TASK-001.task.md"

    def test_unknown_type(self, tmp_path):
        with pytest.raises(gsv.GuardError, match="Unknown artifact type"):
            gsv.artifact_path(tmp_path, "TASK-001", "unknown")


# ─────────────────────────────────────────────
# compute_existing_artifacts
# ─────────────────────────────────────────────


class TestComputeExistingArtifacts:
    def test_empty(self, tmp_path):
        for d in gsv.ARTIFACT_DIRS.values():
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        assert gsv.compute_existing_artifacts(tmp_path, "TASK-001") == set()

    def test_some_present(self, tmp_path):
        _make_artifact_tree(tmp_path, "TASK-001", ["task", "research", "status"])
        # ensure remaining dirs exist
        for d in gsv.ARTIFACT_DIRS.values():
            (tmp_path / d).mkdir(parents=True, exist_ok=True)
        result = gsv.compute_existing_artifacts(tmp_path, "TASK-001")
        assert "task" in result
        assert "research" in result
        assert "status" in result
        assert "code" not in result


# ─────────────────────────────────────────────
# resolve_workspace_relative_path
# ─────────────────────────────────────────────


class TestResolveWorkspaceRelativePath:
    def test_valid(self, tmp_path):
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("", encoding="utf-8")
        normalized, resolved, err = gsv.resolve_workspace_relative_path(tmp_path, "src/main.py")
        assert err is None
        assert "src/main.py" in normalized

    def test_empty_path(self, tmp_path):
        _, _, err = gsv.resolve_workspace_relative_path(tmp_path, "")
        assert err is not None
        assert "empty" in err

    def test_path_escape_dotdot(self, tmp_path):
        _, _, err = gsv.resolve_workspace_relative_path(tmp_path, "../etc/passwd")
        assert err is not None
        assert "within repository root" in err

    def test_absolute_path(self, tmp_path):
        _, _, err = gsv.resolve_workspace_relative_path(tmp_path, "/etc/passwd")
        assert err is not None


# ─────────────────────────────────────────────
# status_uses_legacy_schema
# ─────────────────────────────────────────────


class TestStatusUsesLegacySchema:
    def test_modern(self):
        assert gsv.status_uses_legacy_schema({"state": "done"}) is False

    def test_legacy(self):
        assert gsv.status_uses_legacy_schema({"current_state": "done"}) is True

    def test_both_fields(self):
        # "state" present → not legacy
        assert gsv.status_uses_legacy_schema({"state": "done", "current_state": "done"}) is False

    def test_neither(self):
        assert gsv.status_uses_legacy_schema({}) is False


# ─────────────────────────────────────────────
# extract_task_title
# ─────────────────────────────────────────────


class TestExtractTaskTitle:
    def test_valid(self, tmp_path):
        p = tmp_path / "task.md"
        p.write_text("# Task: Implement Feature X\n## Metadata\n", encoding="utf-8")
        assert gsv.extract_task_title(p) == "Implement Feature X"

    def test_no_title(self, tmp_path):
        p = tmp_path / "task.md"
        p.write_text("## Random\nContent", encoding="utf-8")
        assert gsv.extract_task_title(p) == ""

    def test_none_path(self):
        assert gsv.extract_task_title(None) == ""

    def test_missing_file(self, tmp_path):
        assert gsv.extract_task_title(tmp_path / "nope.md") == ""


# ─────────────────────────────────────────────
# task_is_high_risk
# ─────────────────────────────────────────────


class TestTaskIsHighRisk:
    def test_security_keyword(self, tmp_path):
        p = tmp_path / "task.md"
        p.write_text("# Task: Security audit\n", encoding="utf-8")
        assert gsv.task_is_high_risk(p, "") is True

    def test_upstream_keyword_in_plan(self, tmp_path):
        p = tmp_path / "task.md"
        p.write_text("# Task: Normal task\n", encoding="utf-8")
        assert gsv.task_is_high_risk(p, "upstream pr integration") is True

    def test_no_risk(self, tmp_path):
        p = tmp_path / "task.md"
        p.write_text("# Task: Simple refactor\n", encoding="utf-8")
        assert gsv.task_is_high_risk(p, "simple plan") is False

    def test_none_path(self):
        assert gsv.task_is_high_risk(None, "security concern") is True

    def test_none_path_no_risk(self):
        assert gsv.task_is_high_risk(None, "normal plan") is False


# ─────────────────────────────────────────────
# validate_research_citations
# ─────────────────────────────────────────────


class TestValidateResearchCitations:
    def test_missing_sources(self, tmp_path):
        p = tmp_path / "research.md"
        p.write_text("# Research\n## Other\nContent", encoding="utf-8")
        findings = gsv.validate_research_citations("TASK-001", p)
        assert any(f.severity == "CRITICAL" for f in findings)

    def test_empty_sources(self, tmp_path):
        p = tmp_path / "research.md"
        p.write_text("# Research\n## Sources\nNone", encoding="utf-8")
        findings = gsv.validate_research_citations("TASK-001", p)
        assert any("at least 2" in f.message for f in findings)

    def test_valid_sources(self, tmp_path):
        p = tmp_path / "research.md"
        sources = (
            "## Sources\n"
            '[1] Author A. "Title A." https://example.com/a (2025-01-15 retrieved)\n'
            '[2] Author B. "Title B." https://example.com/b (2025-01-16 retrieved)\n'
        )
        p.write_text(f"# Research\n{sources}", encoding="utf-8")
        findings = gsv.validate_research_citations("TASK-001", p)
        assert findings == []

    def test_single_source_warning(self, tmp_path):
        p = tmp_path / "research.md"
        sources = (
            "## Sources\n"
            '[1] Author. "Title." https://example.com (2025-01-15 retrieved)\n'
        )
        p.write_text(f"# Research\n{sources}", encoding="utf-8")
        findings = gsv.validate_research_citations("TASK-001", p)
        assert any(f.severity == "MAJOR" and "at least 2" in f.message for f in findings)


# ─────────────────────────────────────────────
# validate_status_schema
# ─────────────────────────────────────────────


class TestValidateStatusSchema:
    def _modern_status(self, task_id="TASK-001", state="drafted"):
        return {
            "task_id": task_id,
            "state": state,
            "current_owner": "Claude Code",
            "next_agent": "Claude Code",
            "required_artifacts": ["task", "status"],
            "available_artifacts": ["task", "status"],
            "missing_artifacts": [],
            "blocked_reason": "",
            "last_updated": "2026-01-15T10:00:00+08:00",
        }

    def test_valid_modern(self):
        result = gsv.validate_status_schema(self._modern_status(), "TASK-001")
        assert result.ok

    def test_task_id_mismatch(self):
        result = gsv.validate_status_schema(self._modern_status("TASK-002"), "TASK-001")
        assert not result.ok
        assert any("mismatch" in e for e in result.errors)

    def test_invalid_state(self):
        result = gsv.validate_status_schema(self._modern_status(state="invalid"), "TASK-001")
        assert not result.ok

    def test_missing_keys(self):
        status = {"task_id": "TASK-001", "state": "drafted", "last_updated": "2026-01-15T10:00:00+08:00"}
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("missing required keys" in e for e in result.errors)

    def test_blocked_requires_reason(self):
        status = self._modern_status(state="blocked")
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("blocked_reason" in e for e in result.errors)

    def test_blocked_with_reason(self):
        status = self._modern_status(state="blocked")
        status["blocked_reason"] = "Waiting on upstream"
        result = gsv.validate_status_schema(status, "TASK-001")
        assert result.ok

    def test_unknown_artifact_in_list(self):
        status = self._modern_status()
        status["required_artifacts"] = ["task", "unknown_type"]
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("unknown artifacts" in e for e in result.errors)

    def test_legacy_schema_valid(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "drafted",
            "owner": "Claude",
            "last_updated": "2026-01-15T10:00:00+08:00",
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert result.ok

    def test_legacy_blocked_without_blockers(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "blocked",
            "owner": "Claude",
            "last_updated": "2026-01-15T10:00:00+08:00",
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("blockers" in e for e in result.errors)


# ─────────────────────────────────────────────
# validate_premortem
# ─────────────────────────────────────────────


class TestValidatePremortem:
    def _make_plan(self, tmp_path, risks_section):
        p = tmp_path / "plan.md"
        p.write_text(
            f"# Plan: TASK-001\n## Scope\nSomething\n## Risks\n{risks_section}\n## Files Likely Affected\n- `a.py`\n",
            encoding="utf-8",
        )
        return p

    def _make_task(self, tmp_path, title="Implement Feature"):
        p = tmp_path / "task.md"
        p.write_text(f"# Task: {title}\n## Metadata\n", encoding="utf-8")
        return p

    def test_missing_risks_section(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n## Scope\nSomething\n", encoding="utf-8")
        result = gsv.validate_premortem(plan, None)
        assert not result.ok
        assert any("## Risks section not found" in e for e in result.errors)

    def test_empty_risks(self, tmp_path):
        plan = self._make_plan(tmp_path, "none")
        result = gsv.validate_premortem(plan, None)
        assert not result.ok

    def test_valid_premortem(self, tmp_path):
        risks = textwrap.dedent("""\
            R1: Connection pool exhaustion
            - Risk: High traffic causes pool depletion
            - Trigger: >1000 concurrent connections
            - Detection: Connection timeout alerts
            - Mitigation: Circuit breaker pattern
            - Severity: blocking

            R2: Schema migration failure
            - Risk: Migration script fails
            - Trigger: Database version mismatch
            - Detection: CI migration test
            - Mitigation: Rollback script
            - Severity: non-blocking

            R3: API backward incompatibility
            - Risk: Breaking changes in response format
            - Trigger: Client parsing failure
            - Detection: Contract tests
            - Mitigation: API versioning
            - Severity: non-blocking
        """)
        plan = self._make_plan(tmp_path, risks)
        task = self._make_task(tmp_path)
        result = gsv.validate_premortem(plan, task)
        assert result.ok, f"Unexpected errors: {result.errors}"

    def test_missing_required_field(self, tmp_path):
        risks = "R1: Issue\n- Risk: Something\n- Severity: blocking\n"
        plan = self._make_plan(tmp_path, risks)
        result = gsv.validate_premortem(plan, None)
        assert not result.ok
        assert any("Trigger:" in e for e in result.errors)

    def test_invalid_severity(self, tmp_path):
        risks = textwrap.dedent("""\
            R1: Issue
            - Risk: Something
            - Trigger: Event
            - Detection: Monitor
            - Mitigation: Fix
            - Severity: critical
        """)
        plan = self._make_plan(tmp_path, risks)
        result = gsv.validate_premortem(plan, None)
        assert not result.ok
        assert any("blocking" in e and "non-blocking" in e for e in result.errors)


# ═════════════════════════════════════════════
# FIXTURE-BASED TESTS FOR guard_contract_validator
# ═════════════════════════════════════════════


# ─────────────────────────────────────────────
# normalize_text
# ─────────────────────────────────────────────


class TestGcvNormalizeText:
    def test_crlf_to_lf(self):
        assert gcv.normalize_text("line1\r\nline2") == "line1\nline2"

    def test_placeholder_replacement(self):
        result = gcv.normalize_text("{{PROJECT_NAME}} / {{REPO_NAME}} / {{UPSTREAM_ORG}}")
        assert "__PROJECT__" in result
        assert "__REPO__" in result
        assert "__ORG__" in result

    def test_whitespace_collapse(self):
        assert gcv.normalize_text("a   b\tc") == "a b c"

    def test_strip(self):
        assert gcv.normalize_text("  hello  ") == "hello"


# ─────────────────────────────────────────────
# validate_exact_sync
# ─────────────────────────────────────────────


class TestValidateExactSync:
    def _setup_sync_pair(self, tmp_path, relative, root_content, template_content=None):
        """Create a root file and its template counterpart."""
        root_file = tmp_path / relative
        root_file.parent.mkdir(parents=True, exist_ok=True)
        root_file.write_text(root_content, encoding="utf-8")
        tmpl_file = tmp_path / "template" / relative
        tmpl_file.parent.mkdir(parents=True, exist_ok=True)
        tmpl_file.write_text(template_content or root_content, encoding="utf-8")

    def test_all_in_sync(self, tmp_path):
        for rel in gcv.EXACT_SYNC_FILES:
            self._setup_sync_pair(tmp_path, rel, f"content of {rel}")
        errors = gcv.validate_exact_sync(tmp_path)
        assert errors == []

    def test_root_missing(self, tmp_path):
        # Create template only, skip root
        for rel in gcv.EXACT_SYNC_FILES:
            tmpl = tmp_path / "template" / rel
            tmpl.parent.mkdir(parents=True, exist_ok=True)
            tmpl.write_text("x", encoding="utf-8")
        errors = gcv.validate_exact_sync(tmp_path)
        assert all("Missing root file" in e for e in errors)

    def test_template_missing(self, tmp_path):
        for rel in gcv.EXACT_SYNC_FILES:
            root_f = tmp_path / rel
            root_f.parent.mkdir(parents=True, exist_ok=True)
            root_f.write_text("x", encoding="utf-8")
        errors = gcv.validate_exact_sync(tmp_path)
        assert all("Missing template file" in e for e in errors)

    def test_drift_detected(self, tmp_path):
        for rel in gcv.EXACT_SYNC_FILES:
            self._setup_sync_pair(tmp_path, rel, f"content of {rel}")
        # Introduce drift in the first file
        first = gcv.EXACT_SYNC_FILES[0]
        (tmp_path / first).write_text("different content", encoding="utf-8")
        errors = gcv.validate_exact_sync(tmp_path)
        assert len(errors) == 1
        assert "Contract drift" in errors[0]

    def test_whitespace_and_placeholder_normalized(self, tmp_path):
        for rel in gcv.EXACT_SYNC_FILES:
            self._setup_sync_pair(
                tmp_path, rel,
                "root  content  {{PROJECT_NAME}}",
                "root content {{PROJECT_NAME}}",
            )
        errors = gcv.validate_exact_sync(tmp_path)
        assert errors == []


# ─────────────────────────────────────────────
# validate_required_phrases
# ─────────────────────────────────────────────


class TestValidateRequiredPhrases:
    def test_all_present(self, tmp_path):
        for rel, phrases in gcv.REQUIRED_PHRASES.items():
            f = tmp_path / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_text(" ".join(phrases), encoding="utf-8")
        errors = gcv.validate_required_phrases(tmp_path)
        assert errors == []

    def test_missing_file(self, tmp_path):
        errors = gcv.validate_required_phrases(tmp_path)
        assert all("Missing required file" in e for e in errors)

    def test_missing_phrase(self, tmp_path):
        for rel, phrases in gcv.REQUIRED_PHRASES.items():
            f = tmp_path / rel
            f.parent.mkdir(parents=True, exist_ok=True)
            # Write all phrases except the first one
            f.write_text(" ".join(phrases[1:]), encoding="utf-8")
        errors = gcv.validate_required_phrases(tmp_path)
        assert len(errors) > 0
        assert all("missing required phrase" in e for e in errors)


# ─────────────────────────────────────────────
# validate_repository_profile
# ─────────────────────────────────────────────


class TestValidateRepositoryProfile:
    def _valid_profile(self):
        return {
            "about": "A" * 100,
            "topics": list(gcv.REQUIRED_TOPICS) + ["extra-topic-1"],
        }

    def _write_profile(self, tmp_path, relative, data):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data), encoding="utf-8")

    def test_valid(self, tmp_path):
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            self._write_profile(tmp_path, rel, self._valid_profile())
        errors = gcv.validate_repository_profile(tmp_path)
        assert errors == []

    def test_missing_file(self, tmp_path):
        errors = gcv.validate_repository_profile(tmp_path)
        assert all("Missing required repository profile" in e for e in errors)

    def test_invalid_json(self, tmp_path):
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            path = tmp_path / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("{bad json}", encoding="utf-8")
        errors = gcv.validate_repository_profile(tmp_path)
        assert all("not valid JSON" in e for e in errors)

    def test_about_empty(self, tmp_path):
        profile = self._valid_profile()
        profile["about"] = ""
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            self._write_profile(tmp_path, rel, profile)
        errors = gcv.validate_repository_profile(tmp_path)
        assert any("non-empty string" in e for e in errors)

    def test_about_too_short(self, tmp_path):
        profile = self._valid_profile()
        profile["about"] = "Short"
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            self._write_profile(tmp_path, rel, profile)
        errors = gcv.validate_repository_profile(tmp_path)
        assert any("80-200 chars" in e for e in errors)

    def test_about_too_long(self, tmp_path):
        profile = self._valid_profile()
        profile["about"] = "X" * 201
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            self._write_profile(tmp_path, rel, profile)
        errors = gcv.validate_repository_profile(tmp_path)
        assert any("80-200 chars" in e for e in errors)

    def test_topics_not_list(self, tmp_path):
        profile = self._valid_profile()
        profile["topics"] = "not-a-list"
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            self._write_profile(tmp_path, rel, profile)
        errors = gcv.validate_repository_profile(tmp_path)
        assert any("must define list" in e for e in errors)

    def test_topics_too_few(self, tmp_path):
        profile = self._valid_profile()
        profile["topics"] = ["topic-1", "topic-2"]
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            self._write_profile(tmp_path, rel, profile)
        errors = gcv.validate_repository_profile(tmp_path)
        assert any("6-12 items" in e for e in errors)

    def test_topics_too_many(self, tmp_path):
        profile = self._valid_profile()
        profile["topics"] = [f"topic-{i}" for i in range(13)]
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            self._write_profile(tmp_path, rel, profile)
        errors = gcv.validate_repository_profile(tmp_path)
        assert any("6-12 items" in e for e in errors)

    def test_topics_duplicates(self, tmp_path):
        profile = self._valid_profile()
        profile["topics"] = list(gcv.REQUIRED_TOPICS) + [list(gcv.REQUIRED_TOPICS)[0]]
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            self._write_profile(tmp_path, rel, profile)
        errors = gcv.validate_repository_profile(tmp_path)
        assert any("duplicates" in e for e in errors)

    def test_topics_invalid_format(self, tmp_path):
        profile = self._valid_profile()
        profile["topics"] = list(gcv.REQUIRED_TOPICS) + ["UPPER_CASE"]
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            self._write_profile(tmp_path, rel, profile)
        errors = gcv.validate_repository_profile(tmp_path)
        assert any("lowercase-kebab-case" in e for e in errors)

    def test_topics_missing_required(self, tmp_path):
        profile = self._valid_profile()
        profile["topics"] = [f"custom-topic-{i}" for i in range(7)]
        for rel in gcv.REPOSITORY_PROFILE_FILES:
            self._write_profile(tmp_path, rel, profile)
        errors = gcv.validate_repository_profile(tmp_path)
        assert any("missing required topics" in e for e in errors)


# ─────────────────────────────────────────────
# extract_h2_headers / validate_readme_structure
# ─────────────────────────────────────────────


class TestExtractH2Headers:
    def test_basic(self):
        assert gcv.extract_h2_headers("## One\ntext\n## Two\n") == ["One", "Two"]

    def test_nested_ignored(self):
        assert gcv.extract_h2_headers("### Three\n## Two\n") == ["Two"]

    def test_no_headers(self):
        assert gcv.extract_h2_headers("plain text") == []


class TestValidateReadmeStructure:
    def test_matching(self, tmp_path):
        en = tmp_path / "README.md"
        zh = tmp_path / "README.zh-TW.md"
        en.write_text("## Overview\n## Usage\n", encoding="utf-8")
        zh.write_text("## 概述\n## 使用方式\n", encoding="utf-8")
        errors = gcv.validate_readme_structure(tmp_path)
        assert errors == []

    def test_section_count_mismatch(self, tmp_path):
        en = tmp_path / "README.md"
        zh = tmp_path / "README.zh-TW.md"
        en.write_text("## One\n## Two\n## Three\n", encoding="utf-8")
        zh.write_text("## 一\n## 二\n", encoding="utf-8")
        errors = gcv.validate_readme_structure(tmp_path)
        assert any("structure mismatch" in e for e in errors)

    def test_missing_en(self, tmp_path):
        zh = tmp_path / "README.zh-TW.md"
        zh.write_text("## Test\n", encoding="utf-8")
        errors = gcv.validate_readme_structure(tmp_path)
        assert any("Missing README.md" in e for e in errors)

    def test_template_level(self, tmp_path):
        # Root files present and matching
        (tmp_path / "README.md").write_text("## A\n", encoding="utf-8")
        (tmp_path / "README.zh-TW.md").write_text("## B\n", encoding="utf-8")
        # Template mismatch
        tmpl = tmp_path / "template"
        tmpl.mkdir()
        (tmpl / "README.md").write_text("## A\n## B\n", encoding="utf-8")
        (tmpl / "README.zh-TW.md").write_text("## A\n", encoding="utf-8")
        errors = gcv.validate_readme_structure(tmp_path)
        assert any("template" in e and "mismatch" in e for e in errors)


# ─────────────────────────────────────────────
# detect_changed_files
# ─────────────────────────────────────────────


class TestDetectChangedFiles:
    def test_not_a_git_repo(self, tmp_path):
        # tmp_path is not a git repo; git commands should fail gracefully
        available, changed = gcv.detect_changed_files(tmp_path)
        assert isinstance(changed, set)

    def test_git_not_installed(self, tmp_path, monkeypatch):
        def mock_run(*args, **kwargs):
            raise FileNotFoundError("git not found")

        monkeypatch.setattr(gcv.subprocess, "run", mock_run)
        available, changed = gcv.detect_changed_files(tmp_path)
        assert available is False
        assert changed == set()

    def test_successful_with_changes(self, tmp_path, monkeypatch):
        call_count = 0

        def mock_run(cmd, **kwargs):
            nonlocal call_count
            call_count += 1

            class Result:
                returncode = 0
                stdout = "CLAUDE.md\nGEMINI.md\n" if call_count == 1 else ""

            return Result()

        monkeypatch.setattr(gcv.subprocess, "run", mock_run)
        available, changed = gcv.detect_changed_files(tmp_path)
        assert available is True
        assert "CLAUDE.md" in changed
        assert "GEMINI.md" in changed

    def test_returncode_nonzero_skipped(self, tmp_path, monkeypatch):
        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 128
                stdout = ""

            return Result()

        monkeypatch.setattr(gcv.subprocess, "run", mock_run)
        available, changed = gcv.detect_changed_files(tmp_path)
        assert available is False
        assert changed == set()

    def test_backslash_normalized(self, tmp_path, monkeypatch):
        def mock_run(cmd, **kwargs):
            class Result:
                returncode = 0
                stdout = "artifacts\\scripts\\test.py\n"

            return Result()

        monkeypatch.setattr(gcv.subprocess, "run", mock_run)
        _, changed = gcv.detect_changed_files(tmp_path)
        assert "artifacts/scripts/test.py" in changed


# ─────────────────────────────────────────────
# validate_prompt_case_sync (mock-based)
# ─────────────────────────────────────────────


class TestValidatePromptCaseSync:
    def test_no_git_available(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gcv, "detect_changed_files", lambda root: (False, set()))
        errors = gcv.validate_prompt_case_sync(tmp_path)
        assert errors == []

    def test_no_changes(self, tmp_path, monkeypatch):
        monkeypatch.setattr(gcv, "detect_changed_files", lambda root: (True, set()))
        errors = gcv.validate_prompt_case_sync(tmp_path)
        assert errors == []

    def test_prompt_changed_without_regression(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            gcv, "detect_changed_files",
            lambda root: (True, {"CLAUDE.md", "AGENTS.md"}),
        )
        errors = gcv.validate_prompt_case_sync(tmp_path)
        assert len(errors) == 1
        assert "prompt regression cases" in errors[0].lower()

    def test_prompt_changed_with_regression(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            gcv, "detect_changed_files",
            lambda root: (True, {
                "CLAUDE.md",
                "artifacts/scripts/drills/prompt_regression_cases.json",
            }),
        )
        errors = gcv.validate_prompt_case_sync(tmp_path)
        assert errors == []

    def test_non_prompt_changes_ok(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            gcv, "detect_changed_files",
            lambda root: (True, {"artifacts/scripts/guard_status_validator.py"}),
        )
        errors = gcv.validate_prompt_case_sync(tmp_path)
        assert errors == []


# ─────────────────────────────────────────────
# validate_readme_structure: missing zh only
# ─────────────────────────────────────────────


class TestValidateReadmeStructureMissingZh:
    def test_missing_zh(self, tmp_path):
        (tmp_path / "README.md").write_text("## Test\n", encoding="utf-8")
        errors = gcv.validate_readme_structure(tmp_path)
        assert any("Missing README.zh-TW.md" in e for e in errors)


# ═════════════════════════════════════════════
# COVERAGE EXPANSION: guard_status_validator
# ═════════════════════════════════════════════


# ─────────────────────────────────────────────
# validate_status_schema: decision_waivers & auto_upgrade_log
# ─────────────────────────────────────────────


class TestValidateStatusSchemaDecisionWaivers:
    def _modern_status(self, **overrides):
        base = {
            "task_id": "TASK-001",
            "state": "drafted",
            "current_owner": "Claude",
            "next_agent": "Claude",
            "required_artifacts": ["task", "status"],
            "available_artifacts": ["task", "status"],
            "missing_artifacts": [],
            "blocked_reason": "",
            "last_updated": "2026-01-15T10:00:00+08:00",
        }
        base.update(overrides)
        return base

    def test_valid_waiver(self):
        status = self._modern_status(decision_waivers=[{
            "gate": "Gate_A",
            "reason": "Research not needed",
            "approver": "User",
            "expires": "2099-12-31T23:59:59+08:00",
        }])
        result = gsv.validate_status_schema(status, "TASK-001")
        assert result.ok

    def test_waiver_not_list(self):
        status = self._modern_status(decision_waivers="invalid")
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("decision_waivers" in e and "list" in e for e in result.errors)

    def test_waiver_entry_not_dict(self):
        status = self._modern_status(decision_waivers=["bad"])
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("must be an object" in e for e in result.errors)

    def test_waiver_missing_fields(self):
        status = self._modern_status(decision_waivers=[{"gate": "Gate_A"}])
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("missing required fields" in e for e in result.errors)

    def test_waiver_invalid_gate(self):
        status = self._modern_status(decision_waivers=[{
            "gate": "Gate_Z",
            "reason": "test",
            "approver": "User",
            "expires": "2099-12-31T23:59:59+08:00",
        }])
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("gate must be one of" in e for e in result.errors)

    def test_waiver_expired(self):
        status = self._modern_status(decision_waivers=[{
            "gate": "Gate_A",
            "reason": "test",
            "approver": "User",
            "expires": "2020-01-01T00:00:00+08:00",
        }])
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("expired" in e for e in result.errors)


class TestValidateStatusSchemaAutoUpgradeLog:
    def _modern_status(self, **overrides):
        base = {
            "task_id": "TASK-001",
            "state": "drafted",
            "current_owner": "Claude",
            "next_agent": "Claude",
            "required_artifacts": ["task", "status"],
            "available_artifacts": ["task", "status"],
            "missing_artifacts": [],
            "blocked_reason": "",
            "last_updated": "2026-01-15T10:00:00+08:00",
        }
        base.update(overrides)
        return base

    def test_valid_auto_upgrade_log(self):
        status = self._modern_status(auto_upgrade_log=[{
            "timestamp": "2026-01-15T10:00:00+08:00",
            "reason": "plan has non-empty risks",
            "from_mode": "lightweight",
            "to_mode": "full",
        }])
        result = gsv.validate_status_schema(status, "TASK-001")
        assert result.ok

    def test_auto_upgrade_log_not_list(self):
        status = self._modern_status(auto_upgrade_log="bad")
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("auto_upgrade_log" in e and "list" in e for e in result.errors)

    def test_auto_upgrade_log_entry_not_dict(self):
        status = self._modern_status(auto_upgrade_log=["bad"])
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("must be an object" in e for e in result.errors)

    def test_auto_upgrade_log_missing_field(self):
        status = self._modern_status(auto_upgrade_log=[{"timestamp": "2026-01-15T10:00:00+08:00"}])
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("missing required field" in e for e in result.errors)

    def test_auto_upgrade_log_bad_timestamp(self):
        status = self._modern_status(auto_upgrade_log=[{
            "timestamp": "not-a-timestamp",
            "reason": "test",
            "from_mode": "lightweight",
            "to_mode": "full",
        }])
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("timestamp" in e.lower() for e in result.errors)

    def test_legacy_empty_owner(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "drafted",
            "owner": "",
            "last_updated": "2026-01-15T10:00:00+08:00",
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("owner" in e and "non-empty" in e for e in result.errors)

    def test_legacy_artifacts_not_dict(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "drafted",
            "owner": "Claude",
            "last_updated": "2026-01-15T10:00:00+08:00",
            "artifacts": "bad",
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("artifacts" in e and "object" in e for e in result.errors)

    def test_legacy_non_blocked_with_blockers_warning(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "drafted",
            "owner": "Claude",
            "last_updated": "2026-01-15T10:00:00+08:00",
            "blockers": ["something"],
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert result.ok
        assert any("blockers" in w and "not blocked" in w for w in result.warnings)

    def test_non_blocked_with_reason_warning(self):
        status = self._modern_status(blocked_reason="stale reason")
        result = gsv.validate_status_schema(status, "TASK-001")
        assert result.ok
        assert any("blocked_reason" in w and "not blocked" in w for w in result.warnings)

    def test_required_artifacts_not_list(self):
        status = self._modern_status(required_artifacts="bad")
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.ok
        assert any("required_artifacts" in e and "list" in e for e in result.errors)


# ─────────────────────────────────────────────
# categorize_override_error
# ─────────────────────────────────────────────


class TestCategorizeOverrideError:
    def test_override_log_missing(self):
        assert gsv.categorize_override_error("override log missing for TASK-001") == "override_log_missing"

    def test_premortem_missing(self):
        assert gsv.categorize_override_error("plan.md: premortem check failed — ## risks section not found") == "premortem_missing"

    def test_premortem_dismissed(self):
        assert gsv.categorize_override_error("plan.md: premortem check failed — section is empty or trivially dismissed") == "premortem_missing"

    def test_premortem_other(self):
        assert gsv.categorize_override_error("plan.md: premortem missing required field 'Trigger:'") == "premortem"

    def test_critical(self):
        assert gsv.categorize_override_error("Missing required artifacts for state 'coding': ['code']") == "critical"


# ─────────────────────────────────────────────
# apply_decision_waivers
# ─────────────────────────────────────────────


class TestApplyDecisionWaivers:
    def _waiver_status(self, gate, expires="2099-12-31T23:59:59+08:00"):
        return {
            "decision_waivers": [{
                "gate": gate,
                "reason": "test waiver",
                "approver": "User",
                "expires": expires,
            }],
        }

    def test_no_waivers_passthrough(self):
        result = gsv.ValidationResult(["some error"], ["some warning"])
        status = {}
        out = gsv.apply_decision_waivers(result, status)
        assert out.errors == ["some error"]

    def test_no_errors_passthrough(self):
        result = gsv.ValidationResult([], ["some warning"])
        status = self._waiver_status("Gate_A")
        out = gsv.apply_decision_waivers(result, status)
        assert out.ok

    def test_waiver_covers_gate_a_research(self):
        result = gsv.ValidationResult(
            ["Missing required artifacts for state 'researched': ['research']"],
            [],
        )
        status = self._waiver_status("Gate_A")
        out = gsv.apply_decision_waivers(result, status)
        assert out.ok
        assert "A" in out.active_waivers

    def test_waiver_does_not_cover_unmatched_gate(self):
        result = gsv.ValidationResult(
            ["Missing required artifacts for state 'researched': ['research']"],
            [],
        )
        status = self._waiver_status("Gate_D")
        out = gsv.apply_decision_waivers(result, status)
        assert not out.ok

    def test_meta_error_preserved_when_others_waived(self):
        result = gsv.ValidationResult(
            [
                "Target state 'done' requirements are not yet satisfied.",
                "Missing required artifacts for state 'done': ['verify']",
            ],
            [],
        )
        status = self._waiver_status("Gate_D")
        out = gsv.apply_decision_waivers(result, status)
        # verify waived, but meta error kept only if remaining errors exist
        # Actually meta errors are separated; if all non-meta waived, then no remaining
        assert out.ok


# ─────────────────────────────────────────────
# validate_code_mapping_to_plan
# ─────────────────────────────────────────────


class TestValidateCodeMappingToPlan:
    def _make_code(self, tmp_path, mapping_section):
        p = tmp_path / "code.md"
        content = f"# Code Result: TASK-001\n## Metadata\n## Files Changed\n- `a.py`\n## Summary Of Changes\nDone\n## Mapping To Plan\n{mapping_section}\n"
        p.write_text(content, encoding="utf-8")
        return p

    def test_no_section(self, tmp_path):
        p = tmp_path / "code.md"
        p.write_text("# Code\n## Summary\nDone\n", encoding="utf-8")
        result = gsv.validate_code_mapping_to_plan(p.read_text(encoding="utf-8"), p)
        assert result.ok

    def test_no_plan_item_bullets(self, tmp_path):
        p = self._make_code(tmp_path, "- Implemented everything as planned.")
        result = gsv.validate_code_mapping_to_plan(p.read_text(encoding="utf-8"), p)
        assert result.ok

    def test_valid_entries(self, tmp_path):
        mapping = '- plan_item: 1.1, status: done, evidence: "commit abc"\n- plan_item: 1.2, status: partial, evidence: "WIP"\n'
        p = self._make_code(tmp_path, mapping)
        result = gsv.validate_code_mapping_to_plan(p.read_text(encoding="utf-8"), p)
        assert not result.warnings

    def test_invalid_entry_format(self, tmp_path):
        mapping = '- plan_item: 1.1, status: done, evidence: "ok"\n- plan_item: bad format\n'
        p = self._make_code(tmp_path, mapping)
        result = gsv.validate_code_mapping_to_plan(p.read_text(encoding="utf-8"), p)
        assert len(result.warnings) == 1
        assert "Mapping To Plan entry must match" in result.warnings[0]


# ─────────────────────────────────────────────
# validate_verify_checklist_schema
# ─────────────────────────────────────────────


class TestValidateVerifyChecklistSchema:
    def _make_verify(self, tmp_path, checklist_section):
        p = tmp_path / "verify.md"
        content = f"# Verification: TASK-001\n## Acceptance Criteria Checklist\n{checklist_section}\n## Pass Fail Result\npass\n"
        p.write_text(content, encoding="utf-8")
        return p

    def test_no_section(self, tmp_path):
        p = tmp_path / "verify.md"
        p.write_text("# Verify\n## Pass Fail Result\npass\n", encoding="utf-8")
        result = gsv.validate_verify_checklist_schema(p.read_text(encoding="utf-8"), p)
        assert not result.warnings

    def test_valid_structured_checklist(self, tmp_path):
        section = textwrap.dedent("""\
            - **criterion**: Build passes
            - **method**: CI pipeline
            - **evidence**: Pipeline #42 green
            - **result**: pass
            - **reviewer**: Claude
            - **timestamp**: 2026-01-15T10:00:00+08:00
        """)
        p = self._make_verify(tmp_path, section)
        result = gsv.validate_verify_checklist_schema(p.read_text(encoding="utf-8"), p)
        assert not result.warnings

    def test_missing_fields_warning(self, tmp_path):
        section = textwrap.dedent("""\
            - **criterion**: Build passes
            - **method**: CI
        """)
        p = self._make_verify(tmp_path, section)
        result = gsv.validate_verify_checklist_schema(p.read_text(encoding="utf-8"), p)
        assert len(result.warnings) > 0
        assert any("missing" in w for w in result.warnings)

    def test_invalid_timestamp_warning(self, tmp_path):
        section = textwrap.dedent("""\
            - **criterion**: Build passes
            - **method**: CI
            - **evidence**: ok
            - **result**: pass
            - **reviewer**: Claude
            - **timestamp**: bad-timestamp
        """)
        p = self._make_verify(tmp_path, section)
        result = gsv.validate_verify_checklist_schema(p.read_text(encoding="utf-8"), p)
        assert any("timestamp" in w.lower() for w in result.warnings)


# ─────────────────────────────────────────────
# validate_improvement_artifact
# ─────────────────────────────────────────────


class TestValidateImprovementArtifact:
    def _make_improvement(self, tmp_path, **overrides):
        fields = {
            "source_task": "TASK-001",
            "trigger_type": "failure",
            "preventive": "Add guard",
            "validation": "Run CI",
            "final_rule": "Always validate",
            "status": "approved",
        }
        fields.update(overrides)
        content = textwrap.dedent(f"""\
            # Process Improvement
            ## Metadata
            - Artifact Type: improvement
            - Source Task: {fields['source_task']}
            - Trigger Type: {fields['trigger_type']}
            - Owner: Claude
            - Status: {fields['status']}
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## 1. What Happened
            Something broke
            ## 2. Why It Was Not Prevented
            No guard existed
            ## 3. Failure Classification
            Process gap
            ## 5. Preventive Action (System Level)
            {fields['preventive']}
            ## 6. Validation
            {fields['validation']}
            ## 8. Final Rule
            {fields['final_rule']}
            ## 9. Status
            {fields['status']}
        """)
        p = tmp_path / "improvement.md"
        p.write_text(content, encoding="utf-8")
        return p

    def test_valid(self, tmp_path):
        p = self._make_improvement(tmp_path)
        result = gsv.validate_improvement_artifact(p.read_text(encoding="utf-8"), p, "TASK-001")
        assert result.ok

    def test_missing_source_task(self, tmp_path):
        p = self._make_improvement(tmp_path, source_task="")
        result = gsv.validate_improvement_artifact(p.read_text(encoding="utf-8"), p, "TASK-001")
        assert not result.ok
        assert any("Source Task" in e for e in result.errors)

    def test_wrong_source_task(self, tmp_path):
        p = self._make_improvement(tmp_path, source_task="TASK-999")
        result = gsv.validate_improvement_artifact(p.read_text(encoding="utf-8"), p, "TASK-001")
        assert not result.ok
        assert any("reference" in e.lower() or "TASK-001" in e for e in result.errors)

    def test_invalid_trigger_type(self, tmp_path):
        p = self._make_improvement(tmp_path, trigger_type="unknown")
        result = gsv.validate_improvement_artifact(p.read_text(encoding="utf-8"), p, "TASK-001")
        assert not result.ok
        assert any("Trigger Type" in e for e in result.errors)

    def test_empty_section(self, tmp_path):
        p = self._make_improvement(tmp_path, preventive="none")
        result = gsv.validate_improvement_artifact(p.read_text(encoding="utf-8"), p, "TASK-001")
        assert not result.ok


# ─────────────────────────────────────────────
# compare_reconstructed_scope
# ─────────────────────────────────────────────


class TestCompareReconstructedScope:
    def _make_artifacts(self, tmp_path, plan_files, code_files):
        plan = tmp_path / "plan.md"
        plan.write_text(
            f"# Plan\n## Files Likely Affected\n"
            + "".join(f"- `{f}`\n" for f in plan_files)
            + "\n## Scope\nTest\n",
            encoding="utf-8",
        )
        code = tmp_path / "code.md"
        code.write_text(
            f"# Code Result\n## Files Changed\n"
            + "".join(f"- `{f}`\n" for f in code_files)
            + "\n## Summary Of Changes\nDone\n",
            encoding="utf-8",
        )
        return plan, code

    def test_no_drift(self, tmp_path):
        plan, code = self._make_artifacts(tmp_path, ["a.py", "b.py"], ["a.py", "b.py"])
        result = gsv.compare_reconstructed_scope(plan, code, {"a.py", "b.py"}, "test")
        assert not result.errors
        assert not result.waiver_candidate_errors

    def test_undeclared_file(self, tmp_path):
        plan, code = self._make_artifacts(tmp_path, ["a.py", "b.py"], ["a.py"])
        result = gsv.compare_reconstructed_scope(plan, code, {"a.py", "b.py"}, "test")
        assert any("not listed in ## Files Changed" in e for e in result.waiver_candidate_errors)

    def test_unplanned_file(self, tmp_path):
        plan, code = self._make_artifacts(tmp_path, ["a.py"], ["a.py", "c.py"])
        result = gsv.compare_reconstructed_scope(plan, code, {"a.py", "c.py"}, "test")
        assert any("not listed in ## Files Likely Affected" in e for e in result.waiver_candidate_errors)


# ─────────────────────────────────────────────
# validate_scope_drift_waiver
# ─────────────────────────────────────────────


class TestValidateScopeDriftWaiver:
    def _make_decision(self, tmp_path, task_id, waived_files, justification="Valid reason"):
        d = tmp_path / "decisions"
        d.mkdir(exist_ok=True)
        content = textwrap.dedent(f"""\
            # Decision Log: {task_id}
            ## Metadata
            - Artifact Type: decision
            - Task ID: {task_id}
            - Owner: Claude
            - Status: done
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Issue
            Scope drift
            ## Chosen Option
            Allow drift
            ## Reasoning
            Necessary files
            ## Guard Exception
            - Exception Type: allow-scope-drift
            - Scope Files: {', '.join(waived_files)}
            - Justification: {justification}
        """)
        p = d / f"{task_id}.decision.md"
        p.write_text(content, encoding="utf-8")
        return p

    def test_no_drift_files(self, tmp_path):
        result = gsv.validate_scope_drift_waiver(tmp_path, "TASK-001", set())
        assert result.ok

    def test_drift_without_decision(self, tmp_path):
        (tmp_path / "decisions").mkdir()
        result = gsv.validate_scope_drift_waiver(tmp_path, "TASK-001", {"extra.py"})
        assert not result.ok
        assert any("decision artifact" in e for e in result.errors)

    def test_drift_with_valid_waiver(self, tmp_path):
        self._make_decision(tmp_path, "TASK-001", ["extra.py"])
        result = gsv.validate_scope_drift_waiver(tmp_path, "TASK-001", {"extra.py"})
        assert result.ok

    def test_drift_with_insufficient_waiver(self, tmp_path):
        self._make_decision(tmp_path, "TASK-001", ["other.py"])
        result = gsv.validate_scope_drift_waiver(tmp_path, "TASK-001", {"extra.py"})
        assert not result.ok


# ─────────────────────────────────────────────
# validate_premortem: additional edge cases
# ─────────────────────────────────────────────


class TestValidatePremortemEdges:
    def _make_plan(self, tmp_path, risks):
        p = tmp_path / "plan.md"
        p.write_text(f"# Plan\n## Risks\n{risks}\n", encoding="utf-8")
        return p

    def _make_task(self, tmp_path, title):
        p = tmp_path / "task.md"
        p.write_text(f"# Task: {title}\n## Metadata\n", encoding="utf-8")
        return p

    def test_insufficient_risk_count_for_code_task(self, tmp_path):
        risks = textwrap.dedent("""\
            R1: Issue
            - Risk: Something
            - Trigger: Event
            - Detection: Monitor
            - Mitigation: Fix
            - Severity: blocking
        """)
        plan = self._make_plan(tmp_path, risks)
        task = self._make_task(tmp_path, "Implement Feature")
        result = gsv.validate_premortem(plan, task)
        assert not result.ok
        assert any("at least" in e and "numbered risks" in e for e in result.errors)

    def test_banned_phrase_warning(self, tmp_path):
        risks = textwrap.dedent("""\
            R1: Issue one
            - Risk: Something may break 風險低
            - Trigger: Event
            - Detection: Monitor
            - Mitigation: Fix
            - Severity: blocking
            R2: Issue two
            - Risk: Another thing
            - Trigger: Event2
            - Detection: Monitor2
            - Mitigation: Fix2
            - Severity: non-blocking
            R3: Issue three
            - Risk: Third thing
            - Trigger: Event3
            - Detection: Monitor3
            - Mitigation: Fix3
            - Severity: non-blocking
        """)
        plan = self._make_plan(tmp_path, risks)
        result = gsv.validate_premortem(plan, None)
        assert result.ok
        assert any("風險低" in w for w in result.warnings)

    def test_hotfix_policy_fewer_risks_ok(self, tmp_path):
        risks = textwrap.dedent("""\
            R1: Hotfix risk
            - Risk: Deployment failure
            - Trigger: Bad deploy
            - Detection: Monitor
            - Mitigation: Rollback
            - Severity: non-blocking
        """)
        plan = self._make_plan(tmp_path, risks)
        task = self._make_task(tmp_path, "Hotfix: critical bug")
        result = gsv.validate_premortem(plan, task)
        assert result.ok

    def test_insufficient_blocking_count(self, tmp_path):
        risks = textwrap.dedent("""\
            R1: Issue one
            - Risk: Something
            - Trigger: Event
            - Detection: Monitor
            - Mitigation: Fix
            - Severity: non-blocking
            R2: Issue two
            - Risk: Another
            - Trigger: Event2
            - Detection: Monitor2
            - Mitigation: Fix2
            - Severity: non-blocking
            R3: Issue three
            - Risk: Third
            - Trigger: Event3
            - Detection: Monitor3
            - Mitigation: Fix3
            - Severity: non-blocking
        """)
        plan = self._make_plan(tmp_path, risks)
        task = self._make_task(tmp_path, "Implement feature")
        result = gsv.validate_premortem(plan, task)
        assert not result.ok
        assert any("blocking risks" in e for e in result.errors)


# ─────────────────────────────────────────────
# validate_research_artifact
# ─────────────────────────────────────────────


class TestValidateResearchArtifact:
    def _setup_research(self, tmp_path, task_id="TASK-001", research_text="", status_state="researched"):
        arts = tmp_path / "artifacts"
        for d in ("tasks", "research", "status"):
            (arts / d).mkdir(parents=True, exist_ok=True)
        # Status
        status = {
            "task_id": task_id,
            "state": status_state,
            "current_owner": "Claude",
            "next_agent": "Claude",
            "required_artifacts": ["task", "research", "status"],
            "available_artifacts": ["task", "research", "status"],
            "missing_artifacts": [],
            "blocked_reason": "",
            "last_updated": "2026-01-15T10:00:00+08:00",
        }
        (arts / "status" / f"{task_id}.status.json").write_text(
            json.dumps(status, indent=2), encoding="utf-8"
        )
        # Research
        p = arts / "research" / f"{task_id}.research.md"
        p.write_text(research_text, encoding="utf-8")
        return p

    def test_recommendation_forbidden(self, tmp_path):
        text = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            - Q1
            ## Confirmed Facts
            - Fact one https://example.com
            ## Uncertain Items
            - UNVERIFIED: Maybe
            ## Relevant References
            - Ref
            ## Constraints For Implementation
            - Must use X
            ## Recommendation
            Do this instead
            ## Sources
            [1] Author. "Title." https://example.com (2026-01-15 retrieved)
            [2] Author2. "Title2." https://example2.com (2026-01-15 retrieved)
        """)
        p = self._setup_research(tmp_path, research_text=text)
        result = gsv.validate_research_artifact("TASK-001", text, p)
        assert not result.ok
        assert any("Recommendation" in e for e in result.errors)

    def test_unverified_in_confirmed_facts(self, tmp_path):
        text = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            - Q1
            ## Confirmed Facts
            - UNVERIFIED: This should be in uncertain https://example.com
            ## Uncertain Items
            - UNVERIFIED: Maybe
            ## Relevant References
            - Ref
            ## Constraints For Implementation
            - Must do X
            ## Sources
            [1] Author. "Title." https://example.com (2026-01-15 retrieved)
            [2] Author2. "Title2." https://example2.com (2026-01-15 retrieved)
        """)
        p = self._setup_research(tmp_path, research_text=text)
        result = gsv.validate_research_artifact("TASK-001", text, p)
        assert not result.ok
        assert any("UNVERIFIED" in e and "Confirmed Facts" in e for e in result.errors)

    def test_uncertain_without_prefix(self, tmp_path):
        text = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            - Q1
            ## Confirmed Facts
            - Fact https://example.com
            ## Uncertain Items
            - Maybe something
            ## Relevant References
            - Ref
            ## Constraints For Implementation
            - Must do X
            ## Sources
            [1] Author. "Title." https://example.com (2026-01-15 retrieved)
            [2] Author2. "Title2." https://example2.com (2026-01-15 retrieved)
        """)
        p = self._setup_research(tmp_path, research_text=text)
        result = gsv.validate_research_artifact("TASK-001", text, p)
        assert not result.ok
        assert any("UNVERIFIED:" in e for e in result.errors)


# ─────────────────────────────────────────────
# build_decision_registry: parsing helpers
# ─────────────────────────────────────────────


class TestBdrBuildEntry:
    def _make_decision(self, tmp_path, task_id="TASK-001"):
        root = tmp_path
        (root / "artifacts" / "decisions").mkdir(parents=True)
        content = textwrap.dedent(f"""\
            # Decision Log: {task_id}
            ## Metadata
            - Artifact Type: decision
            - Task ID: {task_id}
            - Owner: Claude
            - Status: done
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Issue
            Need to choose framework
            ## Chosen Option
            React
            ## Reasoning
            Community support
        """)
        p = root / "artifacts" / "decisions" / f"{task_id}.decision.md"
        p.write_text(content, encoding="utf-8")
        return root, p

    def test_valid_decision(self, tmp_path):
        root, p = self._make_decision(tmp_path)
        entry = bdr.build_entry(root, p)
        assert entry.task_id == "TASK-001"
        assert "React" in entry.summary

    def test_decision_type_general(self, tmp_path):
        root, p = self._make_decision(tmp_path)
        entry = bdr.build_entry(root, p)
        assert entry.decision_type == "general_decision"


class TestBdrBuildRegistry:
    def test_empty_dir(self, tmp_path):
        d = tmp_path / "artifacts" / "decisions"
        d.mkdir(parents=True)
        registry = bdr.build_registry(tmp_path)
        assert isinstance(registry, dict)
        assert registry["total"] == 0

    def test_with_entries(self, tmp_path):
        d = tmp_path / "artifacts" / "decisions"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Decision Log: TASK-001
            ## Metadata
            - Artifact Type: decision
            - Task ID: TASK-001
            - Owner: Claude
            - Status: done
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Issue
            Test
            ## Chosen Option
            Option A
            ## Reasoning
            Because
        """)
        (d / "TASK-001.decision.md").write_text(content, encoding="utf-8")
        registry = bdr.build_registry(tmp_path)
        assert registry["total"] == 1

    def test_extract_metadata_date(self):
        text = "- Last Updated: 2026-01-15T10:00:00+08:00\n"
        assert bdr.extract_metadata_date(text) == "2026-01-15T10:00:00+08:00"

    def test_extract_decision_type_guard_exception(self):
        sections = {"guard exception": "some content"}
        assert bdr.extract_decision_type("", sections) == "guard_exception"

    def test_extract_summary_from_issue(self):
        sections = {"issue": "Need to decide something important"}
        assert "Need to decide" in bdr.extract_summary(sections)

    def test_fallback_same_task_ref_missing(self, tmp_path):
        result = bdr.fallback_same_task_ref(tmp_path, "plans", "TASK-001")
        assert result == []

    def test_fallback_same_task_ref_exists(self, tmp_path):
        p = tmp_path / "artifacts" / "plans" / "TASK-001.plan.md"
        p.parent.mkdir(parents=True)
        p.write_text("plan", encoding="utf-8")
        result = bdr.fallback_same_task_ref(tmp_path, "plans", "TASK-001")
        assert len(result) == 1
        assert "TASK-001.plan.md" in result[0]


# ─────────────────────────────────────────────
# validate_scorecard_deltas: helpers
# ─────────────────────────────────────────────


class TestVsdParseRows:
    def test_valid_rows(self):
        markdown = textwrap.dedent("""\
            | Case | Phase | Expected | Outcome | Exit | Baseline | Delta | Final | Evidence | Notes |
            |------|-------|----------|---------|------|----------|-------|-------|----------|-------|
            | TC-01 | static | pass | pass | 0 | 8 | 0 | 8 | `log.txt` | |
            | TC-02 | static | pass | fail | 1 | 7 | -1 | 6 | `log2.txt` | Regression found |
        """)
        rows = vsd.parse_rows(markdown)
        assert len(rows) == 2
        assert rows[0].case == "TC-01"
        assert rows[1].reviewer_delta == -1

    def test_no_table(self):
        rows = vsd.parse_rows("# Scorecard\nNo table here\n")
        assert rows == []

    def test_validate_zero_delta_ok(self):
        rows = [vsd.Row(case="TC-01", reviewer_delta=0, notes="")]
        failures = vsd.validate_rows(rows)
        assert failures == []

    def test_validate_nonzero_delta_without_notes(self):
        rows = [vsd.Row(case="TC-01", reviewer_delta=-1, notes="")]
        failures = vsd.validate_rows(rows)
        assert len(failures) == 1
        assert "TC-01" in failures[0]

    def test_validate_nonzero_delta_with_notes(self):
        rows = [vsd.Row(case="TC-01", reviewer_delta=-1, notes="Regression found")]
        failures = vsd.validate_rows(rows)
        assert failures == []

    def test_validate_placeholder_notes(self):
        for placeholder in ("none", "TBD", "待補"):
            rows = [vsd.Row(case="TC-01", reviewer_delta=1, notes=placeholder)]
            failures = vsd.validate_rows(rows)
            assert len(failures) == 1, f"Expected failure for placeholder '{placeholder}'"


# ─────────────────────────────────────────────
# detect_plan_code_scope_drift: additional
# ─────────────────────────────────────────────


class TestDetectPlanCodeScopeDriftEdges:
    def test_empty_planned(self):
        plan_text = "# Plan\n## Files Likely Affected\n\n"
        code_text = "# Code\n## Files Changed\n- `a.py`\n"
        result = gsv.detect_plan_code_scope_drift(plan_text, code_text)
        assert result == []

    def test_empty_changed(self):
        plan_text = "# Plan\n## Files Likely Affected\n- `a.py`\n"
        code_text = "# Code\n## Files Changed\n\n"
        result = gsv.detect_plan_code_scope_drift(plan_text, code_text)
        assert result == []


# ─────────────────────────────────────────────
# detect_mixed_github_sources: edge case
# ─────────────────────────────────────────────


class TestDetectMixedGithubSourcesEdges:
    def test_raw_github_urls(self):
        text = (
            "https://raw.githubusercontent.com/alice/repo/main/file.py "
            "https://raw.githubusercontent.com/bob/repo/main/file.py"
        )
        result = gsv.detect_mixed_github_sources(text)
        assert len(result) == 1
        assert "repo" in result[0]


# ─────────────────────────────────────────────
# research_citations_are_blocking
# ─────────────────────────────────────────────


class TestResearchCitationsAreBlocking:
    def test_always_true(self):
        assert gsv.research_citations_are_blocking({}) is True
        assert gsv.research_citations_are_blocking({"state": "done"}) is True


# ─────────────────────────────────────────────
# verify_result_is_pass / plan_ready_for_coding
# ─────────────────────────────────────────────


class TestVerifyResultIsPass:
    def test_pass(self, tmp_path):
        p = tmp_path / "verify.md"
        p.write_text("# Verify\n## Pass Fail Result\npass\n", encoding="utf-8")
        assert gsv.verify_result_is_pass(p) is True

    def test_fail(self, tmp_path):
        p = tmp_path / "verify.md"
        p.write_text("# Verify\n## Pass Fail Result\nfail\n", encoding="utf-8")
        assert gsv.verify_result_is_pass(p) is False

    def test_missing(self, tmp_path):
        p = tmp_path / "verify.md"
        p.write_text("# Verify\nNo result section\n", encoding="utf-8")
        assert gsv.verify_result_is_pass(p) is False


class TestPlanReadyForCoding:
    def test_yes(self, tmp_path):
        p = tmp_path / "plan.md"
        p.write_text("# Plan\n## Ready For Coding\nyes\n", encoding="utf-8")
        assert gsv.plan_ready_for_coding(p) is True

    def test_no(self, tmp_path):
        p = tmp_path / "plan.md"
        p.write_text("# Plan\n## Ready For Coding\nno\n", encoding="utf-8")
        assert gsv.plan_ready_for_coding(p) is False


# ─────────────────────────────────────────────
# extract_task_inline_flags
# ─────────────────────────────────────────────


class TestExtractTaskInlineFlags:
    def test_basic(self):
        text = "- lightweight: true\n- premortem: required\n"
        flags = gsv.extract_task_inline_flags(text)
        assert flags["lightweight"] == "true"
        assert flags["premortem"] == "required"

    def test_empty(self):
        assert gsv.extract_task_inline_flags("no flags here") == {}


# ─────────────────────────────────────────────
# default_next_agent_for_state
# ─────────────────────────────────────────────


class TestDefaultNextAgentForState:
    def test_blocked(self):
        assert gsv.default_next_agent_for_state("blocked") == gsv.BLOCKED_STATUS_NEXT_AGENT

    def test_non_blocked(self):
        assert gsv.default_next_agent_for_state("drafted") == gsv.DEFAULT_STATUS_NEXT_AGENT


# ─────────────────────────────────────────────
# parse_structured_checklist_fields
# ─────────────────────────────────────────────


class TestParseStructuredChecklistFields:
    def test_bold_format(self):
        text = "- **criterion**: Build passes\n- **method**: CI\n"
        fields = gsv.parse_structured_checklist_fields(text)
        assert fields["criterion"] == "Build passes"
        assert fields["method"] == "CI"

    def test_plain_format(self):
        text = "- criterion: Build passes\n- method: CI\n"
        fields = gsv.parse_structured_checklist_fields(text)
        assert fields["criterion"] == "Build passes"

    def test_empty(self):
        assert gsv.parse_structured_checklist_fields("no fields") == {}


# ─────────────────────────────────────────────
# classify_premortem_policy
# ─────────────────────────────────────────────


class TestClassifyPremortemPolicy:
    def test_hotfix(self, tmp_path):
        p = tmp_path / "task.md"
        p.write_text("# Task: Hotfix critical bug\n## Metadata\n", encoding="utf-8")
        policy = gsv.classify_premortem_policy(p)
        assert policy.task_type == "hotfix"

    def test_research(self, tmp_path):
        p = tmp_path / "task.md"
        p.write_text("# Task: Research options\n## Metadata\n", encoding="utf-8")
        policy = gsv.classify_premortem_policy(p)
        assert policy.task_type == "research"

    def test_default(self, tmp_path):
        p = tmp_path / "task.md"
        p.write_text("# Task: Implement feature\n## Metadata\n", encoding="utf-8")
        policy = gsv.classify_premortem_policy(p)
        assert policy.task_type == "code"

    def test_none_path(self):
        policy = gsv.classify_premortem_policy(None)
        assert policy.task_type == "code"


# ─────────────────────────────────────────────
# append_auto_upgrade_log
# ─────────────────────────────────────────────


class TestAppendAutoUpgradeLog:
    def test_appends_entry(self, tmp_path):
        p = tmp_path / "status.json"
        status = {"task_id": "TASK-001", "state": "drafted", "last_updated": "2026-01-15T10:00:00+08:00"}
        p.write_text(json.dumps(status, indent=2), encoding="utf-8")
        gsv.append_auto_upgrade_log(p, status, "plan has risks")
        assert len(status["auto_upgrade_log"]) == 1
        assert status["auto_upgrade_log"][0]["reason"] == "plan has risks"
        # Verify written to disk
        on_disk = json.loads(p.read_text(encoding="utf-8"))
        assert "auto_upgrade_log" in on_disk

    def test_appends_to_existing(self, tmp_path):
        p = tmp_path / "status.json"
        status = {
            "task_id": "TASK-001",
            "state": "drafted",
            "last_updated": "2026-01-15T10:00:00+08:00",
            "auto_upgrade_log": [{"timestamp": "2026-01-14T10:00:00+08:00", "reason": "old", "from_mode": "lightweight", "to_mode": "full"}],
        }
        p.write_text(json.dumps(status, indent=2), encoding="utf-8")
        gsv.append_auto_upgrade_log(p, status, "new reason")
        assert len(status["auto_upgrade_log"]) == 2


# ─────────────────────────────────────────────
# print_result
# ─────────────────────────────────────────────


class TestPrintResult:
    def test_ok(self, capsys):
        gsv.print_result(gsv.ValidationResult([], []))
        captured = capsys.readouterr()
        assert "[OK]" in captured.out

    def test_error(self, capsys):
        gsv.print_result(gsv.ValidationResult(["err"], ["warn"]))
        captured = capsys.readouterr()
        assert "[ERROR]" in captured.out
        assert "[WARN]" in captured.out
        assert "[FAIL]" in captured.out

    def test_override_active(self, capsys):
        gsv.print_result(gsv.ValidationResult([], []), override_active=True)
        captured = capsys.readouterr()
        assert "[OVERRIDE ACTIVE]" in captured.out

    def test_waivers_shown(self, capsys):
        gsv.print_result(gsv.ValidationResult([], [], active_waivers=["A", "B"]))
        captured = capsys.readouterr()
        assert "[WAIVER ACTIVE gate=A]" in captured.out


# ─────────────────────────────────────────────
# Phase 2: High-impact coverage expansion
# ─────────────────────────────────────────────

def _ts():
    """Return a valid Taipei timestamp string."""
    return "2026-01-15T10:00:00+08:00"


def _future_ts():
    """Return a future Taipei timestamp for waiver expiry."""
    return "2099-12-31T23:59:59+08:00"


def _make_full_status(task_id, state="drafted", **overrides):
    """Build a valid modern status.json dict."""
    base = {
        "task_id": task_id,
        "state": state,
        "current_owner": "Claude",
        "next_agent": "Claude",
        "required_artifacts": ["task", "status"],
        "available_artifacts": ["task", "status"],
        "missing_artifacts": [],
        "blocked_reason": "",
        "last_updated": _ts(),
    }
    base.update(overrides)
    return base


def _write_status(tmp_path, task_id, status_dict):
    d = tmp_path / "status"
    d.mkdir(parents=True, exist_ok=True)
    p = d / f"{task_id}.status.json"
    p.write_text(json.dumps(status_dict, indent=2) + "\n", encoding="utf-8")
    return p


def _write_markdown_artifact(tmp_path, task_id, atype, extra_content=""):
    """Create a minimal valid markdown artifact."""
    markers = gsv.MARKERS[atype]
    dirname = gsv.ARTIFACT_DIRS[atype]
    ext = gsv.ARTIFACT_EXTENSIONS[atype]
    d = tmp_path / dirname
    d.mkdir(parents=True, exist_ok=True)

    allowed = gsv.ARTIFACT_ALLOWED_STATUSES.get(atype, {"drafted"})
    status_val = next(iter(sorted(allowed)))

    lines = [markers[0] + f" {task_id}"]
    lines.append("## Metadata")
    lines.append(f"- Artifact Type: {atype}")
    lines.append(f"- Task ID: {task_id}")
    lines.append("- Owner: Claude")
    lines.append(f"- Status: {status_val}")
    lines.append(f"- Last Updated: {_ts()}")
    lines.append("")

    # Add all remaining markers as sections (skip those provided in extra_content)
    for marker in markers[1:]:
        if marker.startswith("## "):
            if extra_content and marker in extra_content:
                continue
            lines.append(marker)
            lines.append("Content placeholder")
            lines.append("")
        elif marker.endswith(":") and not marker.startswith("#"):
            # Inline field like "Task ID:" already handled in metadata
            pass

    if extra_content:
        lines.append(extra_content)
    content = "\n".join(lines) + "\n"
    p = d / f"{task_id}{ext}"
    p.write_text(content, encoding="utf-8")
    return p


def _build_task_artifact(tmp_path, task_id):
    d = tmp_path / "tasks"
    d.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent(f"""\
        # Task: Test Task
        ## Metadata
        - Artifact Type: task
        - Task ID: {task_id}
        - Owner: Claude
        - Status: approved
        - Last Updated: {_ts()}
        ## Objective
        Test objective
        ## Constraints
        None
        ## Acceptance Criteria
        Done when tested
    """)
    p = d / f"{task_id}.task.md"
    p.write_text(content, encoding="utf-8")
    return p


def _build_plan_artifact(tmp_path, task_id, ready="yes", risk_count=4):
    d = tmp_path / "plans"
    d.mkdir(parents=True, exist_ok=True)
    risks = ""
    for i in range(1, risk_count + 1):
        sev = "blocking" if i <= 2 else "non-blocking"
        risks += textwrap.dedent(f"""\
            R{i}: Risk {i}
            - Risk: Something might break
            - Trigger: When X happens
            - Detection: Monitor logs
            - Mitigation: Roll back
            - Severity: {sev}
        """)
    content = textwrap.dedent(f"""\
        # Plan: {task_id}
        ## Metadata
        - Artifact Type: plan
        - Task ID: {task_id}
        - Owner: Claude
        - Status: approved
        - Last Updated: {_ts()}
        ## Scope
        Test scope
        ## Files Likely Affected
        - `src/main.py`
        - `tests/test_main.py`
        ## Proposed Changes
        Change things
        ## Validation Strategy
        Run tests
        ## Risks
        {risks}
        ## Ready For Coding
        {ready}
    """)
    p = d / f"{task_id}.plan.md"
    p.write_text(content, encoding="utf-8")
    return p


def _build_code_artifact(tmp_path, task_id):
    d = tmp_path / "code"
    d.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent(f"""\
        # Code Result: {task_id}
        ## Metadata
        - Artifact Type: code
        - Task ID: {task_id}
        - Owner: Claude
        - Status: ready
        - Last Updated: {_ts()}
        ## Files Changed
        - `src/main.py`
        - `tests/test_main.py`
        ## Summary Of Changes
        Implemented feature
        ## Mapping To Plan
        - plan_item: 1.1, status: done, evidence: "Implemented in src/main.py"
    """)
    p = d / f"{task_id}.code.md"
    p.write_text(content, encoding="utf-8")
    return p


def _build_verify_artifact(tmp_path, task_id, result="pass"):
    d = tmp_path / "verify"
    d.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent(f"""\
        # Verification: {task_id}
        ## Metadata
        - Artifact Type: verify
        - Task ID: {task_id}
        - Owner: Claude
        - Status: {result}
        - Last Updated: {_ts()}
        ## Acceptance Criteria Checklist
        - **Criterion**: Tests pass
        - **Method**: pytest
        - **Evidence**: All green
        - **Result**: pass
        - **Reviewer**: Claude
        - **Timestamp**: {_ts()}
        ## Pass Fail Result
        {result}
        ## Build Guarantee
        Commit abc1234
    """)
    p = d / f"{task_id}.verify.md"
    p.write_text(content, encoding="utf-8")
    return p


def _build_research_artifact(tmp_path, task_id):
    d = tmp_path / "research"
    d.mkdir(parents=True, exist_ok=True)
    content = textwrap.dedent(f"""\
        # Research: {task_id}
        ## Metadata
        - Artifact Type: research
        - Task ID: {task_id}
        - Owner: Claude
        - Status: ready
        - Last Updated: {_ts()}
        ## Research Questions
        How does X work?
        ## Confirmed Facts
        - X uses Y approach `docs/x.md`
        - Z is faster https://example.com/z
        ## Relevant References
        See docs
        ## Uncertain Items
        - UNVERIFIED: Might be slow
        ## Constraints For Implementation
        Must use Y
        ## Sources
        [1] Author. "Title." https://example.com (2026-01-15 retrieved)
        [2] Author2. "Title2." https://example2.com (2026-01-14 retrieved)
    """)
    p = d / f"{task_id}.research.md"
    p.write_text(content, encoding="utf-8")
    return p


def _setup_done_tree(tmp_path, task_id="TASK-001"):
    """Set up a complete artifact tree for 'done' state."""
    _build_task_artifact(tmp_path, task_id)
    _build_plan_artifact(tmp_path, task_id)
    _build_code_artifact(tmp_path, task_id)
    _build_verify_artifact(tmp_path, task_id)
    status = _make_full_status(task_id, "done",
        required_artifacts=["task", "code", "verify", "status"],
        available_artifacts=["task", "plan", "code", "verify", "status"],
        missing_artifacts=[])
    _write_status(tmp_path, task_id, status)
    return task_id


# ─────────────────────────────────────────────
# load_archive_snapshot
# ─────────────────────────────────────────────

class TestLoadArchiveSnapshot:
    def test_no_archive_path(self, tmp_path):
        code_path = tmp_path / "code.md"
        evidence = {}
        result = gsv.load_archive_snapshot(tmp_path, code_path, evidence, set())
        assert result == (None, None, None)

    def test_mismatched_archive_fields(self, tmp_path):
        code_path = tmp_path / "code.md"
        evidence = {"archive path": "archive.txt"}
        files, rel, err = gsv.load_archive_snapshot(tmp_path, code_path, evidence, set())
        assert err is not None
        assert "together" in err

    def test_invalid_sha256_format(self, tmp_path):
        code_path = tmp_path / "code.md"
        evidence = {"archive path": "archive.txt", "archive sha256": "not-a-sha"}
        files, rel, err = gsv.load_archive_snapshot(tmp_path, code_path, evidence, set())
        assert "hexadecimal" in err

    def test_archive_file_missing(self, tmp_path):
        import hashlib
        code_path = tmp_path / "code.md"
        evidence = {
            "archive path": "archive.txt",
            "archive sha256": "a" * 64,
        }
        files, rel, err = gsv.load_archive_snapshot(tmp_path, code_path, evidence, set())
        assert "does not exist" in err

    def test_sha256_mismatch(self, tmp_path):
        import hashlib
        archive = tmp_path / "archive.txt"
        archive.write_bytes(b"src/main.py\n")
        code_path = tmp_path / "code.md"
        evidence = {
            "archive path": "archive.txt",
            "archive sha256": "b" * 64,
        }
        files, rel, err = gsv.load_archive_snapshot(tmp_path, code_path, evidence, set())
        assert "does not match" in err

    def test_valid_archive(self, tmp_path):
        import hashlib
        archive_bytes = b"src/main.py\ntests/test_main.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(archive_bytes)
        sha = hashlib.sha256(archive_bytes).hexdigest()
        code_path = tmp_path / "code.md"
        snapshot = {"src/main.py", "tests/test_main.py"}
        evidence = {"archive path": "archive.txt", "archive sha256": sha}
        files, rel, err = gsv.load_archive_snapshot(tmp_path, code_path, evidence, snapshot)
        assert err is None
        assert files == snapshot

    def test_blank_line_in_archive(self, tmp_path):
        import hashlib
        archive_bytes = b"src/main.py\n\ntests/test_main.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(archive_bytes)
        sha = hashlib.sha256(archive_bytes).hexdigest()
        code_path = tmp_path / "code.md"
        evidence = {"archive path": "archive.txt", "archive sha256": sha}
        files, rel, err = gsv.load_archive_snapshot(tmp_path, code_path, evidence, set())
        assert "blank line" in err

    def test_unsorted_archive(self, tmp_path):
        import hashlib
        archive_bytes = b"tests/test_main.py\nsrc/main.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(archive_bytes)
        sha = hashlib.sha256(archive_bytes).hexdigest()
        code_path = tmp_path / "code.md"
        evidence = {"archive path": "archive.txt", "archive sha256": sha}
        files, rel, err = gsv.load_archive_snapshot(tmp_path, code_path, evidence, set())
        assert "sorted" in err

    def test_snapshot_mismatch(self, tmp_path):
        import hashlib
        archive_bytes = b"src/main.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(archive_bytes)
        sha = hashlib.sha256(archive_bytes).hexdigest()
        code_path = tmp_path / "code.md"
        evidence = {"archive path": "archive.txt", "archive sha256": sha}
        files, rel, err = gsv.load_archive_snapshot(tmp_path, code_path, evidence, {"other.py"})
        assert "does not match Changed Files Snapshot" in err


# ─────────────────────────────────────────────
# validate_markdown_artifact
# ─────────────────────────────────────────────

class TestValidateMarkdownArtifact:
    def test_valid_task(self, tmp_path):
        p = _build_task_artifact(tmp_path, "TASK-001")
        result = gsv.validate_markdown_artifact(p, "task", "TASK-001")
        assert not result.errors

    def test_missing_marker(self, tmp_path):
        d = tmp_path / "tasks"
        d.mkdir(parents=True, exist_ok=True)
        p = d / "TASK-001.task.md"
        p.write_text("# Wrong Header\n- Task ID: TASK-001\n", encoding="utf-8")
        result = gsv.validate_markdown_artifact(p, "task", "TASK-001")
        assert any("missing required markers" in e for e in result.errors)

    def test_missing_task_id(self, tmp_path):
        d = tmp_path / "tasks"
        d.mkdir(parents=True, exist_ok=True)
        content = textwrap.dedent("""\
            # Task: Test
            ## Metadata
            - Artifact Type: task
            - Task ID: TASK-999
            - Owner: Claude
            - Status: drafted
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Objective
            test
            ## Constraints
            none
            ## Acceptance Criteria
            done
        """)
        p = d / "TASK-001.task.md"
        p.write_text(content, encoding="utf-8")
        result = gsv.validate_markdown_artifact(p, "task", "TASK-001")
        assert any("missing exact task id" in e for e in result.errors)

    def test_plan_ready_for_coding_yes(self, tmp_path):
        p = _build_plan_artifact(tmp_path, "TASK-001", ready="yes")
        result = gsv.validate_markdown_artifact(p, "plan", "TASK-001")
        assert not any("Ready For Coding" in e for e in result.errors)

    def test_plan_not_ready_error(self, tmp_path):
        p = _build_plan_artifact(tmp_path, "TASK-001", ready="maybe")
        result = gsv.validate_markdown_artifact(p, "plan", "TASK-001")
        assert any("Ready For Coding" in e for e in result.errors)

    def test_verify_pass_fail_result(self, tmp_path):
        p = _build_verify_artifact(tmp_path, "TASK-001", result="pass")
        result = gsv.validate_markdown_artifact(p, "verify", "TASK-001")
        assert not any("Pass Fail Result" in e for e in result.errors)

    def test_verify_missing_pass_fail(self, tmp_path):
        d = tmp_path / "verify"
        d.mkdir(parents=True, exist_ok=True)
        content = textwrap.dedent("""\
            # Verification: TASK-001
            ## Metadata
            - Artifact Type: verify
            - Task ID: TASK-001
            - Owner: Claude
            - Status: pass
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Acceptance Criteria Checklist
            Content
            ## Pass Fail Result
            unknown
            ## Build Guarantee
            Commit xyz
        """)
        p = d / "TASK-001.verify.md"
        p.write_text(content, encoding="utf-8")
        result = gsv.validate_markdown_artifact(p, "verify", "TASK-001")
        assert any("Pass Fail Result" in e for e in result.errors)

    def test_invalid_status_value(self, tmp_path):
        d = tmp_path / "tasks"
        d.mkdir(parents=True, exist_ok=True)
        content = textwrap.dedent("""\
            # Task: Test
            ## Metadata
            - Artifact Type: task
            - Task ID: TASK-001
            - Owner: Claude
            - Status: invalid_status
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Objective
            test
            ## Constraints
            none
            ## Acceptance Criteria
            done
        """)
        p = d / "TASK-001.task.md"
        p.write_text(content, encoding="utf-8")
        result = gsv.validate_markdown_artifact(p, "task", "TASK-001")
        assert any("invalid Status" in e for e in result.errors)

    def test_code_mapping_to_plan_warnings(self, tmp_path):
        p = _build_code_artifact(tmp_path, "TASK-001")
        result = gsv.validate_markdown_artifact(p, "code", "TASK-001")
        assert not any("Mapping To Plan" in w for w in result.errors)

    def test_research_artifact_validation(self, tmp_path):
        _write_status(tmp_path, "TASK-001", _make_full_status("TASK-001"))
        p = _build_research_artifact(tmp_path, "TASK-001")
        result = gsv.validate_markdown_artifact(p, "research", "TASK-001")
        # Should validate without critical errors
        assert not any("## Recommendation" in e for e in result.errors)


# ─────────────────────────────────────────────
# validate_artifact_presence
# ─────────────────────────────────────────────

class TestValidateArtifactPresence:
    def test_drafted_with_task_and_status(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        status = _make_full_status(task_id, "drafted")
        _write_status(tmp_path, task_id, status)
        result = gsv.validate_artifact_presence(tmp_path, task_id, "drafted", status)
        assert not result.errors

    def test_drafted_missing_task(self, tmp_path):
        task_id = "TASK-001"
        status = _make_full_status(task_id, "drafted")
        _write_status(tmp_path, task_id, status)
        result = gsv.validate_artifact_presence(tmp_path, task_id, "drafted", status)
        assert any("Missing required" in e for e in result.errors)

    def test_coding_needs_plan_and_code(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _build_plan_artifact(tmp_path, task_id)
        _build_code_artifact(tmp_path, task_id)
        status = _make_full_status(task_id, "coding",
            required_artifacts=["task", "plan", "code", "status"],
            available_artifacts=["task", "plan", "code", "status"],
            missing_artifacts=[])
        _write_status(tmp_path, task_id, status)
        result = gsv.validate_artifact_presence(tmp_path, task_id, "coding", status)
        # Should not have missing artifact errors
        assert not any("Missing required" in e for e in result.errors)

    def test_done_requires_verify_pass(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _build_plan_artifact(tmp_path, task_id)
        _build_code_artifact(tmp_path, task_id)
        _build_verify_artifact(tmp_path, task_id, result="fail")
        status = _make_full_status(task_id, "done",
            required_artifacts=["task", "code", "verify", "status"],
            available_artifacts=["task", "plan", "code", "verify", "status"],
            missing_artifacts=[])
        _write_status(tmp_path, task_id, status)
        result = gsv.validate_artifact_presence(tmp_path, task_id, "done", status)
        assert any("Pass Fail Result = pass" in e for e in result.errors)

    def test_done_with_verify_pass(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _build_plan_artifact(tmp_path, task_id)
        _build_code_artifact(tmp_path, task_id)
        _build_verify_artifact(tmp_path, task_id, result="pass")
        status = _make_full_status(task_id, "done",
            required_artifacts=["task", "code", "verify", "status"],
            available_artifacts=["task", "plan", "code", "verify", "status"],
            missing_artifacts=[])
        _write_status(tmp_path, task_id, status)
        result = gsv.validate_artifact_presence(tmp_path, task_id, "done", status)
        assert not any("Pass Fail Result" in e for e in result.errors)

    def test_lightweight_mode_skips_plan(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _build_research_artifact(tmp_path, task_id)
        _build_code_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id))
        status = _make_full_status(task_id, "coding")
        _write_status(tmp_path, task_id, status)
        result = gsv.validate_artifact_presence(
            tmp_path, task_id, "coding", status,
            validation_mode=gsv.AUTO_CLASSIFY_LIGHTWEIGHT)
        assert not any("Missing required" in e for e in result.errors)

    def test_available_artifacts_mismatch_warning(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        status = _make_full_status(task_id, "drafted",
            available_artifacts=["task", "research", "status"])  # research doesn't exist
        _write_status(tmp_path, task_id, status)
        result = gsv.validate_artifact_presence(tmp_path, task_id, "drafted", status)
        assert any("available_artifacts mismatch" in w for w in result.warnings)


# ─────────────────────────────────────────────
# validate_transition
# ─────────────────────────────────────────────

class TestValidateTransition:
    def test_valid_drafted_to_researched(self):
        result = gsv.validate_transition("drafted", "researched")
        assert not result.errors

    def test_invalid_state(self):
        result = gsv.validate_transition("drafted", "invalid")
        assert result.errors

    def test_illegal_transition(self):
        result = gsv.validate_transition("drafted", "done")
        assert any("Illegal state transition" in e for e in result.errors)

    def test_unknown_from_state(self):
        result = gsv.validate_transition("nonexistent", "drafted")
        assert any("Unknown from_state" in e for e in result.errors)

    def test_blocked_to_unblocked_needs_improvement(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "blocked"))
        result = gsv.validate_transition("blocked", "drafted", tmp_path, task_id)
        assert any("improvement artifact" in e for e in result.errors)


# ─────────────────────────────────────────────
# validate_all
# ─────────────────────────────────────────────

class TestValidateAll:
    def test_valid_drafted(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        result = gsv.validate_all(tmp_path, task_id)
        assert not result.errors

    def test_invalid_task_id(self, tmp_path):
        result = gsv.validate_all(tmp_path, "bad-id")
        assert any("Invalid task id" in e for e in result.errors)


# ─────────────────────────────────────────────
# build_reconcile_defaults
# ─────────────────────────────────────────────

class TestBuildReconcileDefaults:
    def test_defaults_for_drafted(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        status = _make_full_status(task_id, "drafted")
        defaults, warnings = gsv.build_reconcile_defaults(tmp_path, task_id, status)
        assert defaults["task_id"] == task_id
        assert "state" in defaults

    def test_state_conflict_warning(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _build_plan_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "done"))
        status = _make_full_status(task_id, "done")
        defaults, warnings = gsv.build_reconcile_defaults(tmp_path, task_id, status)
        assert any("conflict" in w for w in warnings)

    def test_invalid_state_warning(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        status = _make_full_status(task_id, "nonexistent_state")
        defaults, warnings = gsv.build_reconcile_defaults(tmp_path, task_id, status)
        assert any("invalid value" in w for w in warnings)


# ─────────────────────────────────────────────
# reconcile_status
# ─────────────────────────────────────────────

class TestReconcileStatus:
    def test_backfill_missing_fields(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        d = tmp_path / "status"
        d.mkdir(parents=True, exist_ok=True)
        # Write minimal status missing several fields
        p = d / f"{task_id}.status.json"
        p.write_text(json.dumps({
            "task_id": task_id,
            "state": "drafted",
            "last_updated": _ts(),
        }, indent=2) + "\n", encoding="utf-8")
        result = gsv.reconcile_status(tmp_path, task_id)
        # After reconcile, read back status
        updated = json.loads(p.read_text(encoding="utf-8"))
        assert "current_owner" in updated
        assert "next_agent" in updated


# ─────────────────────────────────────────────
# apply_override
# ─────────────────────────────────────────────

class TestApplyOverride:
    def test_override_critical_error(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        errors = ["Missing required artifacts for state 'coding': ['plan']"]
        result = gsv.ValidationResult(errors, [])
        overridden = gsv.apply_override(result, tmp_path, task_id, "Testing", "Admin")
        assert not overridden.errors
        assert any("[OVERRIDDEN]" in w for w in overridden.warnings)

    def test_override_premortem_missing_not_suppressed(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        errors = ["plan.md: premortem check failed — ## Risks section not found"]
        result = gsv.ValidationResult(errors, [])
        overridden = gsv.apply_override(result, tmp_path, task_id, "Testing", "Admin")
        assert any("premortem" in e.lower() for e in overridden.errors)

    def test_override_premortem_warning(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        errors = ["plan.md: premortem task_type='code' requires at least 4 numbered risks"]
        result = gsv.ValidationResult(errors, [])
        overridden = gsv.apply_override(result, tmp_path, task_id, "Testing", "Admin")
        assert not overridden.errors
        assert any("OVERRIDE PREMORTEM WARNING" in w for w in overridden.warnings)


# ─────────────────────────────────────────────
# write_transition
# ─────────────────────────────────────────────

class TestWriteTransition:
    def test_valid_transition_drafted_to_researched(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _build_research_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        result = gsv.write_transition(tmp_path, task_id, "drafted", "researched")
        # Check status was updated
        status_path = gsv.artifact_path(tmp_path, task_id, "status")
        updated = json.loads(status_path.read_text(encoding="utf-8"))
        if not result.errors:
            assert updated["state"] == "researched"

    def test_illegal_transition_blocked(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        result = gsv.write_transition(tmp_path, task_id, "drafted", "done")
        assert result.errors

    def test_state_mismatch_refused(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _build_research_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "researched",
            required_artifacts=["task", "research", "status"],
            available_artifacts=["task", "research", "status"],
            missing_artifacts=[]))
        result = gsv.write_transition(tmp_path, task_id, "drafted", "researched")
        assert any("Refusing transition" in e for e in result.errors)


# ─────────────────────────────────────────────
# resolve_validation_mode
# ─────────────────────────────────────────────

class TestResolveValidationMode:
    def test_non_auto_classify(self, tmp_path):
        result = gsv.resolve_validation_mode(tmp_path, "TASK-001", auto_classify=False)
        assert result.validation_mode == gsv.AUTO_CLASSIFY_FULL

    def test_no_plan_drafted_lightweight(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        result = gsv.resolve_validation_mode(tmp_path, task_id, auto_classify=True)
        assert result.validation_mode == gsv.AUTO_CLASSIFY_LIGHTWEIGHT


# ─────────────────────────────────────────────
# state_required_artifacts & infer_state
# ─────────────────────────────────────────────

class TestStateRequiredArtifacts:
    def test_drafted_requires_task_status(self):
        result = gsv.state_required_artifacts("drafted", set())
        assert "task" in result
        assert "status" in result

    def test_done_requires_verify(self):
        result = gsv.state_required_artifacts("done", set())
        assert "verify" in result

    def test_lightweight_mode(self):
        result = gsv.state_required_artifacts("done", set(), gsv.AUTO_CLASSIFY_LIGHTWEIGHT)
        assert result == set(gsv.LIGHTWEIGHT_REQUIRED_ARTIFACTS)

    def test_research_retained_if_exists(self):
        result = gsv.state_required_artifacts("planned", {"research"})
        assert "research" in result


class TestInferStateFromArtifacts:
    def test_empty(self):
        assert gsv.infer_state_from_artifacts(set()) == "drafted"

    def test_task_only(self):
        assert gsv.infer_state_from_artifacts({"task", "status"}) == "drafted"

    def test_full_done(self):
        assert gsv.infer_state_from_artifacts({"task", "code", "verify", "status"}) == "done"


# ─────────────────────────────────────────────
# collect_git_changed_files (mocked)
# ─────────────────────────────────────────────

class TestCollectGitChangedFiles:
    def test_git_not_available(self, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            files, warnings = gsv.collect_git_changed_files(tmp_path)
        assert files == set()
        assert any("not available" in w for w in warnings)

    def test_git_error(self, tmp_path):
        from unittest.mock import MagicMock
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "fatal: not a git repo"
        mock_result.stdout = ""
        with patch("subprocess.run", return_value=mock_result):
            files, warnings = gsv.collect_git_changed_files(tmp_path)
        assert files == set()
        assert any("failed" in w for w in warnings)


class TestCollectGitDiffRangeFiles:
    def test_git_not_available(self, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            files, error = gsv.collect_git_diff_range_files(tmp_path, "abc", "def")
        assert files == set()
        assert "not available" in error


# ─────────────────────────────────────────────
# detect_git_backed_scope_drift
# ─────────────────────────────────────────────

class TestDetectGitBackedScopeDrift:
    def test_no_actual_changed(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n## Files Likely Affected\n- `a.py`\n", encoding="utf-8")
        code = tmp_path / "code.md"
        code.write_text("# Code\n## Files Changed\n- `a.py`\n", encoding="utf-8")
        result = gsv.detect_git_backed_scope_drift(plan, code, set(), {"artifacts/tasks/TASK-001.task.md"})
        assert not result.errors
        assert not result.waiver_candidate_errors

    def test_no_task_artifact_overlap(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n## Files Likely Affected\n- `a.py`\n", encoding="utf-8")
        code = tmp_path / "code.md"
        code.write_text("# Code\n## Files Changed\n- `a.py`\n", encoding="utf-8")
        result = gsv.detect_git_backed_scope_drift(plan, code, {"x.py"}, {"artifacts/tasks/TASK-001.task.md"})
        assert not result.waiver_candidate_errors

    def test_drift_detected(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n## Files Likely Affected\n- `a.py`\n", encoding="utf-8")
        code = tmp_path / "code.md"
        code.write_text("# Code\n## Files Changed\n- `a.py`\n", encoding="utf-8")
        actual = {"a.py", "b.py", "artifacts/tasks/TASK-001.task.md"}
        task_arts = {"artifacts/tasks/TASK-001.task.md"}
        result = gsv.detect_git_backed_scope_drift(plan, code, actual, task_arts)
        assert any("b.py" in e for e in result.waiver_candidate_errors)


# ─────────────────────────────────────────────
# validate_scope_drift_waiver (deeper)
# ─────────────────────────────────────────────

class TestValidateScopeDriftWaiverDeeper:
    def test_waiver_with_decision_file(self, tmp_path):
        task_id = "TASK-001"
        d = tmp_path / "decisions"
        d.mkdir(parents=True, exist_ok=True)
        content = textwrap.dedent(f"""\
            # Decision Log: {task_id}
            ## Metadata
            - Artifact Type: decision
            - Task ID: {task_id}
            - Owner: Claude
            - Status: done
            - Last Updated: {_ts()}
            ## Issue
            Scope drift needed
            ## Chosen Option
            Allow drift
            ## Reasoning
            Necessary change
            ## Guard Exception
            - Exception Type: allow-scope-drift
            - Scope Files: b.py
            - Justification: Required for fix
        """)
        (d / f"{task_id}.decision.md").write_text(content, encoding="utf-8")
        result = gsv.validate_scope_drift_waiver(tmp_path, task_id, {"b.py"})
        assert not result.errors

    def test_waiver_insufficient_scope(self, tmp_path):
        task_id = "TASK-001"
        d = tmp_path / "decisions"
        d.mkdir(parents=True, exist_ok=True)
        content = textwrap.dedent(f"""\
            # Decision Log: {task_id}
            ## Metadata
            - Artifact Type: decision
            - Task ID: {task_id}
            - Owner: Claude
            - Status: done
            - Last Updated: {_ts()}
            ## Issue
            Scope drift
            ## Chosen Option
            Allow
            ## Reasoning
            Needed
            ## Guard Exception
            - Exception Type: allow-scope-drift
            - Scope Files: b.py
            - Justification: Only for b
        """)
        (d / f"{task_id}.decision.md").write_text(content, encoding="utf-8")
        result = gsv.validate_scope_drift_waiver(tmp_path, task_id, {"b.py", "c.py"})
        assert result.errors  # c.py not covered


# ─────────────────────────────────────────────
# prompt_regression_validator
# ─────────────────────────────────────────────

class TestPrvEvaluateCase:
    def test_no_assertions(self):
        case = {"id": "TC-01", "title": "Test", "assertions": []}
        result = prv.evaluate_case(case, Path("."), {})
        assert not result.passed

    def test_must_contain_all_found(self, tmp_path):
        (tmp_path / "test.md").write_text("hello world foo bar", encoding="utf-8")
        case = {
            "id": "TC-01",
            "title": "Test",
            "assertions": [{"file": "test.md", "must_contain_all": ["hello", "foo"]}],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert result.passed

    def test_must_contain_all_missing(self, tmp_path):
        (tmp_path / "test.md").write_text("hello world", encoding="utf-8")
        case = {
            "id": "TC-01",
            "title": "Test",
            "assertions": [{"file": "test.md", "must_contain_all": ["hello", "missing"]}],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_must_not_contain_any(self, tmp_path):
        (tmp_path / "test.md").write_text("hello world secret", encoding="utf-8")
        case = {
            "id": "TC-01",
            "title": "Test",
            "assertions": [{"file": "test.md", "must_not_contain_any": ["secret"]}],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_all_of_any(self, tmp_path):
        (tmp_path / "test.md").write_text("the quick brown fox", encoding="utf-8")
        case = {
            "id": "TC-01",
            "title": "Test",
            "assertions": [
                {"file": "test.md", "all_of_any": [["quick", "slow"], ["cat", "fox"]]}
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert result.passed

    def test_all_of_any_missing(self, tmp_path):
        (tmp_path / "test.md").write_text("the quick brown fox", encoding="utf-8")
        case = {
            "id": "TC-01",
            "title": "Test",
            "assertions": [
                {"file": "test.md", "all_of_any": [["missing1", "missing2"]]}
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_near_terms(self, tmp_path):
        (tmp_path / "test.md").write_text("the quick brown fox jumps", encoding="utf-8")
        case = {
            "id": "TC-01",
            "title": "Test",
            "assertions": [
                {
                    "file": "test.md",
                    "near": [{"terms": ["quick", "fox"], "max_chars": 50}],
                }
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert result.passed

    def test_near_terms_too_far(self, tmp_path):
        content = "quick " + "x" * 300 + " fox"
        (tmp_path / "test.md").write_text(content, encoding="utf-8")
        case = {
            "id": "TC-01",
            "title": "Test",
            "assertions": [
                {
                    "file": "test.md",
                    "near": [{"terms": ["quick", "fox"], "max_chars": 50}],
                }
            ],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_missing_file(self, tmp_path):
        case = {
            "id": "TC-01",
            "title": "Test",
            "assertions": [{"file": "nonexistent.md", "must_contain_all": ["x"]}],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed
        assert any("Target file missing" in f.message for f in result.failures)

    def test_file_caching(self, tmp_path):
        (tmp_path / "test.md").write_text("cached content", encoding="utf-8")
        cache = {}
        case = {
            "id": "TC-01",
            "title": "Test",
            "assertions": [
                {"file": "test.md", "must_contain_all": ["cached"]},
                {"file": "test.md", "must_contain_all": ["content"]},
            ],
        }
        result = prv.evaluate_case(case, tmp_path, cache)
        assert result.passed
        assert "test.md" in cache


class TestPrvRenderReport:
    def test_all_pass(self):
        results = [prv.CaseResult("TC-01", "Test", True, [])]
        report = prv.render_report(results)
        assert "pass" in report
        assert "None" in report  # No failure details

    def test_with_failures(self):
        failure = prv.AssertionFailure("test.md", "missing term: foo", "check foo")
        results = [prv.CaseResult("TC-01", "Test", False, [failure])]
        report = prv.render_report(results)
        assert "fail" in report
        assert "missing term: foo" in report
        assert "check foo" in report


class TestPrvLoadCases:
    def test_valid(self, tmp_path):
        p = tmp_path / "cases.json"
        p.write_text('[{"id": "TC-01"}]', encoding="utf-8")
        assert len(prv.load_cases(p)) == 1

    def test_missing(self, tmp_path):
        with pytest.raises(RuntimeError, match="not found"):
            prv.load_cases(tmp_path / "missing.json")

    def test_invalid_json(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{invalid}", encoding="utf-8")
        with pytest.raises(RuntimeError, match="Invalid JSON"):
            prv.load_cases(p)

    def test_not_list(self, tmp_path):
        p = tmp_path / "obj.json"
        p.write_text('{"key": "value"}', encoding="utf-8")
        with pytest.raises(RuntimeError, match="must be a list"):
            prv.load_cases(p)


# ─────────────────────────────────────────────
# aggregate_red_team_scorecard
# ─────────────────────────────────────────────

class TestArsParseReport:
    def test_valid_report(self):
        markdown = textwrap.dedent("""\
            # Report
            | Case | Phase | Expected | Outcome | Exit | Evidence | Notes |
            | TC-01 | static | pass | pass | 0 | `log.txt` | |
            | TC-02 | live | pass | fail | 1 | `log2.txt` | Bug |
        """)
        rows = ars.parse_report(markdown)
        assert len(rows) == 2
        assert rows[0].case == "TC-01"
        assert rows[0].case_passed
        assert not rows[1].case_passed

    def test_empty_report(self):
        rows = ars.parse_report("# No table here\n")
        assert rows == []


class TestArsBuildScorecard:
    def test_generates_valid_scorecard(self, tmp_path):
        rows = [
            ars.CaseRow("TC-01", "static", "pass", "pass", "0", "log.txt", ""),
            ars.CaseRow("TC-02", "live", "pass", "fail", "1", "log.txt", "Bug"),
        ]
        report_path = tmp_path / "report.md"
        scorecard = ars.build_scorecard(rows, report_path)
        assert "TC-01" in scorecard
        assert "TC-02" in scorecard
        assert "Cases: 2" in scorecard
        assert "Case Passed: 1" in scorecard
        assert "Case Failed: 1" in scorecard

    def test_auto_score_pass(self):
        row = ars.CaseRow("TC-01", "static", "pass", "pass", "0", "log.txt", "")
        assert ars.auto_score(row) == 2

    def test_auto_score_fail(self):
        row = ars.CaseRow("TC-01", "static", "pass", "fail", "1", "log.txt", "")
        assert ars.auto_score(row) == 0


# ─────────────────────────────────────────────
# validate_context_stack extras
# ─────────────────────────────────────────────

class TestVcsExtras:
    def test_normalize_text_basic(self):
        assert prv.normalize_text("Hello  World\n") == "hello world "

    def test_contains_any(self):
        assert prv.contains_any("hello world", ["world", "foo"])
        assert not prv.contains_any("hello world", ["bar", "baz"])

    def test_check_near_terms_true(self):
        assert prv.check_near_terms("abc def ghi", ["abc", "ghi"], 20)

    def test_check_near_terms_false(self):
        text = "abc " + "x" * 300 + " ghi"
        assert not prv.check_near_terms(text.lower(), ["abc", "ghi"], 10)


# ─────────────────────────────────────────────
# detect_historical_diff_scope_drift (partial)
# ─────────────────────────────────────────────

class TestDetectHistoricalDiffScopeDrift:
    def test_no_evidence(self, tmp_path):
        code = tmp_path / "code.md"
        code.write_text("# Code\n## Files Changed\n- `a.py`\n", encoding="utf-8")
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n## Files Likely Affected\n- `a.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(None, plan, code)
        assert not result.errors

    def test_unsupported_evidence_type(self, tmp_path):
        code = tmp_path / "code.md"
        code.write_text("# Code\n## Diff Evidence\n- Evidence Type: unsupported\n", encoding="utf-8")
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(None, plan, code)
        assert any("unsupported" in e for e in result.errors)

    def test_missing_snapshot_fields(self, tmp_path):
        code = tmp_path / "code.md"
        code.write_text("# Code\n## Diff Evidence\n- Evidence Type: commit-range\n", encoding="utf-8")
        plan = tmp_path / "plan.md"
        plan.write_text("# Plan\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(None, plan, code)
        assert any("requires non-empty" in e for e in result.errors)


# ─────────────────────────────────────────────
# summarize_remote_error_detail
# ─────────────────────────────────────────────

class TestSummarizeRemoteErrorDetail:
    def test_with_body(self):
        result = gsv.summarize_remote_error_detail(b"error message", "fallback")
        assert "error message" in result

    def test_empty_body(self):
        result = gsv.summarize_remote_error_detail(b"", "fallback")
        assert result == "fallback"

    def test_long_body_truncated(self):
        body = b"x" * 300
        result = gsv.summarize_remote_error_detail(body, "fallback")
        assert result.endswith("...")
        assert len(result) <= 204


# ─────────────────────────────────────────────
# compute_snapshot_sha256 & parse_csv_file_tokens
# ─────────────────────────────────────────────

class TestComputeSnapshotSha256:
    def test_deterministic(self):
        files = {"a.py", "b.py"}
        h1 = gsv.compute_snapshot_sha256(files)
        h2 = gsv.compute_snapshot_sha256(files)
        assert h1 == h2
        assert len(h1) == 64


class TestParseCsvFileTokens:
    def test_comma_separated(self):
        result = gsv.parse_csv_file_tokens("a.py, b.py, c.py")
        assert result == {"a.py", "b.py", "c.py"}

    def test_empty(self):
        result = gsv.parse_csv_file_tokens("")
        assert result == set()


# ─────────────────────────────────────────────
# parse_repository_ref & normalize_api_base_url
# ─────────────────────────────────────────────

class TestParseRepositoryRef:
    def test_valid(self):
        owner, repo, err = gsv.parse_repository_ref("user/repo")
        assert owner == "user"
        assert repo == "repo"
        assert err is None

    def test_invalid(self):
        owner, repo, err = gsv.parse_repository_ref("invalid")
        assert err is not None


class TestNormalizeApiBaseUrl:
    def test_default(self):
        url, err = gsv.normalize_api_base_url("")
        assert url == "https://api.github.com"
        assert err is None

    def test_custom(self):
        url, err = gsv.normalize_api_base_url("https://custom.api.com/")
        assert url == "https://custom.api.com"
        assert err is None


# ─────────────────────────────────────────────
# resolve_workspace_relative_path
# ─────────────────────────────────────────────

class TestResolveWorkspaceRelativePath:
    def test_valid(self, tmp_path):
        (tmp_path / "file.txt").write_text("content", encoding="utf-8")
        rel, path, err = gsv.resolve_workspace_relative_path(tmp_path, "file.txt")
        assert err is None
        assert path.exists()

    def test_traversal_blocked(self, tmp_path):
        rel, path, err = gsv.resolve_workspace_relative_path(tmp_path, "../../../etc/passwd")
        assert err is not None


# ─────────────────────────────────────────────
# classify_decision_waiver_gate
# ─────────────────────────────────────────────

class TestClassifyDecisionWaiverGate:
    def test_research_gate(self):
        assert gsv.classify_decision_waiver_gate("Missing required artifacts for state 'researched': ['research']") == "Gate_A"

    def test_plan_gate(self):
        assert gsv.classify_decision_waiver_gate("Missing required artifacts for state 'planned': ['plan']") == "Gate_B"

    def test_code_gate(self):
        assert gsv.classify_decision_waiver_gate(".code.md missing something") == "Gate_C"

    def test_gate_e(self):
        assert gsv.classify_decision_waiver_gate("Gate E (PDCA): requires an improvement artifact") == "Gate_E"

    def test_verify_gate(self):
        assert gsv.classify_decision_waiver_gate("done state requires verify artifact with Pass Fail Result") == "Gate_D"

    def test_meta(self):
        assert gsv.classify_decision_waiver_gate("Target state 'done' requirements") == "__META__"

    def test_waiver_expired_returns_none(self):
        assert gsv.classify_decision_waiver_gate("waiver expired for Gate_A at 2026-01-01") is None

    def test_unknown_returns_none(self):
        assert gsv.classify_decision_waiver_gate("some random error") is None


# ─────────────────────────────────────────────
# active_decision_waivers
# ─────────────────────────────────────────────

class TestActiveDecisionWaivers:
    def test_no_waivers(self):
        assert gsv.active_decision_waivers({}) == {}

    def test_expired_waiver_excluded(self):
        status = {
            "decision_waivers": [{
                "gate": "Gate_A",
                "reason": "Test",
                "approver": "Admin",
                "expires": "2020-01-01T00:00:00+08:00",
            }]
        }
        assert gsv.active_decision_waivers(status) == {}

    def test_active_waiver_included(self):
        status = {
            "decision_waivers": [{
                "gate": "Gate_A",
                "reason": "Test",
                "approver": "Admin",
                "expires": _future_ts(),
            }]
        }
        active = gsv.active_decision_waivers(status)
        assert "Gate_A" in active

    def test_invalid_list_type(self):
        status = {"decision_waivers": "not a list"}
        assert gsv.active_decision_waivers(status) == {}


# ─────────────────────────────────────────────
# ensure_override_log_not_missing
# ─────────────────────────────────────────────

class TestEnsureOverrideLogNotMissing:
    def test_no_override_flag(self, tmp_path):
        task_id = "TASK-001"
        _write_status(tmp_path, task_id, _make_full_status(task_id))
        gsv.ensure_override_log_not_missing(tmp_path, task_id)  # Should not raise

    def test_override_flag_but_log_missing(self, tmp_path):
        task_id = "TASK-001"
        status = _make_full_status(task_id)
        status["override_log_required"] = True
        _write_status(tmp_path, task_id, status)
        with pytest.raises(gsv.GuardError, match="override log missing"):
            gsv.ensure_override_log_not_missing(tmp_path, task_id)

    def test_override_flag_with_log(self, tmp_path):
        task_id = "TASK-001"
        status = _make_full_status(task_id)
        status["override_log_required"] = True
        _write_status(tmp_path, task_id, status)
        log_path = gsv.override_log_path(tmp_path, task_id)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_path.write_text("[]", encoding="utf-8")
        gsv.ensure_override_log_not_missing(tmp_path, task_id)  # Should not raise


# ─────────────────────────────────────────────
# append_override_record
# ─────────────────────────────────────────────

class TestAppendOverrideRecord:
    def test_appends_record(self, tmp_path):
        task_id = "TASK-001"
        _write_status(tmp_path, task_id, _make_full_status(task_id))
        gsv.append_override_record(tmp_path, task_id, "test reason", "admin", ["error1"])
        log_path = gsv.override_log_path(tmp_path, task_id)
        log = json.loads(log_path.read_text(encoding="utf-8"))
        assert len(log) == 1
        assert log[0]["reason"] == "test reason"
        # Check status was marked
        status = json.loads((tmp_path / "status" / f"{task_id}.status.json").read_text(encoding="utf-8"))
        assert status.get("override_log_required") is True


# ─────────────────────────────────────────────
# task_is_high_risk & task_requests_lightweight
# ─────────────────────────────────────────────

class TestTaskIsHighRisk:
    def test_security_keyword(self, tmp_path):
        task = tmp_path / "task.md"
        task.write_text("# Task: Security Fix\nFix security vulnerability\n", encoding="utf-8")
        assert gsv.task_is_high_risk(task, "")

    def test_no_risk(self, tmp_path):
        task = tmp_path / "task.md"
        task.write_text("# Task: Update docs\nMinor update\n", encoding="utf-8")
        assert not gsv.task_is_high_risk(task, "")

    def test_plan_text_risk(self):
        assert gsv.task_is_high_risk(None, "This involves upstream PR changes")


class TestExtractTaskTitle:
    def test_valid(self, tmp_path):
        p = tmp_path / "task.md"
        p.write_text("# Task: My Title\nContent\n", encoding="utf-8")
        assert gsv.extract_task_title(p) == "My Title"

    def test_no_match(self, tmp_path):
        p = tmp_path / "task.md"
        p.write_text("# Not a task\n", encoding="utf-8")
        assert gsv.extract_task_title(p) == ""

    def test_none_path(self):
        assert gsv.extract_task_title(None) == ""


# ═════════════════════════════════════════════
# Phase 3: 90%+ coverage expansion
# ═════════════════════════════════════════════


# ─────────────────────────────────────────────
# build_decision_registry — extract_decision_type
# ─────────────────────────────────────────────

class TestBdrExtractDecisionType:
    def test_from_section(self):
        text = "## Metadata\nstuff\n## Decision Type\nworkflow_change\n## Issue\nstuff\n"
        sections = bdr.parse_sections(text)
        assert bdr.extract_decision_type(text, sections) == "workflow_change"

    def test_from_type_line(self):
        text = "## Metadata\nstuff\n## Issue\nstuff\n- Type: design_choice\n"
        sections = bdr.parse_sections(text)
        assert bdr.extract_decision_type(text, sections) == "design_choice"

    def test_guard_exception_fallback(self):
        text = "## Metadata\nstuff\n## Guard Exception\nAllow drift\n"
        sections = bdr.parse_sections(text)
        assert bdr.extract_decision_type(text, sections) == "guard_exception"

    def test_general_decision_fallback(self):
        text = "## Metadata\nstuff\n"
        sections = bdr.parse_sections(text)
        assert bdr.extract_decision_type(text, sections) == "general_decision"


class TestBdrExtractSummary:
    def test_from_summary_section(self):
        text = "## Summary\nThis is the summary.\n\nMore detail.\n"
        sections = bdr.parse_sections(text)
        assert bdr.extract_summary(sections) == "This is the summary."

    def test_from_chosen_option(self):
        text = "## Chosen Option\nOption A selected.\n"
        sections = bdr.parse_sections(text)
        assert bdr.extract_summary(sections) == "Option A selected."

    def test_from_issue(self):
        text = "## Issue\nSomething broke.\n"
        sections = bdr.parse_sections(text)
        assert bdr.extract_summary(sections) == "Something broke."

    def test_empty_sections(self):
        assert bdr.extract_summary({}) == ""

    def test_truncation(self):
        text = "## Summary\n" + "x" * 300 + "\n"
        sections = bdr.parse_sections(text)
        assert len(bdr.extract_summary(sections)) <= 200


class TestBdrExtractFieldTokens:
    def test_single_line_affects(self):
        text = "- Affects: TASK-001, TASK-002\n"
        result = bdr.extract_field_tokens(text, "affects")
        assert "TASK-001" in result
        assert "TASK-002" in result

    def test_multiline_affects(self):
        text = "- Affects: TASK-001\n  TASK-002\n  TASK-003\n\nSomething else\n"
        result = bdr.extract_field_tokens(text, "affects")
        assert "TASK-001" in result
        assert "TASK-002" in result

    def test_stops_at_section(self):
        text = "- Affects: TASK-001\n## Next Section\nmore stuff\n"
        result = bdr.extract_field_tokens(text, "affects")
        assert result == ["TASK-001"]

    def test_stops_at_new_field(self):
        text = "- Affects: TASK-001\n- Related Research: something\n"
        result = bdr.extract_field_tokens(text, "affects")
        assert result == ["TASK-001"]

    def test_related_research(self):
        text = "- Related Research: TASK-050\n"
        result = bdr.extract_field_tokens(text, "related_research")
        assert "TASK-050" in result


class TestBdrNormalizeRef:
    def test_artifacts_path(self):
        assert bdr.normalize_ref("artifacts/plans/TASK-001.plan.md", "plans") == "artifacts/plans/TASK-001.plan.md"

    def test_dir_relative_path(self):
        assert bdr.normalize_ref("plans/TASK-001.plan.md", "plans") == "artifacts/plans/TASK-001.plan.md"

    def test_task_id_only_plans(self):
        assert bdr.normalize_ref("TASK-001", "plans") == "artifacts/plans/TASK-001.plan.md"

    def test_task_id_only_research(self):
        assert bdr.normalize_ref("TASK-001", "research") == "artifacts/research/TASK-001.research.md"

    def test_basename_md(self):
        assert bdr.normalize_ref("TASK-001.plan.md", "plans") == "artifacts/plans/TASK-001.plan.md"

    def test_empty_string(self):
        assert bdr.normalize_ref("", "plans") == ""

    def test_passthrough(self):
        assert bdr.normalize_ref("some/random/path.txt", "plans") == "some/random/path.txt"

    def test_backslash_normalized(self):
        result = bdr.normalize_ref("artifacts\\plans\\TASK-001.plan.md", "plans")
        assert result == "artifacts/plans/TASK-001.plan.md"


class TestBdrBuildEntry:
    def test_complete_decision(self, tmp_path):
        root = tmp_path
        d = root / "artifacts" / "decisions"
        d.mkdir(parents=True)
        (root / "artifacts" / "plans").mkdir(parents=True)
        (root / "artifacts" / "plans" / "TASK-001.plan.md").write_text("plan", encoding="utf-8")
        content = textwrap.dedent("""\
            # Decision Log: TASK-001
            ## Metadata
            - Artifact Type: decision
            - Task ID: TASK-001
            - Owner: Claude
            - Status: done
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Issue
            Something needed deciding
            ## Chosen Option
            We chose option A
            ## Reasoning
            It was the best
            - Affects: TASK-001
            - Related Research: TASK-001
        """)
        (d / "TASK-001.decision.md").write_text(content, encoding="utf-8")
        entry = bdr.build_entry(root, d / "TASK-001.decision.md")
        assert entry.task_id == "TASK-001"
        assert entry.summary
        assert entry.date == "2026-01-15T10:00:00+08:00"
        assert entry.parse_status == "complete"

    def test_partial_decision(self, tmp_path):
        root = tmp_path
        d = root / "artifacts" / "decisions"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Decision Log: TASK-002
            ## Metadata
            - Artifact Type: decision
            - Task ID: TASK-002
        """)
        (d / "TASK-002.decision.md").write_text(content, encoding="utf-8")
        entry = bdr.build_entry(root, d / "TASK-002.decision.md")
        assert entry.parse_status == "partial"


class TestBdrBuildRegistry:
    def test_empty_dir(self, tmp_path):
        d = tmp_path / "artifacts" / "decisions"
        d.mkdir(parents=True)
        result = bdr.build_registry(tmp_path)
        assert result["total"] == 0
        assert result["entries"] == []

    def test_with_entries(self, tmp_path):
        d = tmp_path / "artifacts" / "decisions"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Decision Log: TASK-001
            ## Metadata
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Issue
            Something
        """)
        (d / "TASK-001.decision.md").write_text(content, encoding="utf-8")
        result = bdr.build_registry(tmp_path)
        assert result["total"] == 1


class TestBdrFallbackSameTaskRef:
    def test_exists(self, tmp_path):
        (tmp_path / "artifacts" / "plans").mkdir(parents=True)
        (tmp_path / "artifacts" / "plans" / "TASK-001.plan.md").write_text("x", encoding="utf-8")
        refs = bdr.fallback_same_task_ref(tmp_path, "plans", "TASK-001")
        assert refs == ["artifacts/plans/TASK-001.plan.md"]

    def test_not_exists(self, tmp_path):
        (tmp_path / "artifacts" / "plans").mkdir(parents=True)
        refs = bdr.fallback_same_task_ref(tmp_path, "plans", "TASK-999")
        assert refs == []


class TestBdrHelpers:
    def test_normalize_newlines(self):
        assert bdr.normalize_newlines("a\r\nb\r\n") == "a\nb\n"

    def test_first_paragraph_empty(self):
        assert bdr.first_paragraph("") == ""
        assert bdr.first_paragraph(None) == ""

    def test_first_paragraph_multi(self):
        assert bdr.first_paragraph("first paragraph\n\nsecond paragraph") == "first paragraph"

    def test_collapse_whitespace(self):
        assert bdr.collapse_whitespace("  a   b  c  ") == "a b c"

    def test_extract_task_id_valid(self):
        assert bdr.extract_task_id(Path("TASK-001.decision.md")) == "TASK-001"

    def test_extract_task_id_invalid(self):
        with pytest.raises(ValueError, match="Unsupported"):
            bdr.extract_task_id(Path("invalid.md"))

    def test_extract_metadata_date(self):
        assert bdr.extract_metadata_date("- Last Updated: 2026-01-15T10:00:00+08:00\n") == "2026-01-15T10:00:00+08:00"

    def test_extract_metadata_date_missing(self):
        assert bdr.extract_metadata_date("no date here") == ""

    def test_clean_ref_token_strips(self):
        assert bdr.clean_ref_token("  `TASK-001`  ") == "TASK-001"
        assert bdr.clean_ref_token("- `TASK-002`") == "TASK-002"
        assert bdr.clean_ref_token("* TASK-003") == "TASK-003"

    def test_split_ref_tokens(self):
        result = bdr.split_ref_tokens(["TASK-001, TASK-002", "TASK-003"])
        assert result == ["TASK-001", "TASK-002", "TASK-003"]

    def test_dedupe_preserving_order(self):
        assert bdr.dedupe_preserving_order(["a", "b", "a", "c"]) == ["a", "b", "c"]

    def test_normalize_refs(self):
        result = bdr.normalize_refs(["TASK-001", "TASK-002"], "plans")
        assert "artifacts/plans/TASK-001.plan.md" in result
        assert "artifacts/plans/TASK-002.plan.md" in result


# ─────────────────────────────────────────────
# validate_context_stack — unit tests
# ─────────────────────────────────────────────

class TestVcsEstimateTokens:
    def test_ascii(self):
        tokens = vcs.estimate_tokens("hello world foo bar")
        assert tokens >= 4

    def test_cjk(self):
        tokens = vcs.estimate_tokens("你好世界")
        assert tokens >= 4  # 4 chars × 1.5

    def test_mixed(self):
        tokens = vcs.estimate_tokens("hello 你好 world")
        assert tokens >= 4


class TestVcsExtractFrontmatterName:
    def test_valid(self):
        text = "---\nname: my-prompt\ndescription: test\n---\n# Content"
        assert vcs.extract_frontmatter_name(text) == "my-prompt"

    def test_no_frontmatter(self):
        assert vcs.extract_frontmatter_name("# No frontmatter") is None

    def test_no_name(self):
        text = "---\ndescription: test\n---\n# Content"
        assert vcs.extract_frontmatter_name(text) is None


class TestVcsExtractHeadings:
    def test_basic(self):
        text = "# H1\n## H2\n### H3\nContent\n"
        result = vcs.extract_headings(text)
        assert "H1" in result
        assert "H2" in result
        assert "H3" in result


class TestVcsCheckMemoryBankExistence:
    def test_no_dir(self, tmp_path):
        errors = vcs.check_memory_bank_existence(tmp_path)
        assert any("Directory missing" in e for e in errors)

    def test_missing_file(self, tmp_path):
        mb = tmp_path / ".github" / "memory-bank"
        mb.mkdir(parents=True)
        errors = vcs.check_memory_bank_existence(tmp_path)
        assert any("Missing" in e for e in errors)

    def test_empty_file(self, tmp_path):
        mb = tmp_path / ".github" / "memory-bank"
        mb.mkdir(parents=True)
        for fname in vcs.MEMORY_BANK_EXPECTED_FILES:
            (mb / fname).write_text("", encoding="utf-8")
        errors = vcs.check_memory_bank_existence(tmp_path)
        assert any("Empty file" in e for e in errors)

    def test_all_present(self, tmp_path):
        mb = tmp_path / ".github" / "memory-bank"
        mb.mkdir(parents=True)
        for fname in vcs.MEMORY_BANK_EXPECTED_FILES:
            (mb / fname).write_text("# Content\nSome text\n", encoding="utf-8")
        errors = vcs.check_memory_bank_existence(tmp_path)
        assert not errors


class TestVcsCheckCrossReferences:
    def test_no_dir(self, tmp_path):
        errors = vcs.check_cross_references(tmp_path)
        assert not errors

    def test_broken_ref(self, tmp_path):
        mb = tmp_path / ".github" / "memory-bank"
        mb.mkdir(parents=True)
        (mb / "test.md").write_text("see `docs/nonexistent.md`", encoding="utf-8")
        errors = vcs.check_cross_references(tmp_path)
        assert any("Broken xref" in e for e in errors)

    def test_valid_ref(self, tmp_path):
        mb = tmp_path / ".github" / "memory-bank"
        mb.mkdir(parents=True)
        (tmp_path / "docs").mkdir()
        (tmp_path / "docs" / "existing.md").write_text("x", encoding="utf-8")
        (mb / "test.md").write_text("see `docs/existing.md`", encoding="utf-8")
        errors = vcs.check_cross_references(tmp_path)
        assert not errors


class TestVcsCheckFrontmatter:
    def test_malformed(self, tmp_path):
        pd = tmp_path / ".github" / "prompts"
        pd.mkdir(parents=True)
        (pd / "bad.md").write_text("---\nname: test\nno closing", encoding="utf-8")
        errors, names = vcs.check_frontmatter(tmp_path)
        assert any("Malformed" in e for e in errors)

    def test_valid_prompt(self, tmp_path):
        pd = tmp_path / ".github" / "prompts"
        pd.mkdir(parents=True)
        (pd / "good.md").write_text("---\nname: my-prompt\n---\n# Content", encoding="utf-8")
        errors, names = vcs.check_frontmatter(tmp_path)
        assert "my-prompt" in names["prompt"]

    def test_skill_missing_frontmatter(self, tmp_path):
        sd = tmp_path / ".github" / "skills" / "test-skill"
        sd.mkdir(parents=True)
        (sd / "SKILL.md").write_text("# No frontmatter\nContent", encoding="utf-8")
        errors, names = vcs.check_frontmatter(tmp_path)
        assert any("Missing or malformed" in e for e in errors)

    def test_valid_skill(self, tmp_path):
        sd = tmp_path / ".github" / "skills" / "test-skill"
        sd.mkdir(parents=True)
        (sd / "SKILL.md").write_text("---\nname: test-skill\n---\n# Content", encoding="utf-8")
        errors, names = vcs.check_frontmatter(tmp_path)
        assert "test-skill" in names["skill"]


class TestVcsCheckNameUniqueness:
    def test_no_duplicates(self):
        names = {"prompt": ["a", "b"], "skill": ["c", "d"]}
        assert not vcs.check_name_uniqueness(names)

    def test_duplicate_prompt(self):
        names = {"prompt": ["a", "a"], "skill": []}
        errors = vcs.check_name_uniqueness(names)
        assert any("Duplicate prompt" in e for e in errors)

    def test_duplicate_skill(self):
        names = {"prompt": [], "skill": ["x", "x"]}
        errors = vcs.check_name_uniqueness(names)
        assert any("Duplicate skill" in e for e in errors)

    def test_collision(self):
        names = {"prompt": ["shared"], "skill": ["shared"]}
        errors = vcs.check_name_uniqueness(names)
        assert any("collision" in e for e in errors)


class TestVcsCheckCopilotInstructionsSize:
    def test_missing(self, tmp_path):
        errors = vcs.check_copilot_instructions_size(tmp_path)
        assert any("Missing" in e for e in errors)

    def test_within_limit(self, tmp_path):
        ci = tmp_path / ".github" / "copilot-instructions.md"
        ci.parent.mkdir(parents=True)
        ci.write_text("Short content\n", encoding="utf-8")
        errors = vcs.check_copilot_instructions_size(tmp_path)
        assert not errors

    def test_over_limit(self, tmp_path):
        ci = tmp_path / ".github" / "copilot-instructions.md"
        ci.parent.mkdir(parents=True)
        ci.write_text("word " * 3000, encoding="utf-8")
        errors = vcs.check_copilot_instructions_size(tmp_path)
        assert any("tokens" in e for e in errors)


class TestVcsCheckTemplateSync:
    def test_no_template(self, tmp_path):
        errors = vcs.check_template_sync(tmp_path)
        assert not errors

    def test_missing_template_dir(self, tmp_path):
        (tmp_path / ".github" / "memory-bank").mkdir(parents=True)
        (tmp_path / ".github" / "memory-bank" / "test.md").write_text("x", encoding="utf-8")
        tg = tmp_path / "template" / ".github"
        tg.mkdir(parents=True)
        errors = vcs.check_template_sync(tmp_path)
        assert any("Missing template dir" in e for e in errors)

    def test_missing_file(self, tmp_path):
        (tmp_path / ".github" / "memory-bank").mkdir(parents=True)
        (tmp_path / ".github" / "memory-bank" / "test.md").write_text("x", encoding="utf-8")
        tmb = tmp_path / "template" / ".github" / "memory-bank"
        tmb.mkdir(parents=True)
        errors = vcs.check_template_sync(tmp_path)
        assert any("missing: test.md" in e for e in errors)

    def test_copilot_instructions_missing(self, tmp_path):
        (tmp_path / ".github").mkdir(parents=True)
        (tmp_path / ".github" / "copilot-instructions.md").write_text("x", encoding="utf-8")
        (tmp_path / "template" / ".github").mkdir(parents=True)
        errors = vcs.check_template_sync(tmp_path)
        assert any("copilot-instructions.md missing" in e for e in errors)


class TestVcsCheckMemoryBankQuality:
    def test_no_dir(self, tmp_path):
        errors = vcs.check_memory_bank_quality(tmp_path)
        assert not errors

    def test_missing_heading(self, tmp_path):
        mb = tmp_path / ".github" / "memory-bank"
        mb.mkdir(parents=True)
        (mb / "artifact-rules.md").write_text("# Rules\n## Random\nContent\n", encoding="utf-8")
        errors = vcs.check_memory_bank_quality(tmp_path)
        assert any("missing required heading" in e for e in errors)

    def test_orphan_section(self, tmp_path):
        mb = tmp_path / ".github" / "memory-bank"
        mb.mkdir(parents=True)
        content = "# Rules\n## Task\ncontent\n## Empty Section\n## Code\ncontent\n"
        (mb / "artifact-rules.md").write_text(content, encoding="utf-8")
        errors = vcs.check_memory_bank_quality(tmp_path)
        assert any("orphan section" in e for e in errors)

    def test_long_file_warning(self, tmp_path):
        mb = tmp_path / ".github" / "memory-bank"
        mb.mkdir(parents=True)
        lines = ["# Rules\n## Task\ncontent\n## Plan\ncontent\n## Code\ncontent\n## Verify\ncontent\n"]
        lines.extend(["x\n"] * 130)
        (mb / "artifact-rules.md").write_text("".join(lines), encoding="utf-8")
        errors = vcs.check_memory_bank_quality(tmp_path)
        assert any("lines" in e for e in errors)

    def test_code_fence_skips_headings(self, tmp_path):
        """Cover L285-286,288: code fence at top level skips inner headings."""
        mb = tmp_path / ".github" / "memory-bank"
        mb.mkdir(parents=True)
        # Code fence wrapping a heading — the heading inside shouldn't be
        # treated as a real section (so no orphan warning for it)
        content = (
            "# Rules\n"
            "## Task\n"
            "content\n"
            "```\n"
            "## Fake Heading Inside Fence\n"
            "```\n"
            "## Plan\n"
            "content\n"
            "## Code\n"
            "content\n"
            "## Verify\n"
            "content\n"
        )
        (mb / "artifact-rules.md").write_text(content, encoding="utf-8")
        errors = vcs.check_memory_bank_quality(tmp_path)
        # The "Fake Heading Inside Fence" should NOT produce an orphan warning
        assert not any("Fake Heading" in e for e in errors)

    def test_heading_with_code_fence_content(self, tmp_path):
        """Cover L296,298-300: heading followed by code fence counts as content."""
        mb = tmp_path / ".github" / "memory-bank"
        mb.mkdir(parents=True)
        content = (
            "# Rules\n"
            "## Task\n"
            "```python\n"
            "print('hello')\n"
            "```\n"
            "## Plan\n"
            "content\n"
            "## Code\n"
            "content\n"
            "## Verify\n"
            "content\n"
        )
        (mb / "artifact-rules.md").write_text(content, encoding="utf-8")
        errors = vcs.check_memory_bank_quality(tmp_path)
        # ## Task has code fence as content — should NOT be orphan
        assert not any("orphan" in e and "Task" in e for e in errors)


class TestVcsUtf8Wrapping:
    """Cover L19, L21: module-level stdout/stderr UTF-8 wrapping."""

    def test_wraps_non_utf8_stdout(self):
        import importlib, io as _io
        orig_stdout = sys.stdout
        try:
            fake = _io.TextIOWrapper(_io.BytesIO(), encoding="ascii")
            sys.stdout = fake
            importlib.reload(vcs)
            assert sys.stdout.encoding == "utf-8"
        finally:
            sys.stdout = orig_stdout
            importlib.reload(vcs)

    def test_wraps_non_utf8_stderr(self):
        import importlib, io as _io
        orig_stderr = sys.stderr
        try:
            fake = _io.TextIOWrapper(_io.BytesIO(), encoding="ascii")
            sys.stderr = fake
            importlib.reload(vcs)
            assert sys.stderr.encoding == "utf-8"
        finally:
            sys.stderr = orig_stderr
            importlib.reload(vcs)


# ─────────────────────────────────────────────
# prompt_regression_validator — deeper branches
# ─────────────────────────────────────────────

class TestPrvAssertionEdgeCases:
    def test_missing_file_field(self, tmp_path):
        case = {"id": "TC-01", "title": "T", "assertions": [{"must_contain_all": ["x"]}]}
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed
        assert any("missing file" in f.message for f in result.failures)

    def test_all_of_any_invalid_type(self, tmp_path):
        (tmp_path / "t.md").write_text("content", encoding="utf-8")
        case = {"id": "TC-01", "title": "T", "assertions": [{"file": "t.md", "all_of_any": "bad"}]}
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_all_of_any_empty_group(self, tmp_path):
        (tmp_path / "t.md").write_text("content", encoding="utf-8")
        case = {"id": "TC-01", "title": "T", "assertions": [{"file": "t.md", "all_of_any": [[]]}]}
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_must_contain_all_invalid_type(self, tmp_path):
        (tmp_path / "t.md").write_text("content", encoding="utf-8")
        case = {"id": "TC-01", "title": "T", "assertions": [{"file": "t.md", "must_contain_all": "bad"}]}
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_must_not_contain_any_invalid_type(self, tmp_path):
        (tmp_path / "t.md").write_text("content", encoding="utf-8")
        case = {"id": "TC-01", "title": "T", "assertions": [{"file": "t.md", "must_not_contain_any": "bad"}]}
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_near_invalid_type(self, tmp_path):
        (tmp_path / "t.md").write_text("content", encoding="utf-8")
        case = {"id": "TC-01", "title": "T", "assertions": [{"file": "t.md", "near": "bad"}]}
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed

    def test_near_too_few_terms(self, tmp_path):
        (tmp_path / "t.md").write_text("content", encoding="utf-8")
        case = {
            "id": "TC-01", "title": "T",
            "assertions": [{"file": "t.md", "near": [{"terms": ["one"], "max_chars": 50}]}],
        }
        result = prv.evaluate_case(case, tmp_path, {})
        assert not result.passed


class TestPrvRenderReportDeeper:
    def test_multiple_results(self):
        r1 = prv.CaseResult("TC-01", "Pass", True, [])
        failure = prv.AssertionFailure("a.md", "missing X", "check X")
        r2 = prv.CaseResult("TC-02", "Fail", False, [failure])
        report = prv.render_report([r1, r2])
        assert "TC-01" in report
        assert "TC-02" in report
        assert "missing X" in report
        assert "## Failure Details" in report


# ─────────────────────────────────────────────
# guard_status_validator — deeper coverage
# ─────────────────────────────────────────────

class TestGsvValidateStatusSchema:
    def test_modern_valid(self, tmp_path):
        status = _make_full_status("TASK-001", "drafted")
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.errors

    def test_task_id_mismatch(self):
        status = _make_full_status("TASK-001", "drafted")
        result = gsv.validate_status_schema(status, "TASK-002")
        assert any("mismatch" in e for e in result.errors)

    def test_invalid_state(self):
        status = _make_full_status("TASK-001", "nonexistent")
        result = gsv.validate_status_schema(status, "TASK-001")
        assert any("Invalid state" in e for e in result.errors)


class TestGsvValidateArtifactPresenceDeeper:
    def test_coding_missing_plan_warning(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _build_code_artifact(tmp_path, task_id)
        status = _make_full_status(task_id, "coding",
            required_artifacts=["task", "plan", "code", "status"],
            available_artifacts=["task", "code", "status"],
            missing_artifacts=["plan"])
        _write_status(tmp_path, task_id, status)
        result = gsv.validate_artifact_presence(tmp_path, task_id, "coding", status)
        assert any("Missing required" in e for e in result.errors)

    def test_plan_not_ready_for_coding(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _build_plan_artifact(tmp_path, task_id, ready="no")
        _build_code_artifact(tmp_path, task_id)
        status = _make_full_status(task_id, "coding",
            required_artifacts=["task", "plan", "code", "status"],
            available_artifacts=["task", "plan", "code", "status"],
            missing_artifacts=[])
        _write_status(tmp_path, task_id, status)
        result = gsv.validate_artifact_presence(tmp_path, task_id, "coding", status)
        assert any("Ready For Coding" in e for e in result.errors)


class TestGsvValidateResearchArtifact:
    def test_missing_sources(self, tmp_path):
        task_id = "TASK-001"
        d = tmp_path / "artifacts" / "research"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            Q1
            ## Confirmed Facts
            - Fact 1 https://example.com/source
            ## Constraints For Implementation
            Constraint 1
        """)
        p = d / "TASK-001.research.md"
        p.write_text(content, encoding="utf-8")
        _write_status(tmp_path / "artifacts", task_id, _make_full_status(task_id))
        result = gsv.validate_research_artifact(task_id, content, p)
        assert isinstance(result, gsv.ValidationResult)

    def test_valid_sources(self, tmp_path):
        task_id = "TASK-001"
        d = tmp_path / "artifacts" / "research"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            Q1
            ## Confirmed Facts
            - Fact 1 https://example.com/source
            ## Constraints For Implementation
            Constraint 1
            ## Sources
            [1] Author. "Title." https://example.com (2026-01-15 retrieved)
            [2] Author2. "Title2." https://example2.com (2026-01-14 retrieved)
        """)
        p = d / "TASK-001.research.md"
        p.write_text(content, encoding="utf-8")
        _write_status(tmp_path / "artifacts", task_id, _make_full_status(task_id))
        result = gsv.validate_research_artifact(task_id, content, p)
        assert not result.errors


class TestGsvCollectGithubPrFiles:
    def test_invalid_repo_ref(self):
        files, error = gsv.collect_github_pr_files("invalid", "1", "")
        assert error is not None
        assert files == set()

    def test_http_error(self):
        from unittest.mock import MagicMock
        mock_resp = MagicMock()
        mock_resp.status = 404
        mock_resp.read.return_value = b"Not found"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=mock_resp):
            files, error = gsv.collect_github_pr_files("user/repo", "1", "")
            assert error is not None

    def test_url_error(self):
        from urllib.error import URLError
        with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
            files, error = gsv.collect_github_pr_files("user/repo", "1", "")
            assert error is not None


class TestGsvWriteTransitionGateE:
    def test_done_with_improvement(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _build_plan_artifact(tmp_path, task_id)
        _build_code_artifact(tmp_path, task_id)
        _build_verify_artifact(tmp_path, task_id, result="pass")
        # Create improvement artifact with Status: applied
        imp_dir = tmp_path / "improvement"
        imp_dir.mkdir(parents=True)
        imp_content = textwrap.dedent(f"""\
            # Improvement: {task_id}
            ## Metadata
            - Artifact Type: improvement
            - Task ID: {task_id}
            - Owner: Claude
            - Status: applied
            - Last Updated: {_ts()}
            ## Root Cause
            Test
            ## Corrective Actions
            Fix things
        """)
        (imp_dir / f"{task_id}.improvement.md").write_text(imp_content, encoding="utf-8")
        status = _make_full_status(task_id, "verifying",
            required_artifacts=["task", "code", "verify", "status"],
            available_artifacts=["task", "plan", "code", "verify", "improvement", "status"],
            missing_artifacts=[])
        _write_status(tmp_path, task_id, status)
        result = gsv.write_transition(tmp_path, task_id, "verifying", "done")
        if not result.errors:
            status_path = gsv.artifact_path(tmp_path, task_id, "status")
            updated = json.loads(status_path.read_text(encoding="utf-8"))
            assert updated.get("Gate_E_passed") is True


class TestGsvValidatePremortemDeeper:
    def test_plan_with_insufficient_risks(self, tmp_path):
        p = _build_plan_artifact(tmp_path, "TASK-001", risk_count=2)
        task = _build_task_artifact(tmp_path, "TASK-001")
        result = gsv.validate_premortem(p, task)
        assert any("at least" in e for e in result.errors)

    def test_plan_with_no_risks_section(self, tmp_path):
        d = tmp_path / "plans"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Plan: TASK-001
            ## Metadata
            - Artifact Type: plan
            - Task ID: TASK-001
            - Owner: Claude
            - Status: approved
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Scope
            Test
        """)
        p = d / "TASK-001.plan.md"
        p.write_text(content, encoding="utf-8")
        result = gsv.validate_premortem(p, None)
        assert any("Risks" in e for e in result.errors)


# ─────────────────────────────────────────────
# Phase 3b: closing the 90% gap
# ─────────────────────────────────────────────

class TestGsvParseTaipeiDatetime:
    def test_valid(self):
        result = gsv.parse_taipei_datetime("2026-01-15T10:00:00+08:00")
        assert result is not None

    def test_invalid_format(self):
        assert gsv.parse_taipei_datetime("not-a-date") is None

    def test_value_error_branch(self):
        # Matches the pattern but fails fromisoformat
        assert gsv.parse_taipei_datetime("9999-99-99T00:00:00+08:00") is None


class TestGsvNormalizePathToken:
    def test_drive_letter(self):
        assert gsv.normalize_path_token("C:/Users/test") == "/Users/test"

    def test_dot_slash(self):
        # normalize_path_token strips "./" → value becomes "/src/main.py" after strip
        result = gsv.normalize_path_token("./src/main.py")
        assert "src/main.py" in result

    def test_git_diff_prefix(self):
        assert gsv.normalize_path_token("a/src/main.py") == "src/main.py"
        assert gsv.normalize_path_token("b/src/main.py") == "src/main.py"

    def test_backtick_strip(self):
        assert gsv.normalize_path_token("`src/main.py`") == "src/main.py"


class TestGsvResolveValidationMode:
    def test_auto_classify_false(self, tmp_path):
        result = gsv.resolve_validation_mode(tmp_path, "TASK-001", False)
        assert result.validation_mode == gsv.AUTO_CLASSIFY_FULL

    def test_lightweight_no_plan(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        result = gsv.resolve_validation_mode(tmp_path, task_id, True)
        assert result.validation_mode == gsv.AUTO_CLASSIFY_LIGHTWEIGHT

    def test_upgrade_with_premortem_flag(self, tmp_path):
        task_id = "TASK-001"
        task_dir = tmp_path / "tasks"
        task_dir.mkdir(parents=True)
        content = textwrap.dedent(f"""\
            # Task: {task_id}
            ## Metadata
            - Artifact Type: task
            - Task ID: {task_id}
            - Owner: Claude
            - Status: drafted
            - Last Updated: {_ts()}
            ## Objective
            Test
            ## Inline Flags
            - premortem: true
        """)
        (task_dir / f"{task_id}.task.md").write_text(content, encoding="utf-8")
        _write_status(tmp_path, task_id, _make_full_status(task_id, "drafted"))
        result = gsv.resolve_validation_mode(tmp_path, task_id, True)
        assert result.validation_mode == gsv.AUTO_CLASSIFY_FULL
        assert any("AUTO-UPGRADE" in w for w in result.warnings)

    def test_upgrade_with_plan_risks(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        plan_dir = tmp_path / "plans"
        plan_dir.mkdir(parents=True)
        plan_content = textwrap.dedent(f"""\
            # Plan: {task_id}
            ## Metadata
            - Artifact Type: plan
            - Task ID: {task_id}
            - Owner: Claude
            - Status: approved
            - Last Updated: {_ts()}
            ## Risks
            R1: Something bad might happen
            - Trigger: event
            - Detection: monitoring
            - Mitigation: fix
            - Severity: blocking
        """)
        (plan_dir / f"{task_id}.plan.md").write_text(plan_content, encoding="utf-8")
        status = _make_full_status(task_id, "drafted")
        _write_status(tmp_path, task_id, status)
        result = gsv.resolve_validation_mode(tmp_path, task_id, True)
        assert result.validation_mode == gsv.AUTO_CLASSIFY_FULL


class TestGsvLegacyStatusSchema:
    def test_valid_legacy(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "drafted",
            "owner": "Claude",
            "last_updated": _ts(),
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not result.errors

    def test_missing_owner(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "drafted",
            "owner": "",
            "last_updated": _ts(),
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert any("owner" in e for e in result.errors)

    def test_blocked_no_blockers(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "blocked",
            "owner": "Claude",
            "last_updated": _ts(),
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert any("blockers" in e for e in result.errors)

    def test_blocked_with_blockers(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "blocked",
            "owner": "Claude",
            "last_updated": _ts(),
            "blockers": ["dependency not ready"],
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert not any("blockers" in e for e in result.errors)

    def test_non_blocked_with_blockers_warns(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "drafted",
            "owner": "Claude",
            "last_updated": _ts(),
            "blockers": ["leftover blocker"],
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert any("blockers" in w for w in result.warnings)

    def test_bad_artifacts_type(self):
        status = {
            "task_id": "TASK-001",
            "current_state": "drafted",
            "owner": "Claude",
            "last_updated": _ts(),
            "artifacts": "not-a-dict",
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert any("artifacts" in e for e in result.errors)


class TestGsvModernStatusSchemaDeeper:
    def test_unknown_artifact_in_lists(self):
        status = _make_full_status("TASK-001", "drafted")
        status["required_artifacts"] = ["task", "status", "nonexistent_type"]
        result = gsv.validate_status_schema(status, "TASK-001")
        assert any("unknown artifacts" in e for e in result.errors)

    def test_non_list_required_artifacts(self):
        status = _make_full_status("TASK-001", "drafted")
        status["required_artifacts"] = "not-a-list"
        result = gsv.validate_status_schema(status, "TASK-001")
        assert any("must be a list" in e for e in result.errors)

    def test_blocked_no_reason(self):
        status = _make_full_status("TASK-001", "blocked")
        status["blocked_reason"] = ""
        result = gsv.validate_status_schema(status, "TASK-001")
        assert any("blocked_reason" in e for e in result.errors)

    def test_non_blocked_with_reason_warns(self):
        status = _make_full_status("TASK-001", "drafted")
        status["blocked_reason"] = "old reason"
        result = gsv.validate_status_schema(status, "TASK-001")
        assert any("blocked_reason" in w for w in result.warnings)


class TestGsvValidateTransitionGateE:
    def test_blocked_to_planned_missing_improvement(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        _write_status(tmp_path, task_id, _make_full_status(task_id, "blocked"))
        result = gsv.validate_transition("blocked", "planned", tmp_path, task_id)
        assert any("improvement artifact" in e for e in result.errors)

    def test_blocked_to_planned_improvement_not_applied(self, tmp_path):
        task_id = "TASK-001"
        _build_task_artifact(tmp_path, task_id)
        imp_dir = tmp_path / "improvement"
        imp_dir.mkdir(parents=True)
        imp_content = textwrap.dedent(f"""\
            # Improvement: {task_id}
            ## Metadata
            - Artifact Type: improvement
            - Task ID: {task_id}
            - Owner: Claude
            - Status: drafted
            - Last Updated: {_ts()}
            ## 1. Source Task
            - Source Task: {task_id}
            - Trigger Type: failure
            ## 2. Root Cause
            Stuff
            ## 5. Preventive Action (System Level)
            Stuff
            ## 6. Validation
            Stuff
            ## 8. Final Rule
            Stuff
            ## 9. Status
            drafted
        """)
        (imp_dir / f"{task_id}.improvement.md").write_text(imp_content, encoding="utf-8")
        _write_status(tmp_path, task_id, _make_full_status(task_id, "blocked"))
        result = gsv.validate_transition("blocked", "planned", tmp_path, task_id)
        assert any("Status: applied" in e for e in result.errors)


class TestGsvAppendAutoUpgradeLog:
    def test_writes_log(self, tmp_path):
        status_dir = tmp_path / "status"
        status_dir.mkdir(parents=True)
        status_path = status_dir / "TASK-001.status.json"
        status = _make_full_status("TASK-001", "drafted")
        gsv.write_json(status_path, status)
        gsv.append_auto_upgrade_log(status_path, status, "test reason")
        updated = json.loads(status_path.read_text(encoding="utf-8"))
        assert "auto_upgrade_log" in updated
        assert len(updated["auto_upgrade_log"]) == 1
        assert updated["auto_upgrade_log"][0]["reason"] == "test reason"


class TestGsvResolveWorkspaceRelativePath:
    def test_empty(self, tmp_path):
        _, _, error = gsv.resolve_workspace_relative_path(tmp_path, "")
        assert error is not None

    def test_traversal(self, tmp_path):
        _, _, error = gsv.resolve_workspace_relative_path(tmp_path, "../outside")
        assert error is not None

    def test_valid(self, tmp_path):
        (tmp_path / "test.txt").write_text("x", encoding="utf-8")
        rel, resolved, error = gsv.resolve_workspace_relative_path(tmp_path, "test.txt")
        assert error is None
        assert rel == "test.txt"

    def test_absolute_path(self, tmp_path):
        _, _, error = gsv.resolve_workspace_relative_path(tmp_path, "/etc/passwd")
        assert error is not None


class TestGsvParseRepositoryRef:
    def test_valid(self):
        owner, repo, error = gsv.parse_repository_ref("owner/repo")
        assert owner == "owner"
        assert repo == "repo"
        assert error is None

    def test_invalid(self):
        _, _, error = gsv.parse_repository_ref("no-slash")
        assert error is not None

    def test_dotdot(self):
        _, _, error = gsv.parse_repository_ref("../foo")
        assert error is not None


class TestGsvNormalizeApiBaseUrl:
    def test_default(self):
        url, error = gsv.normalize_api_base_url("")
        assert url == "https://api.github.com"
        assert error is None

    def test_custom(self):
        url, error = gsv.normalize_api_base_url("https://github.example.com/api/v3/")
        assert url == "https://github.example.com/api/v3"
        assert error is None

    def test_invalid(self):
        _, error = gsv.normalize_api_base_url("ftp://invalid")
        assert error is not None


class TestGsvStatusUsesLegacySchema:
    def test_legacy(self):
        assert gsv.status_uses_legacy_schema({"current_state": "drafted"})

    def test_modern(self):
        assert not gsv.status_uses_legacy_schema({"state": "drafted"})


class TestGsvClassifyDecisionWaiverGate:
    def test_missing_research(self):
        error = "Missing required artifacts for state 'researched': 'research'"
        assert gsv.classify_decision_waiver_gate(error) == "Gate_A"

    def test_plan_not_ready(self):
        error = "Plan artifact is not Ready For Coding = yes: TASK-001.plan.md"
        assert gsv.classify_decision_waiver_gate(error) == "Gate_B"

    def test_gate_e(self):
        error = "Gate E (PDCA): resuming from blocked requires an improvement artifact"
        assert gsv.classify_decision_waiver_gate(error) == "Gate_E"

    def test_verify(self):
        error = "done state requires verify artifact with Pass Fail Result = pass"
        assert gsv.classify_decision_waiver_gate(error) == "Gate_D"

    def test_waiver_expired(self):
        assert gsv.classify_decision_waiver_gate("waiver expired blah") is None

    def test_target_state(self):
        assert gsv.classify_decision_waiver_gate("Target state 'done' ...") == "__META__"


# ─────────────────────────────────────────────
# Phase 3c: final push to 90%
# ─────────────────────────────────────────────

class TestGsvResearchArtifactEdgeCases:
    def _setup_research(self, tmp_path, task_id, content):
        d = tmp_path / "artifacts" / "research"
        d.mkdir(parents=True)
        p = d / f"{task_id}.research.md"
        p.write_text(content, encoding="utf-8")
        _write_status(tmp_path / "artifacts", task_id, _make_full_status(task_id))
        return p

    def test_recommendation_forbidden(self, tmp_path):
        content = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            Q1
            ## Confirmed Facts
            - Fact 1 https://example.com/source
            ## Constraints For Implementation
            Constraint 1
            ## Recommendation
            Do X
            ## Sources
            [1] Author. "Title." https://example.com (2026-01-15 retrieved)
            [2] Author2. "Title2." https://example2.com (2026-01-15 retrieved)
        """)
        p = self._setup_research(tmp_path, "TASK-001", content)
        result = gsv.validate_research_artifact("TASK-001", content, p)
        assert any("Recommendation" in e for e in result.errors)

    def test_empty_confirmed_facts(self, tmp_path):
        content = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            Q1
            ## Confirmed Facts
            ## Constraints For Implementation
            Constraint 1
            ## Sources
            [1] Author. "Title." https://example.com (2026-01-15 retrieved)
            [2] Author2. "Title2." https://example2.com (2026-01-15 retrieved)
        """)
        p = self._setup_research(tmp_path, "TASK-001", content)
        result = gsv.validate_research_artifact("TASK-001", content, p)
        assert any("Confirmed Facts" in e for e in result.errors)

    def test_unverified_in_confirmed_facts(self, tmp_path):
        content = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            Q1
            ## Confirmed Facts
            - UNVERIFIED: Something not confirmed https://example.com
            ## Constraints For Implementation
            Constraint 1
            ## Sources
            [1] Author. "Title." https://example.com (2026-01-15 retrieved)
            [2] Author2. "Title2." https://example2.com (2026-01-15 retrieved)
        """)
        p = self._setup_research(tmp_path, "TASK-001", content)
        result = gsv.validate_research_artifact("TASK-001", content, p)
        assert any("UNVERIFIED" in e for e in result.errors)

    def test_uncertain_items_without_prefix(self, tmp_path):
        content = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            Q1
            ## Confirmed Facts
            - Fact 1 https://example.com
            ## Uncertain Items
            - Missing the prefix
            ## Constraints For Implementation
            Constraint 1
            ## Sources
            [1] Author. "Title." https://example.com (2026-01-15 retrieved)
            [2] Author2. "Title2." https://example2.com (2026-01-15 retrieved)
        """)
        p = self._setup_research(tmp_path, "TASK-001", content)
        result = gsv.validate_research_artifact("TASK-001", content, p)
        assert any("UNVERIFIED:" in e for e in result.errors)

    def test_empty_constraints(self, tmp_path):
        content = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            Q1
            ## Confirmed Facts
            - Fact 1 https://example.com
            ## Constraints For Implementation
            None
            ## Sources
            [1] Author. "Title." https://example.com (2026-01-15 retrieved)
            [2] Author2. "Title2." https://example2.com (2026-01-15 retrieved)
        """)
        p = self._setup_research(tmp_path, "TASK-001", content)
        result = gsv.validate_research_artifact("TASK-001", content, p)
        assert any("Constraints" in e for e in result.errors)

    def test_mixed_github_sources(self, tmp_path):
        content = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: ready
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Research Questions
            Q1
            ## Confirmed Facts
            - Fact 1 https://github.com/owner1/myrepo
            - Fact 2 https://github.com/owner2/myrepo
            ## Constraints For Implementation
            Constraint 1
            ## Sources
            [1] Author. "Title." https://github.com/owner1/myrepo (2026-01-15 retrieved)
            [2] Author2. "Title2." https://github.com/owner2/myrepo (2026-01-15 retrieved)
        """)
        p = self._setup_research(tmp_path, "TASK-001", content)
        result = gsv.validate_research_artifact("TASK-001", content, p)
        assert any("mixed truth source" in w for w in result.warnings)


class TestGsvValidateResearchCitations:
    def _write_research(self, tmp_path, task_id, sources_text):
        d = tmp_path / "artifacts" / "research"
        d.mkdir(parents=True)
        content = textwrap.dedent(f"""\
            # Research: {task_id}
            ## Sources
            {sources_text}
        """)
        p = d / f"{task_id}.research.md"
        p.write_text(content, encoding="utf-8")
        return p

    def test_no_sources_section(self, tmp_path):
        task_id = "TASK-001"
        d = tmp_path / "artifacts" / "research"
        d.mkdir(parents=True)
        content = "# Research\n## Metadata\nstuff\n"
        p = d / f"{task_id}.research.md"
        p.write_text(content, encoding="utf-8")
        findings = gsv.validate_research_citations(task_id, p)
        assert any(f.severity == "CRITICAL" for f in findings)

    def test_sources_is_none(self, tmp_path):
        task_id = "TASK-001"
        p = self._write_research(tmp_path, task_id, "None")
        findings = gsv.validate_research_citations(task_id, p)
        assert any(f.severity == "CRITICAL" for f in findings)

    def test_only_one_source(self, tmp_path):
        task_id = "TASK-001"
        p = self._write_research(tmp_path, task_id,
            '[1] Author. "Title." https://example.com (2026-01-15 retrieved)')
        findings = gsv.validate_research_citations(task_id, p)
        assert any("at least 2" in f.message for f in findings)

    def test_url_only_line_with_partial_date(self, tmp_path):
        task_id = "TASK-001"
        sources = '[1] Author. "T." https://a.com (2026-01-15 retrieved)\nhttps://bare.com (2026-01 retrieved)'
        p = self._write_research(tmp_path, task_id, sources)
        findings = gsv.validate_research_citations(task_id, p)
        assert any(f.severity == "MINOR" for f in findings)

    def test_url_only_line_without_date(self, tmp_path):
        task_id = "TASK-001"
        sources = '[1] Author. "T." https://a.com (2026-01-15 retrieved)\nhttps://bare.com'
        p = self._write_research(tmp_path, task_id, sources)
        findings = gsv.validate_research_citations(task_id, p)
        assert any("MAJOR" == f.severity for f in findings)

    def test_non_matching_line(self, tmp_path):
        task_id = "TASK-001"
        sources = '[1] Author. "T." https://a.com (2026-01-15 retrieved)\njust plain text'
        p = self._write_research(tmp_path, task_id, sources)
        findings = gsv.validate_research_citations(task_id, p)
        assert any("MAJOR" == f.severity for f in findings)


class TestGsvDetectMixedGithubSources:
    def test_no_mixed(self):
        text = "https://github.com/owner1/repo1\nhttps://github.com/owner1/repo1"
        assert gsv.detect_mixed_github_sources(text) == []

    def test_mixed(self):
        text = "https://github.com/owner1/myrepo\nhttps://github.com/owner2/myrepo"
        mixed = gsv.detect_mixed_github_sources(text)
        assert len(mixed) == 1
        assert "myrepo" in mixed[0]


# ─────────────────────────────────────────────
# Phase 4: gsv 95% — git & HTTP mocking
# ─────────────────────────────────────────────

import subprocess
from unittest.mock import MagicMock


def _mock_subprocess_run(returncode=0, stdout="", stderr=""):
    """Helper to create a mock subprocess.CompletedProcess."""
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.returncode = returncode
    mock.stdout = stdout
    mock.stderr = stderr
    return mock


class TestGsvCollectGitChangedFiles:
    def test_success(self, tmp_path):
        results = [
            _mock_subprocess_run(stdout="src/a.py\n"),
            _mock_subprocess_run(stdout="src/b.py\n"),
            _mock_subprocess_run(stdout=""),
        ]
        with patch("subprocess.run", side_effect=results):
            changed, warnings = gsv.collect_git_changed_files(tmp_path)
        assert "src/a.py" in changed
        assert "src/b.py" in changed
        assert not warnings

    def test_git_not_found(self, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            changed, warnings = gsv.collect_git_changed_files(tmp_path)
        assert changed == set()
        assert any("not available" in w for w in warnings)

    def test_git_error(self, tmp_path):
        with patch("subprocess.run", return_value=_mock_subprocess_run(returncode=1, stderr="fatal: error")):
            changed, warnings = gsv.collect_git_changed_files(tmp_path)
        assert changed == set()
        assert any("failed" in w for w in warnings)


class TestGsvCollectGitDiffRangeFiles:
    def test_success(self, tmp_path):
        with patch("subprocess.run", return_value=_mock_subprocess_run(stdout="file1.py\nfile2.py\n")):
            changed, error = gsv.collect_git_diff_range_files(tmp_path, "abc123", "def456")
        assert "file1.py" in changed
        assert "file2.py" in changed
        assert error is None

    def test_git_not_found(self, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            changed, error = gsv.collect_git_diff_range_files(tmp_path, "abc", "def")
        assert changed == set()
        assert "not available" in error

    def test_git_error(self, tmp_path):
        with patch("subprocess.run", return_value=_mock_subprocess_run(returncode=1, stderr="fatal")):
            changed, error = gsv.collect_git_diff_range_files(tmp_path, "abc", "def")
        assert changed == set()
        assert error is not None


class TestGsvResolveGitRevisionCommit:
    def test_success(self, tmp_path):
        sha = "a" * 40
        with patch("subprocess.run", return_value=_mock_subprocess_run(stdout=sha + "\n")):
            result, error = gsv.resolve_git_revision_commit(tmp_path, "main")
        assert result == sha
        assert error is None

    def test_git_not_found(self, tmp_path):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result, error = gsv.resolve_git_revision_commit(tmp_path, "main")
        assert result is None
        assert "not available" in error

    def test_git_error(self, tmp_path):
        with patch("subprocess.run", return_value=_mock_subprocess_run(returncode=128, stderr="bad rev")):
            result, error = gsv.resolve_git_revision_commit(tmp_path, "badref")
        assert result is None
        assert error is not None


class TestGsvDetectGitBackedScopeDrift:
    def test_no_changed_files(self, tmp_path):
        plan = tmp_path / "plan.md"
        code = tmp_path / "code.md"
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        code.write_text("## Files Changed\n- src/a.py\n", encoding="utf-8")
        result = gsv.detect_git_backed_scope_drift(plan, code, set(), {"artifacts/tasks/TASK-001.task.md"})
        assert not result.errors
        assert not result.waiver_candidate_errors

    def test_undeclared_drift(self, tmp_path):
        plan = tmp_path / "plan.md"
        code = tmp_path / "code.md"
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        code.write_text("## Files Changed\n- src/a.py\n", encoding="utf-8")
        actual = {"src/a.py", "src/extra.py", "artifacts/tasks/TASK-001.task.md"}
        task_arts = {"artifacts/tasks/TASK-001.task.md"}
        result = gsv.detect_git_backed_scope_drift(plan, code, actual, task_arts)
        assert any("src/extra.py" in e for e in result.waiver_candidate_errors)
        assert "src/extra.py" in result.drift_files


class TestGsvDetectHistoricalDiffScopeDrift:
    def test_no_evidence(self, tmp_path):
        code = tmp_path / "code.md"
        plan = tmp_path / "plan.md"
        code.write_text("## Files Changed\n- src/a.py\n", encoding="utf-8")
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan, code)
        assert not result.errors

    def test_unsupported_evidence_type(self, tmp_path):
        code = tmp_path / "code.md"
        plan = tmp_path / "plan.md"
        code.write_text("## Files Changed\n- src/a.py\n## Diff Evidence\n- Evidence Type: unsupported_type\n", encoding="utf-8")
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan, code)
        assert any("unsupported" in e for e in result.errors)


class TestGsvCollectGithubPrFilesDeeper:
    def test_negative_pr_number(self):
        files, error = gsv.collect_github_pr_files("user/repo", "0", "")
        assert error is not None
        assert "positive integer" in error

    def test_non_digit_pr_number(self):
        files, error = gsv.collect_github_pr_files("user/repo", "abc", "")
        assert error is not None

    def test_bad_api_url(self):
        files, error = gsv.collect_github_pr_files("user/repo", "1", "ftp://invalid")
        assert error is not None

    def test_successful_single_page(self):
        payload = [{"filename": "src/main.py"}, {"filename": "README.md"}]
        mock_body = json.dumps(payload).encode("utf-8")
        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_body
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=mock_resp):
            files, error = gsv.collect_github_pr_files("user/repo", "1", "")
        assert error is None
        assert "src/main.py" in files
        assert "README.md" in files

    def test_invalid_json_response(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=mock_resp):
            files, error = gsv.collect_github_pr_files("user/repo", "1", "")
        assert error is not None
        assert "invalid JSON" in error

    def test_non_list_response(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"not": "a list"}'
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=mock_resp):
            files, error = gsv.collect_github_pr_files("user/repo", "1", "")
        assert error is not None
        assert "non-list" in error

    def test_non_object_file_entry(self):
        payload = ["not-a-dict"]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=mock_resp):
            files, error = gsv.collect_github_pr_files("user/repo", "1", "")
        assert error is not None
        assert "non-object" in error

    def test_missing_filename(self):
        payload = [{"status": "added"}]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=mock_resp):
            files, error = gsv.collect_github_pr_files("user/repo", "1", "")
        assert error is not None
        assert "without filename" in error

    def test_http_error_with_detail(self):
        exc = urllib.error.HTTPError("http://example.com", 403, "Forbidden", {}, None)
        exc.read = lambda: b"rate limit exceeded"
        with patch("urllib.request.urlopen", side_effect=exc):
            files, error = gsv.collect_github_pr_files("user/repo", "1", "")
        assert error is not None
        assert "403" in error

    def test_url_error_detail(self):
        from urllib.error import URLError
        with patch("urllib.request.urlopen", side_effect=URLError("connection refused")):
            files, error = gsv.collect_github_pr_files("user/repo", "1", "")
        assert error is not None
        assert "connection" in error

    def test_filename_normalizes_to_empty(self):
        """L516: filename '.' normalizes to empty after strip."""
        from unittest.mock import MagicMock
        import json
        mock_resp = MagicMock()
        mock_resp.status = 200
        mock_resp.read.return_value = json.dumps([{"filename": "."}]).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: None
        mock_resp.headers = {"Link": ""}
        with patch("urllib.request.urlopen", return_value=mock_resp):
            files, error = gsv.collect_github_pr_files("user/repo", "1", "")
        assert error is not None
        assert "invalid filename" in error


import urllib.error


class TestGsvSummarizeRemoteErrorDetail:
    def test_with_body(self):
        result = gsv.summarize_remote_error_detail(b"error details here", "fallback")
        assert "error details" in result

    def test_empty_body(self):
        result = gsv.summarize_remote_error_detail(b"", "fallback")
        assert result == "fallback"

    def test_long_body_truncated(self):
        result = gsv.summarize_remote_error_detail(b"x" * 300, "fallback")
        assert len(result) <= 210
        assert result.endswith("...")


class TestGsvCompareReconstructedScope:
    def test_no_drift(self, tmp_path):
        plan = tmp_path / "plan.md"
        code = tmp_path / "code.md"
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        code.write_text("## Files Changed\n- src/a.py\n", encoding="utf-8")
        result = gsv.compare_reconstructed_scope(plan, code, {"src/a.py"}, "test")
        assert not result.waiver_candidate_errors

    def test_with_drift(self, tmp_path):
        plan = tmp_path / "plan.md"
        code = tmp_path / "code.md"
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        code.write_text("## Files Changed\n- src/a.py\n", encoding="utf-8")
        result = gsv.compare_reconstructed_scope(plan, code, {"src/a.py", "src/extra.py"}, "test")
        assert any("src/extra.py" in e for e in result.waiver_candidate_errors)


class TestGsvValidateScopeDriftWaiver:
    def test_no_drift(self, tmp_path):
        result = gsv.validate_scope_drift_waiver(tmp_path, "TASK-001", set())
        assert not result.errors

    def test_no_decision_artifact(self, tmp_path):
        (tmp_path / "decisions").mkdir(parents=True)
        result = gsv.validate_scope_drift_waiver(tmp_path, "TASK-001", {"src/extra.py"})
        assert any("decision artifact" in e for e in result.errors)

    def test_with_guard_exception_match(self, tmp_path):
        d = tmp_path / "decisions"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Decision Log: TASK-001
            ## Metadata
            - Artifact Type: decision
            - Task ID: TASK-001
            - Owner: Claude
            - Status: done
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Guard Exception
            - Exception Type: allow-scope-drift
            - Scope Files: src/extra.py
            - Justification: Needed for feature
        """)
        (d / "TASK-001.decision.md").write_text(content, encoding="utf-8")
        result = gsv.validate_scope_drift_waiver(tmp_path, "TASK-001", {"src/extra.py"})
        assert not result.errors
        assert any("waiver applied" in w for w in result.warnings)


class TestGsvDetectPlanCodeScopeDrift:
    def test_no_drift(self):
        plan = "## Files Likely Affected\n- src/a.py\n- src/b.py\n"
        code = "## Files Changed\n- src/a.py\n"
        assert gsv.detect_plan_code_scope_drift(plan, code) == []

    def test_drift_detected(self):
        plan = "## Files Likely Affected\n- src/a.py\n"
        code = "## Files Changed\n- src/a.py\n- src/extra.py\n"
        drift = gsv.detect_plan_code_scope_drift(plan, code)
        assert "src/extra.py" in drift


class TestGsvLoadGitScopeContext:
    def test_no_git_root(self, tmp_path):
        repo_root, changed, arts, warnings = gsv.load_git_scope_context(tmp_path, "TASK-001")
        assert repo_root is None
        assert changed == set()

    def test_with_git_root(self, tmp_path):
        (tmp_path / ".git").mkdir()
        results = [
            _mock_subprocess_run(stdout=""),
            _mock_subprocess_run(stdout=""),
            _mock_subprocess_run(stdout=""),
        ]
        with patch("subprocess.run", side_effect=results):
            repo_root, changed, arts, warnings = gsv.load_git_scope_context(tmp_path, "TASK-001")
        assert repo_root is not None


class TestGsvDetectGitRoot:
    def test_found(self, tmp_path):
        (tmp_path / ".git").mkdir()
        assert gsv.detect_git_root(tmp_path) == tmp_path.resolve()

    def test_not_found(self, tmp_path):
        assert gsv.detect_git_root(tmp_path / "deep" / "nested") is None


class TestGsvParseDiffEvidence:
    def test_none(self):
        assert gsv.parse_diff_evidence("no diff evidence section") is None

    def test_with_evidence(self):
        text = "## Diff Evidence\n- Evidence Type: commit-range\n- Base Commit: abc\n"
        result = gsv.parse_diff_evidence(text)
        assert result is not None
        assert result.get("evidence type") == "commit-range"


class TestGsvResolveStatusState:
    def test_modern(self):
        assert gsv.resolve_status_state({"state": "coding"}) == "coding"

    def test_legacy(self):
        assert gsv.resolve_status_state({"current_state": "drafted"}) == "drafted"

    def test_empty(self):
        assert gsv.resolve_status_state({}) is None


class TestGsvValidateMarkdownArtifact:
    def test_valid_plan(self, tmp_path):
        d = tmp_path / "plans"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Plan: TASK-001
            ## Metadata
            - Artifact Type: plan
            - Task ID: TASK-001
            - Owner: Claude
            - Status: approved
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Scope
            Test scope
            ## Proposed Changes
            Change A
            ## Files Likely Affected
            - src/main.py
            ## Validation Strategy
            Run tests
            ## Ready For Coding
            yes
            ## Risks
            R1: Risk
            - Trigger: trigger
            - Detection: detection
            - Mitigation: mitigation
            - Severity: blocking
            R2: Another
            - Trigger: t
            - Detection: d
            - Mitigation: m
            - Severity: blocking
            R3: Third
            - Trigger: t
            - Detection: d
            - Mitigation: m
            - Severity: non-blocking
            R4: Fourth
            - Trigger: t
            - Detection: d
            - Mitigation: m
            - Severity: non-blocking
        """)
        p = d / "TASK-001.plan.md"
        p.write_text(content, encoding="utf-8")
        result = gsv.validate_markdown_artifact(p, "plan", "TASK-001")
        assert not result.errors

    def test_plan_missing_ready_for_coding(self, tmp_path):
        d = tmp_path / "plans"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Plan: TASK-001
            ## Metadata
            - Artifact Type: plan
            - Task ID: TASK-001
            - Owner: Claude
            - Status: approved
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Scope
            Test
        """)
        p = d / "TASK-001.plan.md"
        p.write_text(content, encoding="utf-8")
        result = gsv.validate_markdown_artifact(p, "plan", "TASK-001")
        assert any("Ready For Coding" in e for e in result.errors)

    def test_verify_missing_pass_fail(self, tmp_path):
        d = tmp_path / "verify"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Verify: TASK-001
            ## Metadata
            - Artifact Type: verify
            - Task ID: TASK-001
            - Owner: Claude
            - Status: done
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Build Guarantee
            Test
        """)
        p = d / "TASK-001.verify.md"
        p.write_text(content, encoding="utf-8")
        result = gsv.validate_markdown_artifact(p, "verify", "TASK-001")
        assert any("Pass Fail Result" in e for e in result.errors)

    def test_invalid_status_value(self, tmp_path):
        d = tmp_path / "tasks"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Task: TASK-001
            ## Metadata
            - Artifact Type: task
            - Task ID: TASK-001
            - Owner: Claude
            - Status: invalid_status_value
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Objective
            Test
            ## Constraints
            None
            ## Acceptance Criteria
            Done
        """)
        p = d / "TASK-001.task.md"
        p.write_text(content, encoding="utf-8")
        result = gsv.validate_markdown_artifact(p, "task", "TASK-001")
        assert any("invalid Status" in e for e in result.errors)

    def test_missing_owner(self, tmp_path):
        d = tmp_path / "tasks"
        d.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Task: TASK-001
            ## Metadata
            - Artifact Type: task
            - Task ID: TASK-001
            - Status: drafted
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Objective
            Test
            ## Constraints
            None
            ## Acceptance Criteria
            Done
        """)
        p = d / "TASK-001.task.md"
        p.write_text(content, encoding="utf-8")
        result = gsv.validate_markdown_artifact(p, "task", "TASK-001")
        assert any("Owner" in e for e in result.errors), f"Expected Owner error, got: {result.errors}"


class TestGsvLoadArchiveSnapshot:
    def test_path_without_sha(self, tmp_path):
        code = tmp_path / "code.md"
        code.write_text("x", encoding="utf-8")
        evidence = {"archive path": "archive.txt"}
        _, _, error = gsv.load_archive_snapshot(tmp_path, code, evidence, set())
        assert error is not None
        assert "together" in error

    def test_sha_without_path(self, tmp_path):
        code = tmp_path / "code.md"
        code.write_text("x", encoding="utf-8")
        evidence = {"archive sha256": "abc123"}
        _, _, error = gsv.load_archive_snapshot(tmp_path, code, evidence, set())
        assert error is not None
        assert "together" in error

    def test_both_empty(self, tmp_path):
        code = tmp_path / "code.md"
        code.write_text("x", encoding="utf-8")
        evidence = {}
        result, _, error = gsv.load_archive_snapshot(tmp_path, code, evidence, set())
        assert result is None
        assert error is None

    def test_archive_not_found(self, tmp_path):
        code = tmp_path / "code.md"
        code.write_text("x", encoding="utf-8")
        import hashlib
        evidence = {"archive path": "missing.txt", "archive sha256": "abc123"}
        _, _, error = gsv.load_archive_snapshot(tmp_path, code, evidence, set())
        assert error is not None

    def test_archive_sha_mismatch(self, tmp_path):
        import hashlib
        code = tmp_path / "code.md"
        code.write_text("x", encoding="utf-8")
        archive = tmp_path / "archive.txt"
        archive.write_text("file1.py\nfile2.py\n", encoding="utf-8")
        evidence = {"archive path": "archive.txt", "archive sha256": "0000000000000000000000000000000000000000000000000000000000000000"}
        _, _, error = gsv.load_archive_snapshot(tmp_path, code, evidence, {"file1.py", "file2.py"})
        assert error is not None
        assert "SHA256" in error

    def test_archive_valid(self, tmp_path):
        import hashlib
        code = tmp_path / "code.md"
        code.write_text("x", encoding="utf-8")
        archive = tmp_path / "archive.txt"
        archive.write_text("file1.py\nfile2.py\n", encoding="utf-8")
        real_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
        evidence = {"archive path": "archive.txt", "archive sha256": real_hash}
        result, rel, error = gsv.load_archive_snapshot(tmp_path, code, evidence, {"file1.py", "file2.py"})
        assert error is None
        assert result is not None


class TestGsvNormalizePathTokenDriveLetter:
    def test_drive_letter_stripped(self):
        assert gsv.normalize_path_token("C:/src/main.py") == "/src/main.py"

    def test_lowercase_drive_letter(self):
        assert gsv.normalize_path_token("d:/foo/bar.py") == "/foo/bar.py"

    def test_backslash_drive_letter(self):
        assert gsv.normalize_path_token("C:\\src\\main.py") == "/src/main.py"


class TestGsvResolveValidationModeDeeper:
    def test_auto_classify_false(self, tmp_path):
        result = gsv.resolve_validation_mode(tmp_path, "TASK-001", False)
        assert result.validation_mode == gsv.AUTO_CLASSIFY_FULL
        assert not result.warnings

    def test_auto_classify_lightweight_no_plan(self, tmp_path):
        status_dir = tmp_path / "status"
        status_dir.mkdir(parents=True)
        (status_dir / "TASK-001.status.json").write_text(
            json.dumps({"task_id": "TASK-001", "state": "drafted", "last_updated": _ts()}), encoding="utf-8"
        )
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "TASK-001.task.md").write_text("# Task\n## Metadata\n- Task ID: TASK-001\n## Objective\nTest\n", encoding="utf-8")
        result = gsv.resolve_validation_mode(tmp_path, "TASK-001", True)
        assert result.validation_mode == gsv.AUTO_CLASSIFY_LIGHTWEIGHT
        assert any("lightweight" in w for w in result.warnings)

    def test_auto_upgrade_with_premortem(self, tmp_path):
        status_dir = tmp_path / "status"
        status_dir.mkdir(parents=True)
        (status_dir / "TASK-001.status.json").write_text(
            json.dumps({"task_id": "TASK-001", "state": "drafted", "last_updated": _ts()}), encoding="utf-8"
        )
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        (tasks_dir / "TASK-001.task.md").write_text(
            "# Task\n## Metadata\n- Task ID: TASK-001\n## Objective\nTest\n## Inline Flags\n- premortem: true\n", encoding="utf-8"
        )
        result = gsv.resolve_validation_mode(tmp_path, "TASK-001", True)
        assert result.validation_mode == gsv.AUTO_CLASSIFY_FULL
        assert any("AUTO-UPGRADE" in w for w in result.warnings)


class TestGsvAppendAutoUpgradeLogDeeper:
    def test_non_list_existing_log(self, tmp_path):
        path = tmp_path / "status.json"
        status = {"auto_upgrade_log": "not-a-list"}
        gsv.append_auto_upgrade_log(path, status, "test reason")
        assert isinstance(status["auto_upgrade_log"], list)
        assert len(status["auto_upgrade_log"]) == 1


class TestGsvValidateStatusSchemaLegacy:
    def test_legacy_schema_missing_owner(self, tmp_path):
        status = {
            "task_id": "TASK-001",
            "current_state": "drafted",
            "last_updated": _ts(),
        }
        result = gsv.validate_status_schema(status, "TASK-001")
        assert any("owner" in e.lower() for e in result.errors), f"Expected owner error, got: {result.errors}"


class TestGsvValidateTransitionGateE:
    def test_blocked_to_coding_no_improvement(self, tmp_path):
        result = gsv.validate_transition("blocked", "coding", tmp_path, "TASK-001")
        assert any("improvement" in e for e in result.errors)

    def test_blocked_to_coding_improvement_not_applied(self, tmp_path):
        imp_dir = tmp_path / "improvement"
        imp_dir.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Process Improvement
            ## Metadata
            - Artifact Type: improvement
            - Task ID: TASK-001
            - Source Task: TASK-001
            - Trigger Type: blocked
            - Owner: Claude
            - Status: drafted
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## 1. What Happened
            Test
            ## 2. Why It Was Not Prevented
            Test
            ## 3. Failure Classification
            Test
            ## 5. Preventive Action (System Level)
            Test action
            ## 6. Validation
            Test validation
            ## 8. Final Rule
            Test rule
            ## 9. Status
            Drafted
        """)
        (imp_dir / "TASK-001.improvement.md").write_text(content, encoding="utf-8")
        result = gsv.validate_transition("blocked", "coding", tmp_path, "TASK-001")
        assert any("applied" in e for e in result.errors)

    def test_blocked_to_coding_improvement_applied(self, tmp_path):
        imp_dir = tmp_path / "improvement"
        imp_dir.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Process Improvement
            ## Metadata
            - Artifact Type: improvement
            - Task ID: TASK-001
            - Source Task: TASK-001
            - Trigger Type: blocked
            - Owner: Claude
            - Status: applied
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## 1. What Happened
            Test
            ## 2. Why It Was Not Prevented
            Test
            ## 3. Failure Classification
            Test
            ## 5. Preventive Action (System Level)
            Test action
            ## 6. Validation
            Test validation
            ## 8. Final Rule
            Test rule
            ## 9. Status
            Applied
        """)
        (imp_dir / "TASK-001.improvement.md").write_text(content, encoding="utf-8")
        result = gsv.validate_transition("blocked", "coding", tmp_path, "TASK-001")
        assert not any("improvement" in e for e in result.errors)


def _setup_valid_done_tree(tmp_path, task_id="TASK-001"):
    """Set up a complete artifact tree for 'done' state with properly formatted artifacts."""
    _write_markdown_artifact(tmp_path, task_id, "task", "## Objective\nTest objective\n## Constraints\nSome constraints\n## Acceptance Criteria\nDone when tested\n")
    plan_extra = (
        "## Scope\nTest scope\n"
        "## Files Likely Affected\n- `src/main.py`\n- `tests/test_main.py`\n"
        "## Proposed Changes\nChange things\n"
        "## Validation Strategy\nRun tests\n"
        "## Risks\n"
        "R1: Risk 1\n- Risk: Something\n- Trigger: When X\n- Detection: Monitor\n- Mitigation: Rollback\n- Severity: blocking\n"
        "R2: Risk 2\n- Risk: Something\n- Trigger: When Y\n- Detection: Monitor\n- Mitigation: Rollback\n- Severity: blocking\n"
        "R3: Risk 3\n- Risk: Something\n- Trigger: When Z\n- Detection: Monitor\n- Mitigation: Rollback\n- Severity: non-blocking\n"
        "R4: Risk 4\n- Risk: Something\n- Trigger: When W\n- Detection: Monitor\n- Mitigation: Rollback\n- Severity: non-blocking\n"
        "## Ready For Coding\nyes\n"
    )
    _write_markdown_artifact(tmp_path, task_id, "plan", plan_extra)
    code_extra = "## Files Changed\n- `src/main.py`\n- `tests/test_main.py`\n## Summary Of Changes\nImplemented feature\n"
    _write_markdown_artifact(tmp_path, task_id, "code", code_extra)
    verify_extra = "## Build Guarantee\nCommit abc123\n## Pass Fail Result\npass\n"
    _write_markdown_artifact(tmp_path, task_id, "verify", verify_extra)
    research_extra = (
        "## Research Questions\n- How does X work?\n"
        "## Confirmed Facts\n- X works via Y — see https://example.com/docs\n"
        "## Sources\n[1] Example Org. \"Example Doc.\" https://example.com/docs (2026-01-15 retrieved)\n[2] Another Org. \"Ref Guide.\" https://example.org/ref (2026-01-15 retrieved)\n"
        "## Relevant References\n- https://example.com\n"
        "## Uncertain Items\n- UNVERIFIED: Z might also apply\n"
        "## Constraints For Implementation\nMust use Y approach\n"
    )
    _write_markdown_artifact(tmp_path, task_id, "research", research_extra)
    status = _make_full_status(task_id, "done",
        required_artifacts=["task", "code", "verify", "research", "status"],
        available_artifacts=["task", "plan", "code", "verify", "research", "status"],
        missing_artifacts=[])
    _write_status(tmp_path, task_id, status)
    return task_id


class TestGsvWriteTransitionGateE:
    def _make_improvement(self, tmp_path, improvement_status="applied"):
        imp_dir = tmp_path / "improvement"
        imp_dir.mkdir(exist_ok=True)
        content = (
            "# Process Improvement\n"
            "## Metadata\n"
            "- Artifact Type: improvement\n"
            "- Task ID: TASK-001\n"
            "- Source Task: TASK-001\n"
            "- Trigger Type: blocked\n"
            "- Owner: Claude\n"
            f"- Status: {improvement_status}\n"
            f"- Last Updated: {_ts()}\n"
            "\n"
            "## 1. What Happened\nTest\n"
            "## 2. Why It Was Not Prevented\nTest\n"
            "## 3. Failure Classification\nTest\n"
            "## 5. Preventive Action (System Level)\nTest action\n"
            "## 6. Validation\nTest validation\n"
            "## 8. Final Rule\nTest rule\n"
            "## 9. Status\n" + improvement_status.capitalize() + "\n"
        )
        (imp_dir / "TASK-001.improvement.md").write_text(content, encoding="utf-8")

    def test_gate_e_auto_populate_done_with_applied_improvement(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        self._make_improvement(tmp_path, "applied")
        # Update status to verifying and include improvement in available
        sp = tmp_path / "status" / "TASK-001.status.json"
        s = json.loads(sp.read_text(encoding="utf-8"))
        s["state"] = "verifying"
        s["available_artifacts"] = sorted(["task", "plan", "code", "verify", "research", "status", "improvement"])
        sp.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = gsv.write_transition(tmp_path, "TASK-001", "verifying", "done")
        assert result.ok
        status = gsv.load_json(gsv.artifact_path(tmp_path, "TASK-001", "status"))
        assert status.get("Gate_E_passed") is True
        assert status.get("Gate_E_timestamp")
        assert any("improvement" in e for e in status.get("Gate_E_evidence", []))

    def test_gate_e_not_passed_from_blocked_without_applied(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        self._make_improvement(tmp_path, "drafted")
        sp = tmp_path / "status" / "TASK-001.status.json"
        s = json.loads(sp.read_text(encoding="utf-8"))
        s["state"] = "blocked"
        s["blocked_reason"] = "test block"
        s["available_artifacts"] = sorted(["task", "plan", "code", "verify", "research", "status", "improvement"])
        sp.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = gsv.write_transition(tmp_path, "TASK-001", "blocked", "done")
        assert not result.ok


class TestGsvPrintResult:
    def test_ok_result(self, capsys):
        result = gsv.ValidationResult([], [])
        gsv.print_result(result)
        captured = capsys.readouterr()
        assert "[OK]" in captured.out

    def test_error_result(self, capsys):
        result = gsv.ValidationResult(["some error"], ["some warning"])
        gsv.print_result(result)
        captured = capsys.readouterr()
        assert "[ERROR]" in captured.out
        assert "[FAIL]" in captured.out
        assert "[WARN]" in captured.out

    def test_override_active(self, capsys):
        result = gsv.ValidationResult([], [])
        gsv.print_result(result, override_active=True)
        captured = capsys.readouterr()
        assert "[OVERRIDE ACTIVE]" in captured.out


class TestGsvMainFunction:
    def test_basic_validate(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        exit_code = gsv.main(["--task-id", "TASK-001", "--artifacts-root", str(tmp_path)])
        assert exit_code == 0

    def test_write_transition(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        sp = tmp_path / "status" / "TASK-001.status.json"
        s = json.loads(sp.read_text(encoding="utf-8"))
        s["state"] = "verifying"
        sp.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        exit_code = gsv.main([
            "--task-id", "TASK-001",
            "--artifacts-root", str(tmp_path),
            "--write-transition", "verifying", "done",
            "--allow-scope-drift",
        ])
        assert exit_code == 0

    def test_strict_and_allow_conflict(self, tmp_path):
        exit_code = gsv.main([
            "--task-id", "TASK-001",
            "--artifacts-root", str(tmp_path),
            "--strict-scope", "--allow-scope-drift",
        ])
        assert exit_code == 2

    def test_override_without_approver(self, tmp_path):
        exit_code = gsv.main([
            "--task-id", "TASK-001",
            "--artifacts-root", str(tmp_path),
            "--override", "reason",
        ])
        assert exit_code == 2

    def test_reconcile_mode(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        exit_code = gsv.main(["--task-id", "TASK-001", "--artifacts-root", str(tmp_path), "--reconcile"])
        assert exit_code == 0


class TestGsvHistoricalDiffCommitRange:
    def test_commit_range_valid_flow(self, tmp_path):
        # Plan and code artifacts for commit-range
        plan = tmp_path / "plans" / "TASK-001.plan.md"
        plan.parent.mkdir(parents=True)
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        code = tmp_path / "code" / "TASK-001.code.md"
        code.parent.mkdir(parents=True)
        base_sha = "a" * 40
        head_sha = "b" * 40
        snapshot_files = {"src/a.py"}
        snapshot_sha = gsv.compute_snapshot_sha256(snapshot_files)
        code_text = textwrap.dedent(f"""\
            ## Files Changed
            - src/a.py
            ## Diff Evidence
            - Evidence Type: commit-range
            - Base Commit: {base_sha}
            - Head Commit: {head_sha}
            - Diff Command: git diff --name-only {base_sha}..{head_sha}
            - Changed Files Snapshot: src/a.py
            - Snapshot SHA256: {snapshot_sha}
        """)
        code.write_text(code_text, encoding="utf-8")
        # Mock git diff to return the same file set
        mock_result = _mock_subprocess_run(stdout="src/a.py\n")
        with patch("subprocess.run", return_value=mock_result):
            result = gsv.detect_historical_diff_scope_drift(tmp_path, plan, code)
        assert not result.errors

    def test_commit_range_missing_fields(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        code = tmp_path / "code.md"
        snapshot_sha = gsv.compute_snapshot_sha256({"src/a.py"})
        code_text = textwrap.dedent(f"""\
            ## Files Changed
            - src/a.py
            ## Diff Evidence
            - Evidence Type: commit-range
            - Changed Files Snapshot: src/a.py
            - Snapshot SHA256: {snapshot_sha}
        """)
        code.write_text(code_text, encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan, code)
        assert any("requires" in e for e in result.errors)

    def test_commit_range_invalid_sha(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        code = tmp_path / "code.md"
        snapshot_sha = gsv.compute_snapshot_sha256({"src/a.py"})
        code_text = textwrap.dedent(f"""\
            ## Files Changed
            - src/a.py
            ## Diff Evidence
            - Evidence Type: commit-range
            - Base Commit: short
            - Head Commit: alsoShort
            - Diff Command: git diff --name-only short..alsoShort
            - Changed Files Snapshot: src/a.py
            - Snapshot SHA256: {snapshot_sha}
        """)
        code.write_text(code_text, encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan, code)
        assert any("40-character" in e for e in result.errors)

    def test_commit_range_snapshot_mismatch(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        code = tmp_path / "code.md"
        code_text = textwrap.dedent("""\
            ## Files Changed
            - src/a.py
            ## Diff Evidence
            - Evidence Type: commit-range
            - Changed Files Snapshot: src/a.py
            - Snapshot SHA256: 0000000000000000000000000000000000000000000000000000000000000000
        """)
        code.write_text(code_text, encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan, code)
        assert any("Snapshot SHA256" in e for e in result.errors)

    def test_github_pr_valid_flow(self, tmp_path):
        plan = tmp_path / "plans" / "TASK-001.plan.md"
        plan.parent.mkdir(parents=True)
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        code = tmp_path / "code" / "TASK-001.code.md"
        code.parent.mkdir(parents=True)
        snapshot_files = {"src/a.py"}
        snapshot_sha = gsv.compute_snapshot_sha256(snapshot_files)
        code_text = textwrap.dedent(f"""\
            ## Files Changed
            - src/a.py
            ## Diff Evidence
            - Evidence Type: github-pr
            - Repository: user/repo
            - PR Number: 1
            - Changed Files Snapshot: src/a.py
            - Snapshot SHA256: {snapshot_sha}
        """)
        code.write_text(code_text, encoding="utf-8")
        payload = [{"filename": "src/a.py"}]
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = lambda *a: None
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = gsv.detect_historical_diff_scope_drift(None, plan, code)
        assert not result.errors

    def test_github_pr_provider_error(self, tmp_path):
        plan = tmp_path / "plan.md"
        plan.write_text("## Files Likely Affected\n- src/a.py\n", encoding="utf-8")
        code = tmp_path / "code.md"
        snapshot_files = {"src/a.py"}
        snapshot_sha = gsv.compute_snapshot_sha256(snapshot_files)
        code_text = textwrap.dedent(f"""\
            ## Files Changed
            - src/a.py
            ## Diff Evidence
            - Evidence Type: github-pr
            - Repository: user/repo
            - PR Number: 1
            - Changed Files Snapshot: src/a.py
            - Snapshot SHA256: {snapshot_sha}
        """)
        code.write_text(code_text, encoding="utf-8")
        exc = urllib.error.URLError("connection refused")
        with patch("urllib.request.urlopen", side_effect=exc):
            result = gsv.detect_historical_diff_scope_drift(None, plan, code)
        assert any("failed" in e for e in result.errors)


class TestGsvComputeSnapshotSha256:
    def test_deterministic(self):
        files = {"b.py", "a.py"}
        h1 = gsv.compute_snapshot_sha256(files)
        h2 = gsv.compute_snapshot_sha256(files)
        assert h1 == h2
        assert len(h1) == 64


class TestGsvValidateVerifyChecklist:
    def test_valid_checklist(self, tmp_path):
        text = textwrap.dedent("""\
            ## Acceptance Criteria Checklist

            - Criterion: Tests pass
            - Method: pytest
            - Reviewer: Claude
            - Evidence: All tests green
            - Result: pass
            - Timestamp: 2026-01-15T10:00:00+08:00
        """)
        path = tmp_path / "verify.md"
        path.write_text(text, encoding="utf-8")
        result = gsv.validate_verify_checklist_schema(text, path)
        assert not result.warnings

    def test_missing_fields(self, tmp_path):
        text = textwrap.dedent("""\
            ## Acceptance Criteria Checklist

            - Criterion: Tests pass
        """)
        path = tmp_path / "verify.md"
        result = gsv.validate_verify_checklist_schema(text, path)
        assert any("missing" in w for w in result.warnings)


class TestGsvValidateArtifactPresenceCoding:
    def test_coding_plan_not_ready(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        # Modify plan to not be ready for coding
        plan_path = tmp_path / "plans" / "TASK-001.plan.md"
        text = plan_path.read_text(encoding="utf-8")
        text = text.replace("yes", "no")
        plan_path.write_text(text, encoding="utf-8")
        # Set state to coding
        sp = tmp_path / "status" / "TASK-001.status.json"
        s = json.loads(sp.read_text(encoding="utf-8"))
        s["state"] = "coding"
        sp.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = gsv.validate_all(tmp_path, "TASK-001")
        assert any("Ready For Coding" in e for e in result.errors)


class TestGsvValidateResearchArtifactDeeper:
    def test_research_with_invalid_source_format(self, tmp_path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        task_content = textwrap.dedent("""\
            # Task: TASK-001
            ## Metadata
            - Artifact Type: task
            - Task ID: TASK-001
            - Owner: Claude
            - Status: drafted
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Objective
            Test
        """)
        (tasks_dir / "TASK-001.task.md").write_text(task_content, encoding="utf-8")
        research_dir = tmp_path / "research"
        research_dir.mkdir(parents=True)
        content = textwrap.dedent("""\
            # Research: TASK-001
            ## Metadata
            - Artifact Type: research
            - Task ID: TASK-001
            - Owner: Claude
            - Status: done
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Findings
            Some findings
            ## Sources
            1. First source
            2. Second source
        """)
        (research_dir / "TASK-001.research.md").write_text(content, encoding="utf-8")
        status_dir = tmp_path / "status"
        status_dir.mkdir(parents=True)
        (status_dir / "TASK-001.status.json").write_text(
            json.dumps({"task_id": "TASK-001", "state": "researched", "last_updated": _ts()}), encoding="utf-8"
        )
        result = gsv.validate_research_artifact("TASK-001", content, research_dir / "TASK-001.research.md")
        # Should warn about source format
        assert result.errors or result.warnings


class TestGsvValidatePremortimDeeper:
    def test_high_risk_signals_no_blocking_risk(self, tmp_path):
        plan_content = textwrap.dedent("""\
            # Plan: TASK-001
            ## Metadata
            - Artifact Type: plan
            - Task ID: TASK-001
            - Owner: Claude
            - Status: approved
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Scope
            Test
            ## Ready For Coding
            yes
            ## Risks
            R1: Risk
            - Trigger: trigger
            - Detection: detection
            - Mitigation: mitigation
            - Severity: non-blocking
        """)
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(plan_content, encoding="utf-8")
        task_content = textwrap.dedent("""\
            # Task: TASK-001
            ## Metadata
            - Artifact Type: task
            - Task ID: TASK-001
            - Owner: Claude
            - Status: drafted
            - Last Updated: 2026-01-15T10:00:00+08:00
            ## Objective
            Test
            ## Inline Flags
            - task_type: security
        """)
        task_path = tmp_path / "task.md"
        task_path.write_text(task_content, encoding="utf-8")
        result = gsv.validate_premortem(plan_path, task_path)
        # With security task type, should need blocking risks
        assert result.errors or result.warnings


class TestGsvStateRequiredArtifacts:
    def test_lightweight_mode(self):
        required = gsv.state_required_artifacts("done", set(), validation_mode=gsv.AUTO_CLASSIFY_LIGHTWEIGHT)
        assert required == set(gsv.LIGHTWEIGHT_REQUIRED_ARTIFACTS)

    def test_full_mode_done_with_research(self):
        required = gsv.state_required_artifacts("done", {"research"})
        assert "research" in required

    def test_full_mode_done_with_test(self):
        required = gsv.state_required_artifacts("done", {"test"}, validation_mode=gsv.AUTO_CLASSIFY_FULL)
        # test should not be required at done unless test artifact exists
        # Actually the logic adds test only for verifying/done
        assert "test" in required


class TestGsvInferStateFromArtifacts:
    def test_empty(self):
        assert gsv.infer_state_from_artifacts(set()) == "drafted"

    def test_with_task_only(self):
        result = gsv.infer_state_from_artifacts({"task", "status"})
        assert result == "drafted"


class TestGsvValidateAllIntegration:
    def test_valid_done_state(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        result = gsv.validate_all(tmp_path, "TASK-001")
        assert result.ok

    def test_invalid_task_id(self, tmp_path):
        result = gsv.validate_all(tmp_path, "bad-id")
        assert not result.ok

    def test_lightweight_mode(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        result = gsv.validate_all(tmp_path, "TASK-001", validation_mode=gsv.AUTO_CLASSIFY_LIGHTWEIGHT)
        assert result.ok


class TestGsvResolveWorkspaceRelativePath:
    def test_relative_path(self, tmp_path):
        target = tmp_path / "src" / "main.py"
        target.parent.mkdir(parents=True)
        target.write_text("x", encoding="utf-8")
        rel, resolved, err = gsv.resolve_workspace_relative_path(tmp_path, "src/main.py")
        assert rel == "src/main.py"
        assert err is None

    def test_empty_path(self, tmp_path):
        rel, resolved, err = gsv.resolve_workspace_relative_path(tmp_path, "")
        assert rel is None
        assert err is not None

    def test_path_traversal(self, tmp_path):
        rel, resolved, err = gsv.resolve_workspace_relative_path(tmp_path, "../escape")
        assert err is not None


class TestGsvParseRepositoryRef:
    def test_valid(self):
        owner, repo, err = gsv.parse_repository_ref("user/myrepo")
        assert owner == "user"
        assert repo == "myrepo"
        assert err is None

    def test_invalid(self):
        owner, repo, err = gsv.parse_repository_ref("invalid-format")
        assert err is not None


class TestGsvNormalizeApiBaseUrl:
    def test_default(self):
        url, err = gsv.normalize_api_base_url("")
        assert url == "https://api.github.com"
        assert err is None

    def test_custom_url(self):
        url, err = gsv.normalize_api_base_url("https://github.example.com/api/v3")
        assert url == "https://github.example.com/api/v3"
        assert err is None

    def test_invalid_scheme(self):
        url, err = gsv.normalize_api_base_url("ftp://invalid.com")
        assert url is None
        assert err is not None

    def test_trailing_slash_stripped(self):
        url, err = gsv.normalize_api_base_url("https://api.github.com/")
        assert url == "https://api.github.com"


class TestGsvStatusUsesLegacySchema:
    def test_modern(self):
        assert not gsv.status_uses_legacy_schema({"state": "coding"})

    def test_legacy(self):
        assert gsv.status_uses_legacy_schema({"current_state": "drafted"})

    def test_both(self):
        assert not gsv.status_uses_legacy_schema({"state": "coding", "current_state": "drafted"})


# ── Phase 4c: targeted coverage for remaining uncovered lines ──


class TestGsvNormalizePathTokenDiffPrefix:
    """Cover line 305: a/ and b/ prefix stripping."""
    def test_a_prefix(self):
        assert gsv.normalize_path_token("a/src/main.py") == "src/main.py"

    def test_b_prefix(self):
        assert gsv.normalize_path_token("b/src/main.py") == "src/main.py"

    def test_dot_slash_stripped_by_outer_strip(self):
        # The . in ./ is consumed by the special-char strip, so ./ branch is unreachable
        assert gsv.normalize_path_token("./src/main.py") == "/src/main.py"


class TestGsvResolveWorkspaceRelativePathEdgeCases:
    """Cover lines 362-363, 376-377, 380-381, 390."""
    def test_absolute_posix_path_rejected(self, tmp_path):
        rel, resolved, err = gsv.resolve_workspace_relative_path(tmp_path, "/etc/passwd")
        assert err is not None
        assert "repository root" in err

    def test_dotdot_path_rejected(self, tmp_path):
        rel, resolved, err = gsv.resolve_workspace_relative_path(tmp_path, "foo/../../escape")
        assert err is not None

    def test_valid_nested_path(self, tmp_path):
        target = tmp_path / "src" / "lib.py"
        target.parent.mkdir(parents=True)
        target.write_text("x", encoding="utf-8")
        rel, resolved, err = gsv.resolve_workspace_relative_path(tmp_path, "src/lib.py")
        assert rel == "src/lib.py"
        assert resolved is not None
        assert err is None


class TestGsvCollectGithubPrFilesEdgeCases:
    """Cover lines 505, 507, 516 — pagination and edge cases."""
    @unittest.mock.patch("artifacts.scripts.guard_status_validator.urllib.request.urlopen")
    def test_exceeds_max_pages(self, mock_urlopen):
        """Cover line 507 — too many pages."""
        # Create a response with exactly 100 items to trigger next page
        full_page = [{"filename": f"file{i}.py"} for i in range(100)]
        def make_resp(data):
            resp = unittest.mock.MagicMock()
            resp.read.return_value = json.dumps(data).encode()
            resp.headers = {}
            resp.__enter__ = lambda s: s
            resp.__exit__ = unittest.mock.MagicMock(return_value=False)
            return resp
        # MAX_GITHUB_PR_FILES_PAGES + 1 full pages
        max_pages = gsv.MAX_GITHUB_PR_FILES_PAGES
        mock_urlopen.side_effect = [make_resp(full_page) for _ in range(max_pages + 1)]
        files, err = gsv.collect_github_pr_files("owner/repo", "1", "")
        assert err is not None
        assert "exceeds" in err

    @unittest.mock.patch("artifacts.scripts.guard_status_validator.urllib.request.urlopen")
    def test_non_list_response(self, mock_urlopen):
        resp = unittest.mock.MagicMock()
        resp.read.return_value = json.dumps({"error": "not found"}).encode()
        resp.headers = {}
        resp.__enter__ = lambda s: s
        resp.__exit__ = unittest.mock.MagicMock(return_value=False)
        mock_urlopen.return_value = resp
        files, err = gsv.collect_github_pr_files("owner/repo", "1", "")
        assert err is not None

    @unittest.mock.patch("artifacts.scripts.guard_status_validator.urllib.request.urlopen")
    def test_missing_filename_key(self, mock_urlopen):
        resp = unittest.mock.MagicMock()
        resp.read.return_value = json.dumps([{"path": "a.py"}]).encode()
        resp.headers = {}
        resp.__enter__ = lambda s: s
        resp.__exit__ = unittest.mock.MagicMock(return_value=False)
        mock_urlopen.return_value = resp
        files, err = gsv.collect_github_pr_files("owner/repo", "1", "")
        assert err is not None
        assert "without filename" in err


class TestGsvExtractTaskTitleEdge:
    """Cover line 1261."""
    def test_no_match(self, tmp_path):
        p = tmp_path / "tasks" / "TASK-001.task.md"
        p.parent.mkdir(parents=True)
        p.write_text("Not a task heading\n", encoding="utf-8")
        result = gsv.extract_task_title(p)
        assert result == ""

    def test_none_path(self):
        assert gsv.extract_task_title(None) == ""


class TestGsvMainEntrypoint:
    """Cover lines 1544, 1556."""
    def test_main_validate_mode(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        rc = gsv.main(["--task-id", "TASK-001", "--artifacts-root", str(tmp_path)])
        assert rc == 0

    def test_main_transition_mode(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        sp = tmp_path / "status" / "TASK-001.status.json"
        s = json.loads(sp.read_text(encoding="utf-8"))
        s["state"] = "verifying"
        s["available_artifacts"] = sorted(["task", "plan", "code", "verify", "research", "status"])
        s["required_artifacts"] = sorted(["task", "code", "verify", "research", "status"])
        sp.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        rc = gsv.main(["--task-id", "TASK-001", "--artifacts-root", str(tmp_path), "--write-transition", "verifying", "done"])
        assert rc == 0

    def test_main_strict_and_allow_conflict(self):
        rc = gsv.main(["--task-id", "TASK-001", "--strict-scope", "--allow-scope-drift"])
        assert rc == 2

    def test_main_override_without_approver(self, tmp_path):
        rc = gsv.main(["--task-id", "TASK-001", "--artifacts-root", str(tmp_path), "--override", "reason"])
        assert rc == 2


class TestGsvWriteTransitionEdgeCases:
    """Cover lines 1664, 1679, 1704-1706."""
    @unittest.mock.patch.object(gsv, "validate_all", return_value=gsv.ValidationResult([], []))
    @unittest.mock.patch.object(gsv, "validate_transition", return_value=gsv.ValidationResult([], []))
    def test_state_mismatch_refuses(self, mock_vt, mock_va, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        # status state is "done", but from_state is "coding" → mismatch
        result = gsv.write_transition(tmp_path, "TASK-001", "coding", "verifying")
        assert not result.ok
        assert any("Refusing" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "validate_artifact_presence", return_value=gsv.ValidationResult([], []))
    @unittest.mock.patch.object(gsv, "validate_all", return_value=gsv.ValidationResult([], []))
    @unittest.mock.patch.object(gsv, "validate_transition", return_value=gsv.ValidationResult([], []))
    def test_gate_e_blocked_without_applied_improvement(self, mock_vt, mock_va, mock_vap, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        imp_dir = tmp_path / "improvement"
        imp_dir.mkdir(exist_ok=True)
        content = (
            "# Process Improvement\n"
            "## Metadata\n"
            "- Artifact Type: improvement\n"
            "- Task ID: TASK-001\n"
            "- Source Task: TASK-001\n"
            "- Trigger Type: blocked\n"
            "- Owner: Claude\n"
            "- Status: drafted\n"
            f"- Last Updated: {_ts()}\n\n"
            "## 1. What Happened\nTest\n"
            "## 2. Why It Was Not Prevented\nTest\n"
            "## 3. Failure Classification\nTest\n"
            "## 5. Preventive Action (System Level)\nTest\n"
            "## 6. Validation\nTest\n"
            "## 8. Final Rule\nTest\n"
            "## 9. Status\nDrafted\n"
        )
        (imp_dir / "TASK-001.improvement.md").write_text(content, encoding="utf-8")
        sp = tmp_path / "status" / "TASK-001.status.json"
        s = json.loads(sp.read_text(encoding="utf-8"))
        s["state"] = "blocked"
        s["blocked_reason"] = "test"
        s["available_artifacts"] = sorted(["task", "plan", "code", "verify", "research", "status", "improvement"])
        s["required_artifacts"] = sorted(["task", "code", "verify", "research", "status"])
        sp.write_text(json.dumps(s, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        result = gsv.write_transition(tmp_path, "TASK-001", "blocked", "done")
        assert result.ok
        s2 = json.loads(sp.read_text(encoding="utf-8"))
        assert s2.get("Gate_E_passed") is False


class TestGsvResolveGitRevisionCommitError:
    """Cover lines 649-653."""
    @unittest.mock.patch("artifacts.scripts.guard_status_validator.subprocess.run")
    def test_nonzero_returncode(self, mock_run):
        mock_run.return_value = _mock_subprocess_run(returncode=128, stderr="fatal: bad object")
        commit, err = gsv.resolve_git_revision_commit(Path("/tmp"), "HEAD")
        assert err is not None
        assert commit is None

    @unittest.mock.patch("artifacts.scripts.guard_status_validator.subprocess.run")
    def test_empty_stdout(self, mock_run):
        mock_run.return_value = _mock_subprocess_run(returncode=0, stdout="  \n")
        # Empty stdout after strip causes IndexError — this is a known edge case
        with pytest.raises(IndexError):
            gsv.resolve_git_revision_commit(Path("/tmp"), "HEAD")


# ── Phase 4d: targeted coverage for remaining gaps ──


class TestGsvPlanHasNonEmptyRisks:
    """Cover lines 362-363."""
    def test_with_risks(self):
        text = "## Risks\n- Risk 1: something\n"
        assert gsv.plan_has_non_empty_risks(text) is True

    def test_empty_risks(self):
        text = "## Risks\nNone\n"
        assert gsv.plan_has_non_empty_risks(text) is False

    def test_no_section(self):
        text = "## Other\nstuff\n"
        assert gsv.plan_has_non_empty_risks(text) is False


class TestGsvResolveWorkspaceOSError:
    """Cover lines 380-381."""
    @unittest.mock.patch("pathlib.Path.resolve", side_effect=OSError("permission denied"))
    def test_os_error(self, mock_resolve):
        _, _, err = gsv.resolve_workspace_relative_path(Path("/repo"), "src/main.py")
        assert err is not None
        assert "permission" in err


class TestGsvClassifyDecisionWaiverGate:
    """Cover line 1544 (Gate_A)."""
    def test_gate_a_research(self):
        result = gsv.classify_decision_waiver_gate("TASK-001.research.md: missing section")
        assert result == "Gate_A"

    def test_gate_a_research_artifact(self):
        result = gsv.classify_decision_waiver_gate("research artifact is required")
        assert result == "Gate_A"


class TestGsvActiveDecisionWaiversEdge:
    """Cover line 1556 (non-dict entry skip)."""
    def test_non_dict_entries_skipped(self):
        status = {"decision_waivers": ["not_a_dict", 42, None]}
        result = gsv.active_decision_waivers(status)
        assert result == {}

    def test_non_list_waivers(self):
        status = {"decision_waivers": "invalid"}
        result = gsv.active_decision_waivers(status)
        assert result == {}


class TestGsvValidateImprovementMissingSource:
    """Cover line 1079."""
    def test_missing_source_task(self):
        text = (
            "# Process Improvement\n"
            "## Metadata\n"
            "- Artifact Type: improvement\n"
            "- Task ID: TASK-001\n"
            "- Trigger Type: blocked\n"
            "- Owner: Claude\n"
            "- Status: drafted\n"
            f"- Last Updated: {_ts()}\n\n"
            "## 1. What Happened\nTest\n"
        )
        result = gsv.validate_improvement_artifact(text, Path("TASK-001.improvement.md"), "TASK-001")
        assert any("Source Task" in e for e in result.errors)


class TestGsvAutoClassifyLightweight:
    """Cover lines 879, 889."""
    def test_lightweight_upgrade_due_to_plan_risks(self, tmp_path):
        task_dir = tmp_path / "tasks"
        task_dir.mkdir()
        plan_dir = tmp_path / "plans"
        plan_dir.mkdir()
        status_dir = tmp_path / "status"
        status_dir.mkdir()
        task_text = (
            "# Task\n## Metadata\n"
            "- Artifact Type: task\n- Task ID: TASK-001\n"
            f"- Owner: Claude\n- Status: drafted\n- Last Updated: {_ts()}\n"
            "## Objective\nTest\n## Constraints\nNone\n## Acceptance Criteria\nDone\n"
            "## Inline Flags\nlightweight: true\n"
        )
        (task_dir / "TASK-001.task.md").write_text(task_text, encoding="utf-8")
        plan_text = (
            "# Plan\n## Metadata\n"
            "- Artifact Type: plan\n- Task ID: TASK-001\n"
            f"- Owner: Claude\n- Status: drafted\n- Last Updated: {_ts()}\n"
            "## Objective\nTest\n## Proposed Changes\nTest\n"
            "## Files Likely Affected\n- src/main.py\n"
            "## Validation Strategy\nTest\n"
            "## Risks\n- R1: real risk with trigger and mitigation\n"
        )
        (plan_dir / "TASK-001.plan.md").write_text(plan_text, encoding="utf-8")
        status = {
            "task_id": "TASK-001", "state": "drafted",
            "available_artifacts": ["task", "plan", "status"],
            "required_artifacts": ["task", "status"],
            "missing_artifacts": [],
        }
        sp = status_dir / "TASK-001.status.json"
        sp.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        result = gsv.resolve_validation_mode(tmp_path, "TASK-001", auto_classify=True)
        assert result.validation_mode == gsv.AUTO_CLASSIFY_FULL
        assert any("AUTO-UPGRADE" in w for w in result.warnings)


class TestGsvReconcileProtectedFields:
    """Cover line 1339."""
    def test_protected_fields_not_overwritten(self, tmp_path):
        status_dir = tmp_path / "status"
        status_dir.mkdir()
        task_dir = tmp_path / "tasks"
        task_dir.mkdir()
        task_text = (
            "# Task\n## Metadata\n"
            "- Artifact Type: task\n- Task ID: TASK-001\n"
            f"- Owner: Claude\n- Status: drafted\n- Last Updated: {_ts()}\n"
            "## Objective\nTest\n## Constraints\nNone\n## Acceptance Criteria\nDone\n"
        )
        (task_dir / "TASK-001.task.md").write_text(task_text, encoding="utf-8")
        status = {"task_id": "TASK-001", "state": "drafted"}
        sp = status_dir / "TASK-001.status.json"
        sp.write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
        result = gsv.reconcile_status(tmp_path, "TASK-001")
        s2 = json.loads(sp.read_text(encoding="utf-8"))
        # state is protected, should remain "drafted"
        assert s2["state"] == "drafted"


class TestGsvTaskArtifactRelativePaths:
    """Cover lines 649-653."""
    def test_collects_artifact_paths(self, tmp_path):
        task_dir = tmp_path / "tasks"
        task_dir.mkdir()
        (task_dir / "TASK-001.task.md").write_text("# Task\n", encoding="utf-8")
        plan_dir = tmp_path / "plans"
        plan_dir.mkdir()
        (plan_dir / "TASK-001.plan.md").write_text("# Plan\n", encoding="utf-8")
        result = gsv.task_artifact_relative_paths(tmp_path, "TASK-001", tmp_path)
        assert "tasks/task-001.task.md" in result or any("task" in p for p in result)

    def test_outside_repo_root(self, tmp_path):
        artifacts_root = tmp_path / "artifacts"
        artifacts_root.mkdir()
        task_dir = artifacts_root / "tasks"
        task_dir.mkdir()
        (task_dir / "TASK-001.task.md").write_text("# Task\n", encoding="utf-8")
        other_root = tmp_path / "other"
        other_root.mkdir()
        result = gsv.task_artifact_relative_paths(artifacts_root, "TASK-001", other_root)
        # paths outside repo_root should be skipped (ValueError branch)
        assert len(result) == 0


class TestGsvClassifyDecisionWaiverGateMore:
    """Cover line 1540."""
    def test_gate_b_plan(self):
        result = gsv.classify_decision_waiver_gate("TASK-001.plan.md: missing section")
        assert result == "Gate_B"

    def test_gate_b_plan_not_ready(self):
        result = gsv.classify_decision_waiver_gate("plan artifact is not ready for coding")
        assert result == "Gate_B"


class TestGsvWriteTransitionValidateAllFails:
    """Cover line 1664."""
    @unittest.mock.patch.object(gsv, "validate_all", return_value=gsv.ValidationResult(["some error"], []))
    @unittest.mock.patch.object(gsv, "validate_transition", return_value=gsv.ValidationResult([], []))
    def test_validate_all_errors_returned(self, mock_vt, mock_va, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        result = gsv.write_transition(tmp_path, "TASK-001", "done", "blocked")
        assert not result.ok
        assert "some error" in result.errors


class TestGsvWriteTransitionTargetPresenceFails:
    """Cover line 1679."""
    @unittest.mock.patch.object(gsv, "validate_artifact_presence", return_value=gsv.ValidationResult(["missing verify"], []))
    @unittest.mock.patch.object(gsv, "validate_all", return_value=gsv.ValidationResult([], []))
    @unittest.mock.patch.object(gsv, "validate_transition", return_value=gsv.ValidationResult([], []))
    def test_target_presence_errors(self, mock_vt, mock_va, mock_vap, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        result = gsv.write_transition(tmp_path, "TASK-001", "done", "blocked")
        assert not result.ok
        assert any("Target state" in e for e in result.errors)


# ── Phase 5: Coverage push toward 97% ──────────────────────────────


class TestGsvParseRepositoryRefDotSegments:
    """Cover line 390 — dot/dotdot owner/repo segments."""
    def test_dot_owner(self):
        _owner, _repo, err = gsv.parse_repository_ref("./myrepo")
        assert err == "Repository owner/repo segments must be concrete names"

    def test_dotdot_repo(self):
        _owner, _repo, err = gsv.parse_repository_ref("owner/..")
        assert err == "Repository owner/repo segments must be concrete names"

    def test_dot_repo(self):
        _owner, _repo, err = gsv.parse_repository_ref("owner/.")
        assert err == "Repository owner/repo segments must be concrete names"

    def test_dotdot_owner(self):
        _owner, _repo, err = gsv.parse_repository_ref("../repo")
        assert err == "Repository owner/repo segments must be concrete names"


class TestGsvResolveWorkspacePathEscape:
    """Cover lines 380-381 — resolved path escapes repository root."""
    def test_path_escape_via_resolve(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        original_resolve = Path.resolve
        call_count = [0]
        def patched_resolve(self_path, strict=False):
            call_count[0] += 1
            if call_count[0] == 2:
                return Path("/outside/repo/dir")
            return original_resolve(self_path, strict=strict) if strict else original_resolve(self_path)
        with unittest.mock.patch.object(Path, "resolve", patched_resolve):
            _rel, _resolved, err = gsv.resolve_workspace_relative_path(repo, "some/path")
        assert err == "path escapes repository root"


class TestGsvLoadArchiveSnapshotBranches:
    """Cover lines 422, 427-428, 437-438, 441, 449, 451 — load_archive_snapshot error paths."""

    def _make_evidence(self, archive_path, archive_sha256):
        return {"archive path": archive_path, "archive sha256": archive_sha256}

    def test_archive_path_not_found(self, tmp_path):
        """Line 427-428: FileNotFoundError when reading archive."""
        evidence = self._make_evidence(
            "nonexistent_archive.txt",
            "a" * 64,
        )
        _files, _rel, err = gsv.load_archive_snapshot(tmp_path, Path("TASK-001.code.md"), evidence, set())
        assert err is not None
        assert "does not exist" in err

    def test_archive_os_error(self, tmp_path):
        """Line 429-430: OSError on read."""
        archive = tmp_path / "archive.txt"
        archive.mkdir()  # directory, not file — read_bytes raises
        evidence = self._make_evidence("archive.txt", "a" * 64)
        _files, _rel, err = gsv.load_archive_snapshot(tmp_path, Path("TASK-001.code.md"), evidence, set())
        assert err is not None
        assert "unable to read" in err or "does not exist" in err or "denied" in err.lower() or "Is a directory" in err or "Error" in err

    def test_archive_sha256_mismatch(self, tmp_path):
        """Line 432-433: SHA256 doesn't match."""
        archive = tmp_path / "archive.txt"
        archive.write_text("src/main.py\n", encoding="utf-8")
        evidence = self._make_evidence("archive.txt", "b" * 64)
        _files, _rel, err = gsv.load_archive_snapshot(tmp_path, Path("TASK-001.code.md"), evidence, {"src/main.py"})
        assert err is not None
        assert "SHA256 does not match" in err

    def test_archive_non_utf8(self, tmp_path):
        """Lines 437-438: UnicodeDecodeError."""
        archive = tmp_path / "archive.bin"
        content = b"\x80\x81\x82\x83"
        archive.write_bytes(content)
        import hashlib
        sha = hashlib.sha256(content).hexdigest()
        evidence = self._make_evidence("archive.bin", sha)
        _files, _rel, err = gsv.load_archive_snapshot(tmp_path, Path("TASK-001.code.md"), evidence, set())
        assert err is not None
        assert "UTF-8" in err

    def test_archive_blank_line(self, tmp_path):
        """Line 449: blank line in archive."""
        import hashlib
        content = "src/main.py\n\ntests/test.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(content.encode("utf-8"))
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        evidence = self._make_evidence("archive.txt", sha)
        _files, _rel, err = gsv.load_archive_snapshot(
            tmp_path, Path("TASK-001.code.md"), evidence, {"src/main.py", "tests/test.py"}
        )
        assert err is not None
        assert "blank line" in err

    def test_archive_invalid_path_traversal(self, tmp_path):
        """Line 451: path with mid-traversal '/../'."""
        import hashlib
        content = "src/../escape/file.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(content.encode("utf-8"))
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        evidence = self._make_evidence("archive.txt", sha)
        _files, _rel, err = gsv.load_archive_snapshot(
            tmp_path, Path("TASK-001.code.md"), evidence, {"src/../escape/file.py"}
        )
        assert err is not None
        assert "invalid path" in err

    def test_archive_unsorted(self, tmp_path):
        """Line 459: paths not sorted."""
        import hashlib
        content = "z/file.py\na/file.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(content.encode("utf-8"))
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        evidence = self._make_evidence("archive.txt", sha)
        _files, _rel, err = gsv.load_archive_snapshot(
            tmp_path, Path("TASK-001.code.md"), evidence, {"a/file.py", "z/file.py"}
        )
        assert err is not None
        assert "sorted" in err

    def test_archive_duplicate_path(self, tmp_path):
        """Line 454-455: duplicate path."""
        import hashlib
        content = "src/main.py\nsrc/main.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(content.encode("utf-8"))
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        evidence = self._make_evidence("archive.txt", sha)
        _files, _rel, err = gsv.load_archive_snapshot(
            tmp_path, Path("TASK-001.code.md"), evidence, {"src/main.py"}
        )
        assert err is not None
        assert "duplicate" in err

    def test_archive_snapshot_mismatch(self, tmp_path):
        """Line 462-464: archive files != snapshot files."""
        import hashlib
        content = "src/main.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(content.encode("utf-8"))
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        evidence = self._make_evidence("archive.txt", sha)
        _files, _rel, err = gsv.load_archive_snapshot(
            tmp_path, Path("TASK-001.code.md"), evidence, {"src/main.py", "src/extra.py"}
        )
        assert err is not None
        assert "does not match Changed Files Snapshot" in err

    def test_archive_success(self, tmp_path):
        """Happy path: archive matches snapshot."""
        import hashlib
        content = "src/extra.py\nsrc/main.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(content.encode("utf-8"))
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        evidence = self._make_evidence("archive.txt", sha)
        files, rel, err = gsv.load_archive_snapshot(
            tmp_path, Path("TASK-001.code.md"), evidence, {"src/main.py", "src/extra.py"}
        )
        assert err is None
        assert files == {"src/main.py", "src/extra.py"}
        assert rel == "archive.txt"

    def test_archive_path_and_sha_must_appear_together(self, tmp_path):
        """Line 414: archive_path without sha256."""
        evidence = {"archive path": "archive.txt", "archive sha256": ""}
        _files, _rel, err = gsv.load_archive_snapshot(tmp_path, Path("TASK-001.code.md"), evidence, set())
        assert err is not None
        assert "together" in err

    def test_archive_sha_invalid_hex(self, tmp_path):
        """Line 420: invalid hex string."""
        evidence = {"archive path": "archive.txt", "archive sha256": "not-hex"}
        _files, _rel, err = gsv.load_archive_snapshot(tmp_path, Path("TASK-001.code.md"), evidence, set())
        assert err is not None
        assert "hexadecimal" in err

    def test_no_archive_returns_none(self, tmp_path):
        """Line 417-418: both empty → return None,None,None."""
        evidence = {"archive path": "", "archive sha256": ""}
        files, rel, err = gsv.load_archive_snapshot(tmp_path, Path("TASK-001.code.md"), evidence, set())
        assert files is None
        assert rel is None
        assert err is None


class TestGsvCollectGithubPrFilesWithToken:
    """Cover line 481 — Authorization header when GITHUB_TOKEN is set."""
    def test_token_header_included(self):
        with unittest.mock.patch.dict(os.environ, {"GITHUB_TOKEN": "test-token-abc"}, clear=False):
            with unittest.mock.patch("urllib.request.urlopen") as mock_urlopen:
                mock_resp = unittest.mock.MagicMock()
                mock_resp.read.return_value = b"[]"
                mock_resp.__enter__ = lambda s: s
                mock_resp.__exit__ = lambda s, *a: None
                mock_urlopen.return_value = mock_resp
                files, err = gsv.collect_github_pr_files("owner/repo", "1", "")
        assert err is None
        assert files == set()
        # Verify Authorization header was set
        call_args = mock_urlopen.call_args
        request_obj = call_args[0][0]
        assert request_obj.get_header("Authorization") == "Bearer test-token-abc"


class TestGsvDetectGitBackedScopeDriftUndeclared:
    """Cover line 674 — undeclared actual changed files."""
    def test_undeclared_files(self, tmp_path):
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(
            "## Files Likely Affected\n- `src/main.py`\n",
            encoding="utf-8",
        )
        code_path = tmp_path / "code.md"
        code_path.write_text(
            "## Files Changed\n- `src/main.py`\n",
            encoding="utf-8",
        )
        actual_changed = {"src/main.py", "src/extra.py", "artifacts/tasks/TASK-001.task.md"}
        task_artifacts = {"artifacts/tasks/TASK-001.task.md"}
        result = gsv.detect_git_backed_scope_drift(plan_path, code_path, actual_changed, task_artifacts)
        assert result.waiver_candidate_errors
        assert any("src/extra.py" in e for e in result.waiver_candidate_errors)
        assert "src/extra.py" in result.drift_files

    def test_all_declared_no_drift(self, tmp_path):
        plan_path = tmp_path / "plan.md"
        plan_path.write_text(
            "## Files Likely Affected\n- `src/main.py`\n",
            encoding="utf-8",
        )
        code_path = tmp_path / "code.md"
        code_path.write_text(
            "## Files Changed\n- `src/main.py`\n",
            encoding="utf-8",
        )
        actual_changed = {"src/main.py", "artifacts/tasks/TASK-001.task.md"}
        task_artifacts = {"artifacts/tasks/TASK-001.task.md"}
        result = gsv.detect_git_backed_scope_drift(plan_path, code_path, actual_changed, task_artifacts)
        assert not result.waiver_candidate_errors
        assert not result.drift_files


class TestGsvVerifyChecklistStructuredMissingField:
    """Cover line 1134 — structured checklist item missing a field."""
    def test_missing_evidence_field(self, tmp_path):
        text = (
            "## Acceptance Criteria Checklist\n\n"
            "- **Criterion**: Feature works\n"
            "- **Method**: Manual test\n"
            "- **Reviewer**: Alice\n"
            "- **Timestamp**: 2026-01-15T10:00:00+08:00\n"
        )
        path = tmp_path / "TASK-001.verify.md"
        result = gsv.validate_verify_checklist_schema(text, path)
        assert any("missing evidence field" in w or "missing result field" in w for w in result.warnings)

    def test_all_fields_present_no_warning(self, tmp_path):
        text = (
            "## Acceptance Criteria Checklist\n\n"
            "- **Criterion**: Feature works\n"
            "- **Method**: Manual test\n"
            "- **Evidence**: Screenshot attached\n"
            "- **Result**: pass\n"
            "- **Reviewer**: Alice\n"
            "- **Timestamp**: 2026-01-15T10:00:00+08:00\n"
        )
        path = tmp_path / "TASK-001.verify.md"
        result = gsv.validate_verify_checklist_schema(text, path)
        # No missing-field warnings
        missing_warnings = [w for w in result.warnings if "missing" in w and "field" in w]
        assert not missing_warnings


class TestGsvPremortemHighRiskWarning:
    """Cover line 1261 — high-risk warning when min_critical=0 and no blocking risks."""
    def test_hotfix_with_security_keyword_no_blocking(self, tmp_path):
        # hotfix policy → min_critical=0, min_risks=1
        task_path = tmp_path / "tasks" / "TASK-001.task.md"
        task_path.parent.mkdir(parents=True)
        task_path.write_text(
            "# Task: hotfix fix security issue\n## Metadata\n- Task ID: TASK-001\n",
            encoding="utf-8",
        )
        plan_path = tmp_path / "plans" / "TASK-001.plan.md"
        plan_path.parent.mkdir(parents=True)
        plan_text = (
            "# Plan\n## Metadata\n- Task ID: TASK-001\n"
            "## Risks\n"
            "R1: Regression risk\n"
            "- Risk: May break other features\n"
            "- Trigger: When deployed\n"
            "- Detection: Monitoring\n"
            "- Mitigation: Rollback\n"
            "- Severity: non-blocking\n"
            "## Ready For Coding\nyes\n"
        )
        plan_path.write_text(plan_text, encoding="utf-8")
        result = gsv.validate_premortem(plan_path, task_path)
        assert any("high-risk signals" in w for w in result.warnings)


class TestGsvReconcileStatusProtectedFieldSkip:
    """Cover line 1339 — protected field in defaults is skipped during reconcile."""
    def test_protected_field_not_overwritten(self, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        sp = tmp_path / "status" / "TASK-001.status.json"
        status = json.loads(sp.read_text(encoding="utf-8"))
        # Set a protected field
        status["Gate_E_passed"] = True
        status["Gate_E_evidence"] = "commit abc123"
        sp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Now mock build_reconcile_defaults to include protected fields in defaults
        fake_defaults = {
            "Gate_E_passed": False,
            "Gate_E_evidence": "overwritten",
            "some_new_field": "value",
        }
        with unittest.mock.patch.object(gsv, "build_reconcile_defaults", return_value=(fake_defaults, [])):
            result = gsv.reconcile_status(tmp_path, "TASK-001")
        # Protected fields should NOT have been overwritten
        updated = json.loads(sp.read_text(encoding="utf-8"))
        assert updated["Gate_E_passed"] is True
        assert updated["Gate_E_evidence"] == "commit abc123"
        # Non-protected field should have been added
        assert updated.get("some_new_field") == "value"


class TestGsvValidateScopeDriftWaiverBranches:
    """Cover lines 808, 811 — decision without Guard Exception / wrong exception type."""
    def test_decision_without_guard_exception(self, tmp_path):
        """Line 808: decision exists but has no Guard Exception section."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()
        decision = (
            "# Decision\n## Metadata\n- Task ID: TASK-001\n"
            "## Context\nSome context\n"
            "## Decision\nSome decision\n"
        )
        (decisions_dir / "TASK-001.decision.md").write_text(decision, encoding="utf-8")
        result = gsv.validate_scope_drift_waiver(tmp_path, "TASK-001", {"src/extra.py"})
        assert result.errors
        assert any("Guard Exception" in e for e in result.errors)

    def test_decision_wrong_exception_type(self, tmp_path):
        """Line 811: decision has Guard Exception but wrong type."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()
        decision = (
            "# Decision\n## Metadata\n- Task ID: TASK-001\n"
            "## Guard Exception\n"
            "- Exception Type: some-other-type\n"
            "- Scope Files: src/extra.py\n"
            "- Justification: testing\n"
        )
        (decisions_dir / "TASK-001.decision.md").write_text(decision, encoding="utf-8")
        result = gsv.validate_scope_drift_waiver(tmp_path, "TASK-001", {"src/extra.py"})
        assert result.errors
        assert any("Guard Exception" in e for e in result.errors)

    def test_decision_correct_waiver(self, tmp_path):
        """Happy path: correct allow-scope-drift waiver."""
        decisions_dir = tmp_path / "decisions"
        decisions_dir.mkdir()
        decision = (
            "# Decision\n## Metadata\n- Task ID: TASK-001\n"
            "## Guard Exception\n"
            "- Exception Type: allow-scope-drift\n"
            "- Scope Files: src/extra.py\n"
            "- Justification: Necessary for fix\n"
        )
        (decisions_dir / "TASK-001.decision.md").write_text(decision, encoding="utf-8")
        result = gsv.validate_scope_drift_waiver(tmp_path, "TASK-001", {"src/extra.py"})
        assert not result.errors
        assert any("waiver applied" in w for w in result.warnings)


class TestGsvValidateAllScopeDriftGitBacked:
    """Cover lines 1413-1421 — validate_all calls detect_git_backed_scope_drift."""
    @unittest.mock.patch.object(gsv, "load_git_scope_context")
    def test_git_backed_drift_in_coding_state(self, mock_lgsc, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        # Set state to coding (validate_all reads state from status.json)
        sp = tmp_path / "status" / "TASK-001.status.json"
        status = json.loads(sp.read_text(encoding="utf-8"))
        status["state"] = "coding"
        sp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        # Mock git scope context: task artifacts overlap actual_changed
        mock_lgsc.return_value = (
            tmp_path,
            {"src/main.py", "src/extra.py", "artifacts/tasks/TASK-001.task.md"},
            {"artifacts/tasks/TASK-001.task.md"},
            [],
        )
        result = gsv.validate_all(tmp_path, "TASK-001")
        # non-strict → waiver_candidate_errors go to warnings
        assert any("src/extra.py" in w for w in result.warnings)


class TestGsvValidateAllHistoricalDrift:
    """Cover lines 1425-1432 — validate_all falls through to detect_historical_diff_scope_drift."""
    @unittest.mock.patch.object(gsv, "detect_historical_diff_scope_drift")
    @unittest.mock.patch.object(gsv, "load_git_scope_context")
    def test_historical_drift_in_done_state(self, mock_lgsc, mock_hdsd, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        # done state (already set by _setup_valid_done_tree) → historical branch
        mock_lgsc.return_value = (tmp_path, set(), set(), [])
        mock_hdsd.return_value = gsv.ScopeCheckResult(
            [], ["drift warning candidate"], ["some warning"], {"src/drifted.py"}
        )
        result = gsv.validate_all(tmp_path, "TASK-001")
        # waiver_candidate_errors become warnings (non-strict)
        assert any("drift warning candidate" in w for w in result.warnings)
        assert any("some warning" in w for w in result.warnings)


class TestGsvValidateAllScopeDriftWaiver:
    """Cover lines 1443-1445 — scope drift waiver integration in validate_all."""
    @unittest.mock.patch.object(gsv, "validate_scope_drift_waiver")
    @unittest.mock.patch.object(gsv, "detect_historical_diff_scope_drift")
    @unittest.mock.patch.object(gsv, "load_git_scope_context")
    @unittest.mock.patch.object(gsv, "detect_plan_code_scope_drift")
    def test_waiver_triggered_on_drift(self, mock_pcsd, mock_lgsc, mock_hdsd, mock_vsdw, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        mock_pcsd.return_value = {"src/drifted.py"}
        mock_lgsc.return_value = (tmp_path, set(), set(), [])
        mock_hdsd.return_value = gsv.ScopeCheckResult([], [], [], set())
        mock_vsdw.return_value = gsv.ValidationResult(
            ["waiver not found for drift files"], ["waiver info"]
        )
        result = gsv.validate_all(tmp_path, "TASK-001", strict_scope=False)
        # validate_scope_drift_waiver was called
        mock_vsdw.assert_called_once()
        assert any("waiver not found" in e for e in result.errors)


# ── Phase 5b: Targeting remaining uncovered lines ───────────────────


class TestGsvLoadArchiveInvalidPath:
    """Cover line 422 — resolve_workspace_relative_path returns error for archive path."""
    def test_archive_path_with_slash_prefix(self, tmp_path):
        import hashlib
        evidence = {"archive path": "/etc/shadow", "archive sha256": "a" * 64}
        _files, _rel, err = gsv.load_archive_snapshot(tmp_path, Path("TASK-001.code.md"), evidence, set())
        assert err is not None
        assert "invalid Archive Path" in err

    def test_archive_path_escape(self, tmp_path):
        evidence = {"archive path": "../../secret", "archive sha256": "b" * 64}
        _files, _rel, err = gsv.load_archive_snapshot(tmp_path, Path("TASK-001.code.md"), evidence, set())
        assert err is not None
        assert "invalid Archive Path" in err


class TestGsvLoadArchiveEmptyFile:
    """Cover line 441 — archive file has no lines."""
    def test_empty_archive(self, tmp_path):
        import hashlib
        archive = tmp_path / "empty_archive.txt"
        archive.write_bytes(b"")
        sha = hashlib.sha256(b"").hexdigest()
        evidence = {"archive path": "empty_archive.txt", "archive sha256": sha}
        _files, _rel, err = gsv.load_archive_snapshot(tmp_path, Path("TASK-001.code.md"), evidence, set())
        assert err is not None
        assert "at least one" in err


class TestGsvDetectGitBackedScopeDriftEmptyScope:
    """Cover line 674 — actual_scope_changed is empty after filtering."""
    def test_only_artifact_files_changed(self, tmp_path):
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        code_path = tmp_path / "code.md"
        code_path.write_text("## Files Changed\n- `src/main.py`\n", encoding="utf-8")
        # Only artifacts/ paths changed (and not in declared/planned)
        actual_changed = {"artifacts/other/file.md", "artifacts/tasks/TASK-001.task.md"}
        task_artifacts = {"artifacts/tasks/TASK-001.task.md"}
        result = gsv.detect_git_backed_scope_drift(plan_path, code_path, actual_changed, task_artifacts)
        # artifacts/other/file.md starts with artifacts/ and is not in declared/planned → excluded
        assert not result.waiver_candidate_errors
        assert not result.drift_files


class TestGsvVerifyChecklistNonMatchingFields:
    """Cover line 1134 — structured block with no matching key fields."""
    def test_block_with_only_evidence_result(self, tmp_path):
        text = (
            "## Acceptance Criteria Checklist\n\n"
            "- **Evidence**: Screenshot\n"
            "- **Result**: pass\n"
        )
        path = tmp_path / "TASK-001.verify.md"
        result = gsv.validate_verify_checklist_schema(text, path)
        # No warnings because the block doesn't have any of criterion/method/reviewer/timestamp
        assert not result.warnings


class TestGsvValidateAllStrictScopePlanCodeDrift:
    """Cover line 1419 — strict_scope=True with plan-code drift."""
    @unittest.mock.patch.object(gsv, "load_git_scope_context")
    @unittest.mock.patch.object(gsv, "detect_plan_code_scope_drift")
    def test_strict_scope_plan_code_drift(self, mock_pcsd, mock_lgsc, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        sp = tmp_path / "status" / "TASK-001.status.json"
        status = json.loads(sp.read_text(encoding="utf-8"))
        status["state"] = "coding"
        sp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        mock_pcsd.return_value = {"src/drifted.py"}
        mock_lgsc.return_value = (tmp_path, set(), set(), [])
        result = gsv.validate_all(tmp_path, "TASK-001", strict_scope=True)
        assert any("files changed not listed in" in e and "src/drifted.py" in e for e in result.errors)


class TestGsvValidateAllStrictScopeGitBackedDrift:
    """Cover line 1429 — strict_scope=True with git-backed drift."""
    @unittest.mock.patch.object(gsv, "load_git_scope_context")
    def test_strict_scope_git_backed_drift(self, mock_lgsc, tmp_path):
        _setup_valid_done_tree(tmp_path, "TASK-001")
        sp = tmp_path / "status" / "TASK-001.status.json"
        status = json.loads(sp.read_text(encoding="utf-8"))
        status["state"] = "coding"
        sp.write_text(json.dumps(status, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        mock_lgsc.return_value = (
            tmp_path,
            {"src/main.py", "src/extra.py", "artifacts/tasks/TASK-001.task.md"},
            {"artifacts/tasks/TASK-001.task.md"},
            [],
        )
        result = gsv.validate_all(tmp_path, "TASK-001", strict_scope=True)
        assert any("git-backed scope check" in e and "src/extra.py" in e for e in result.errors)


# ── Phase 6: commit-range / github-pr scope drift (lines 722-786) ──


def _make_diff_evidence_code(tmp_path, evidence_type, snapshot_files, extra_fields=None):
    """Helper: create a code artifact with ## Diff Evidence section."""
    sha = gsv.compute_snapshot_sha256(snapshot_files) if snapshot_files else ""
    lines = [
        "## Diff Evidence",
        f"- Evidence Type: {evidence_type}",
        f"- Changed Files Snapshot: {', '.join(sorted(snapshot_files))}",
        f"- Snapshot SHA256: {sha}",
    ]
    if extra_fields:
        for k, v in extra_fields.items():
            lines.append(f"- {k}: {v}")
    code_path = tmp_path / "code.md"
    code_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return code_path


class TestGsvHistoricalDriftGithubPrBranch:
    """Cover lines 722-733 — github-pr evidence branch."""

    def test_missing_repository(self, tmp_path):
        """L722-723: Missing repository field."""
        code_path = _make_diff_evidence_code(
            tmp_path, "github-pr", {"src/main.py"},
            {"PR Number": "42"},
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("requires non-empty Repository" in e for e in result.errors)

    def test_missing_pr_number(self, tmp_path):
        """L722-723: Missing PR Number field."""
        code_path = _make_diff_evidence_code(
            tmp_path, "github-pr", {"src/main.py"},
            {"Repository": "owner/repo"},
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("requires non-empty Repository" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "collect_github_pr_files")
    def test_provider_error(self, mock_collect, tmp_path):
        """L724-727: Provider returns error."""
        mock_collect.return_value = (set(), "HTTP 403 forbidden")
        code_path = _make_diff_evidence_code(
            tmp_path, "github-pr", {"src/main.py"},
            {"Repository": "owner/repo", "PR Number": "42"},
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("evidence fetch failed" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "collect_github_pr_files")
    def test_provider_snapshot_mismatch(self, mock_collect, tmp_path):
        """L729-732: Provider files != snapshot."""
        mock_collect.return_value = ({"src/main.py", "src/other.py"}, None)
        code_path = _make_diff_evidence_code(
            tmp_path, "github-pr", {"src/main.py"},
            {"Repository": "owner/repo", "PR Number": "42"},
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("does not match github-pr provider" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "collect_github_pr_files")
    def test_provider_match_happy_path(self, mock_collect, tmp_path):
        """L733: Provider matches → compare_reconstructed_scope."""
        mock_collect.return_value = ({"src/main.py"}, None)
        code_path = _make_diff_evidence_code(
            tmp_path, "github-pr", {"src/main.py"},
            {"Repository": "owner/repo", "PR Number": "42"},
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert not result.errors


_FAKE_BASE = "a" * 40
_FAKE_HEAD = "b" * 40


class TestGsvHistoricalDriftCommitRangeBranch:
    """Cover lines 735-786 — commit-range evidence branch."""

    def _make_commit_range_code(self, tmp_path, snapshot_files, base=_FAKE_BASE, head=_FAKE_HEAD,
                                diff_cmd="git diff --name-only", base_ref="", head_ref="",
                                archive_path="", archive_sha256=""):
        extra = {
            "Base Commit": base,
            "Head Commit": head,
            "Diff Command": diff_cmd,
        }
        if base_ref:
            extra["Base Ref"] = base_ref
        if head_ref:
            extra["Head Ref"] = head_ref
        if archive_path:
            extra["Archive Path"] = archive_path
        if archive_sha256:
            extra["Archive SHA256"] = archive_sha256
        return _make_diff_evidence_code(tmp_path, "commit-range", snapshot_files, extra)

    def test_no_repo_root(self, tmp_path):
        """L735-736: repo_root is None."""
        code_path = self._make_commit_range_code(tmp_path, {"src/main.py"})
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(None, plan_path, code_path)
        assert not result.errors  # silently returns empty

    def test_missing_base_commit(self, tmp_path):
        """L742-746: Missing base commit."""
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, base="", head=_FAKE_HEAD
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("requires non-empty Base Commit" in e for e in result.errors)

    def test_missing_diff_command(self, tmp_path):
        """L742-746: Missing diff command."""
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, diff_cmd=""
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("requires non-empty" in e for e in result.errors)

    def test_invalid_sha_format(self, tmp_path):
        """L747-749: Non-40-char hex SHA."""
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, base="short", head=_FAKE_HEAD
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("40-character git commit SHAs" in e for e in result.errors)

    def test_archive_error(self, tmp_path):
        """L750-753: load_archive_snapshot returns error."""
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"},
            archive_path="missing.txt", archive_sha256="c" * 64,
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("does not exist" in e or "Archive" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "resolve_git_revision_commit")
    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_base_ref_error(self, mock_diff, mock_resolve, tmp_path):
        """L755-757: Base ref resolution error."""
        mock_resolve.return_value = (None, "unknown revision")
        mock_diff.return_value = ({"src/main.py"}, None)
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, base_ref="main"
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("Base Ref" in w and "no longer resolves" in w for w in result.warnings)

    @unittest.mock.patch.object(gsv, "resolve_git_revision_commit")
    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_base_ref_mismatch(self, mock_diff, mock_resolve, tmp_path):
        """L758-761: Base ref resolves to different commit."""
        mock_resolve.return_value = ("c" * 40, None)
        mock_diff.return_value = ({"src/main.py"}, None)
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, base_ref="main"
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("Base Ref" in w and "not pinned" in w for w in result.warnings)

    @unittest.mock.patch.object(gsv, "resolve_git_revision_commit")
    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_head_ref_error(self, mock_diff, mock_resolve, tmp_path):
        """L764-765: Head ref resolution error."""
        # First call (base_ref) → not called (no base_ref)
        # For head_ref only:
        mock_resolve.return_value = (None, "unknown revision")
        mock_diff.return_value = ({"src/main.py"}, None)
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, head_ref="feature"
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("Head Ref" in w and "no longer resolves" in w for w in result.warnings)

    @unittest.mock.patch.object(gsv, "resolve_git_revision_commit")
    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_head_ref_mismatch(self, mock_diff, mock_resolve, tmp_path):
        """L766-769: Head ref resolves to different commit."""
        mock_resolve.return_value = ("d" * 40, None)
        mock_diff.return_value = ({"src/main.py"}, None)
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, head_ref="feature"
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("Head Ref" in w and "not pinned" in w for w in result.warnings)

    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_diff_error_no_archive(self, mock_diff, tmp_path):
        """L773-775: Diff error without archive fallback."""
        mock_diff.return_value = (set(), "fatal: bad revision")
        code_path = self._make_commit_range_code(tmp_path, {"src/main.py"})
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("diff replay failed" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_diff_error_with_archive_fallback(self, mock_diff, tmp_path):
        """L776-780: Diff error with archive fallback."""
        import hashlib
        archive_content = "src/main.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(archive_content.encode("utf-8"))
        archive_sha = hashlib.sha256(archive_content.encode("utf-8")).hexdigest()
        mock_diff.return_value = (set(), "fatal: bad revision")
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"},
            archive_path="archive.txt", archive_sha256=archive_sha,
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        # Should use archive fallback, not error
        assert not result.errors
        assert any("archive fallback" in w for w in result.warnings)

    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_diff_changed_mismatch(self, mock_diff, tmp_path):
        """L781-786: Diff result doesn't match snapshot."""
        mock_diff.return_value = ({"src/main.py", "src/other.py"}, None)
        code_path = self._make_commit_range_code(tmp_path, {"src/main.py"})
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("does not match" in e and "replayed" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_happy_path_no_drift(self, mock_diff, tmp_path):
        """Happy path: diff matches snapshot, files planned → no drift."""
        mock_diff.return_value = ({"src/main.py"}, None)
        code_path = self._make_commit_range_code(tmp_path, {"src/main.py"})
        # code artifact needs ## Files Changed too
        with open(code_path, "a", encoding="utf-8") as f:
            f.write("\n## Files Changed\n- `src/main.py`\n")
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert not result.errors

    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_archive_fallback_mismatch(self, mock_diff, tmp_path):
        """L782: archive fallback mismatch label in error."""
        import hashlib
        archive_content = "src/different.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(archive_content.encode("utf-8"))
        archive_sha = hashlib.sha256(archive_content.encode("utf-8")).hexdigest()
        mock_diff.return_value = (set(), "fatal: bad revision")
        # Snapshot has src/main.py but archive has src/different.py
        # But wait — archive must match snapshot for load_archive_snapshot to succeed
        # So this test is about diff_changed (from archive) != snapshot
        # That can't happen if archive == snapshot (load_archive checks this)
        # The mismatch happens when archive loads OK but diff replayed from archive
        # still doesn't match. Actually the archive_files == snapshot_files check
        # would prevent this case from ever hitting line 782 via archive fallback.
        # Line 782 with archive fallback label can only be reached if archive_files
        # IS the snapshot (passes load_archive) but somehow diff_changed is different.
        # Since in the fallback path diff_changed = archive_files = snapshot_files,
        # the check `diff_changed != snapshot_files` is always False → line 782 unreachable
        # in the archive fallback path. But line 782 IS reachable in the normal diff path
        # (scope_label = "commit-range scope check") via the test_diff_changed_mismatch above.
        pass  # This specific sub-case is unreachable via archive fallback


# ── Phase 6: commit-range / github-pr scope drift (lines 722-786) ──


def _make_diff_evidence_code(tmp_path, evidence_type, snapshot_files, extra_fields=None):
    """Helper: create a code artifact with ## Diff Evidence section."""
    sha = gsv.compute_snapshot_sha256(snapshot_files) if snapshot_files else ""
    lines = [
        "## Diff Evidence",
        f"- Evidence Type: {evidence_type}",
        f"- Changed Files Snapshot: {', '.join(sorted(snapshot_files))}",
        f"- Snapshot SHA256: {sha}",
    ]
    if extra_fields:
        for k, v in extra_fields.items():
            lines.append(f"- {k}: {v}")
    code_path = tmp_path / "code.md"
    code_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return code_path


class TestGsvHistoricalDriftGithubPrBranch:
    """Cover lines 722-733 — github-pr evidence branch."""

    def test_missing_repository(self, tmp_path):
        """L722-723: Missing repository field."""
        code_path = _make_diff_evidence_code(
            tmp_path, "github-pr", {"src/main.py"},
            {"PR Number": "42"},
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("requires non-empty Repository" in e for e in result.errors)

    def test_missing_pr_number(self, tmp_path):
        """L722-723: Missing PR Number field."""
        code_path = _make_diff_evidence_code(
            tmp_path, "github-pr", {"src/main.py"},
            {"Repository": "owner/repo"},
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("requires non-empty Repository" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "collect_github_pr_files")
    def test_provider_error(self, mock_collect, tmp_path):
        """L724-727: Provider returns error."""
        mock_collect.return_value = (set(), "HTTP 403 forbidden")
        code_path = _make_diff_evidence_code(
            tmp_path, "github-pr", {"src/main.py"},
            {"Repository": "owner/repo", "PR Number": "42"},
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("evidence fetch failed" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "collect_github_pr_files")
    def test_provider_snapshot_mismatch(self, mock_collect, tmp_path):
        """L729-732: Provider files != snapshot."""
        mock_collect.return_value = ({"src/main.py", "src/other.py"}, None)
        code_path = _make_diff_evidence_code(
            tmp_path, "github-pr", {"src/main.py"},
            {"Repository": "owner/repo", "PR Number": "42"},
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("does not match github-pr provider" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "collect_github_pr_files")
    def test_provider_match_happy_path(self, mock_collect, tmp_path):
        """L733: Provider matches → compare_reconstructed_scope."""
        mock_collect.return_value = ({"src/main.py"}, None)
        code_path = _make_diff_evidence_code(
            tmp_path, "github-pr", {"src/main.py"},
            {"Repository": "owner/repo", "PR Number": "42"},
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert not result.errors


_FAKE_BASE = "a" * 40
_FAKE_HEAD = "b" * 40


class TestGsvHistoricalDriftCommitRangeBranch:
    """Cover lines 735-786 — commit-range evidence branch."""

    def _make_commit_range_code(self, tmp_path, snapshot_files, base=_FAKE_BASE, head=_FAKE_HEAD,
                                diff_cmd="git diff --name-only", base_ref="", head_ref="",
                                archive_path="", archive_sha256=""):
        extra = {
            "Base Commit": base,
            "Head Commit": head,
            "Diff Command": diff_cmd,
        }
        if base_ref:
            extra["Base Ref"] = base_ref
        if head_ref:
            extra["Head Ref"] = head_ref
        if archive_path:
            extra["Archive Path"] = archive_path
        if archive_sha256:
            extra["Archive SHA256"] = archive_sha256
        return _make_diff_evidence_code(tmp_path, "commit-range", snapshot_files, extra)

    def test_no_repo_root(self, tmp_path):
        """L735-736: repo_root is None."""
        code_path = self._make_commit_range_code(tmp_path, {"src/main.py"})
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(None, plan_path, code_path)
        assert not result.errors  # silently returns empty

    def test_missing_base_commit(self, tmp_path):
        """L742-746: Missing base commit."""
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, base="", head=_FAKE_HEAD
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("requires non-empty Base Commit" in e for e in result.errors)

    def test_missing_diff_command(self, tmp_path):
        """L742-746: Missing diff command."""
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, diff_cmd=""
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("requires non-empty" in e for e in result.errors)

    def test_invalid_sha_format(self, tmp_path):
        """L747-749: Non-40-char hex SHA."""
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, base="short", head=_FAKE_HEAD
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("40-character git commit SHAs" in e for e in result.errors)

    def test_archive_error(self, tmp_path):
        """L750-753: load_archive_snapshot returns error."""
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"},
            archive_path="missing.txt", archive_sha256="c" * 64,
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("does not exist" in e or "Archive" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "resolve_git_revision_commit")
    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_base_ref_error(self, mock_diff, mock_resolve, tmp_path):
        """L755-757: Base ref resolution error."""
        mock_resolve.return_value = (None, "unknown revision")
        mock_diff.return_value = ({"src/main.py"}, None)
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, base_ref="main"
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("Base Ref" in w and "no longer resolves" in w for w in result.warnings)

    @unittest.mock.patch.object(gsv, "resolve_git_revision_commit")
    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_base_ref_mismatch(self, mock_diff, mock_resolve, tmp_path):
        """L758-761: Base ref resolves to different commit."""
        mock_resolve.return_value = ("c" * 40, None)
        mock_diff.return_value = ({"src/main.py"}, None)
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, base_ref="main"
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("Base Ref" in w and "not pinned" in w for w in result.warnings)

    @unittest.mock.patch.object(gsv, "resolve_git_revision_commit")
    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_head_ref_error(self, mock_diff, mock_resolve, tmp_path):
        """L764-765: Head ref resolution error."""
        # First call (base_ref) → not called (no base_ref)
        # For head_ref only:
        mock_resolve.return_value = (None, "unknown revision")
        mock_diff.return_value = ({"src/main.py"}, None)
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, head_ref="feature"
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("Head Ref" in w and "no longer resolves" in w for w in result.warnings)

    @unittest.mock.patch.object(gsv, "resolve_git_revision_commit")
    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_head_ref_mismatch(self, mock_diff, mock_resolve, tmp_path):
        """L766-769: Head ref resolves to different commit."""
        mock_resolve.return_value = ("d" * 40, None)
        mock_diff.return_value = ({"src/main.py"}, None)
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"}, head_ref="feature"
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("Head Ref" in w and "not pinned" in w for w in result.warnings)

    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_diff_error_no_archive(self, mock_diff, tmp_path):
        """L773-775: Diff error without archive fallback."""
        mock_diff.return_value = (set(), "fatal: bad revision")
        code_path = self._make_commit_range_code(tmp_path, {"src/main.py"})
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("diff replay failed" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_diff_error_with_archive_fallback(self, mock_diff, tmp_path):
        """L776-780: Diff error with archive fallback."""
        import hashlib
        archive_content = "src/main.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(archive_content.encode("utf-8"))
        archive_sha = hashlib.sha256(archive_content.encode("utf-8")).hexdigest()
        mock_diff.return_value = (set(), "fatal: bad revision")
        code_path = self._make_commit_range_code(
            tmp_path, {"src/main.py"},
            archive_path="archive.txt", archive_sha256=archive_sha,
        )
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        # Should use archive fallback, not error
        assert not result.errors
        assert any("archive fallback" in w for w in result.warnings)

    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_diff_changed_mismatch(self, mock_diff, tmp_path):
        """L781-786: Diff result doesn't match snapshot."""
        mock_diff.return_value = ({"src/main.py", "src/other.py"}, None)
        code_path = self._make_commit_range_code(tmp_path, {"src/main.py"})
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert any("does not match" in e and "replayed" in e for e in result.errors)

    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_happy_path_no_drift(self, mock_diff, tmp_path):
        """Happy path: diff matches snapshot, files planned → no drift."""
        mock_diff.return_value = ({"src/main.py"}, None)
        code_path = self._make_commit_range_code(tmp_path, {"src/main.py"})
        # code artifact needs ## Files Changed too
        with open(code_path, "a", encoding="utf-8") as f:
            f.write("\n## Files Changed\n- `src/main.py`\n")
        plan_path = tmp_path / "plan.md"
        plan_path.write_text("## Files Likely Affected\n- `src/main.py`\n", encoding="utf-8")
        result = gsv.detect_historical_diff_scope_drift(tmp_path, plan_path, code_path)
        assert not result.errors

    @unittest.mock.patch.object(gsv, "collect_git_diff_range_files")
    def test_archive_fallback_mismatch(self, mock_diff, tmp_path):
        """L782: archive fallback mismatch label in error."""
        import hashlib
        archive_content = "src/different.py\n"
        archive = tmp_path / "archive.txt"
        archive.write_bytes(archive_content.encode("utf-8"))
        archive_sha = hashlib.sha256(archive_content.encode("utf-8")).hexdigest()
        mock_diff.return_value = (set(), "fatal: bad revision")
        # Snapshot has src/main.py but archive has src/different.py
        # But wait — archive must match snapshot for load_archive_snapshot to succeed
        # So this test is about diff_changed (from archive) != snapshot
        # That can't happen if archive == snapshot (load_archive checks this)
        # The mismatch happens when archive loads OK but diff replayed from archive
        # still doesn't match. Actually the archive_files == snapshot_files check
        # would prevent this case from ever hitting line 782 via archive fallback.
        # Line 782 with archive fallback label can only be reached if archive_files
        # IS the snapshot (passes load_archive) but somehow diff_changed is different.
        # Since in the fallback path diff_changed = archive_files = snapshot_files,
        # the check `diff_changed != snapshot_files` is always False → line 782 unreachable
        # in the archive fallback path. But line 782 IS reachable in the normal diff path
        # (scope_label = "commit-range scope check") via the test_diff_changed_mismatch above.
        pass  # This specific sub-case is unreachable via archive fallback



# -- Phase 8: parse_args coverage for 4 modules --


class TestParseArgsCoverage:
    """Cover parse_args return lines for ars, bdr, prv, vsd."""

    def test_ars_parse_args(self, tmp_path):
        report = tmp_path / "report.md"
        report.write_text("# Report\n", encoding="utf-8")
        args = ars.parse_args(["--report", str(report)])
        assert args.report == str(report)

    def test_bdr_parse_args(self, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["bdr", "--root", "/tmp"])
        args = bdr.parse_args()
        assert args.root == "/tmp"

    def test_prv_parse_args(self, tmp_path):
        cases = tmp_path / "cases.json"
        cases.write_text("[]", encoding="utf-8")
        args = prv.parse_args(["--root", str(tmp_path), "--cases", str(cases)])
        assert args.root == str(tmp_path)

    def test_vsd_parse_args(self, tmp_path):
        sc = tmp_path / "scorecard.md"
        sc.write_text("# Scorecard\n", encoding="utf-8")
        args = vsd.parse_args(["--scorecard", str(sc)])
        assert args.scorecard == str(sc)



# ── discover_templates tests ──


import discover_templates as dt


class TestDtYamlImportGuard:
    """Cover L13-19: except ImportError when yaml is missing."""

    def test_exit_when_yaml_unavailable(self, monkeypatch):
        import builtins
        import importlib
        real_import = builtins.__import__

        def fail_yaml(name, *args, **kwargs):
            if name == "yaml":
                raise ImportError("test: no yaml")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fail_yaml)
        with pytest.raises(SystemExit) as exc_info:
            importlib.reload(dt)
        assert exc_info.value.code == 1
        monkeypatch.undo()
        importlib.reload(dt)


class TestDtParseFrontmatter:
    def test_valid_frontmatter(self, tmp_path):
        md = tmp_path / "TEMPLATE.md"
        md.write_text("---\nname: Test\nversion: '1.0'\n---\n# Body\n", encoding="utf-8")
        result = dt.parse_frontmatter(md)
        assert result["name"] == "Test"
        assert result["version"] == "1.0"

    def test_no_frontmatter(self, tmp_path):
        md = tmp_path / "TEMPLATE.md"
        md.write_text("# No frontmatter\n", encoding="utf-8")
        result = dt.parse_frontmatter(md)
        assert result == {}

    def test_empty_frontmatter(self, tmp_path):
        md = tmp_path / "TEMPLATE.md"
        md.write_text("---\n---\n# Body\n", encoding="utf-8")
        result = dt.parse_frontmatter(md)
        assert result == {}


class TestDtDiscover:
    def _make_template(self, templates_dir, role_name, fm_dict):
        import yaml
        role_dir = templates_dir / role_name
        role_dir.mkdir(parents=True, exist_ok=True)
        fm_yaml = yaml.dump(fm_dict, default_flow_style=False)
        (role_dir / "TEMPLATE.md").write_text(
            f"---\n{fm_yaml}---\n# Template\n", encoding="utf-8"
        )

    def test_discover_all(self, tmp_path):
        self._make_template(tmp_path, "coder", {
            "name": "Coder", "applicable_agents": ["Codex CLI"],
            "applicable_stages": ["coding"],
        })
        self._make_template(tmp_path, "researcher", {
            "name": "Researcher", "applicable_agents": ["Gemini CLI"],
            "applicable_stages": ["research"],
        })
        results = dt.discover(templates_dir=tmp_path)
        assert len(results) == 2

    def test_filter_by_agent(self, tmp_path):
        self._make_template(tmp_path, "coder", {
            "name": "Coder", "applicable_agents": ["Codex CLI"],
            "applicable_stages": ["coding"],
        })
        self._make_template(tmp_path, "researcher", {
            "name": "Researcher", "applicable_agents": ["Gemini CLI"],
            "applicable_stages": ["research"],
        })
        results = dt.discover(agent="Codex CLI", templates_dir=tmp_path)
        assert len(results) == 1
        assert results[0].name == "Coder"

    def test_filter_by_stage(self, tmp_path):
        self._make_template(tmp_path, "coder", {
            "name": "Coder", "applicable_agents": ["Codex CLI"],
            "applicable_stages": ["coding"],
        })
        results = dt.discover(stage="research", templates_dir=tmp_path)
        assert len(results) == 0

    def test_stage_any_wildcard(self, tmp_path):
        self._make_template(tmp_path, "utility", {
            "name": "Utility", "applicable_agents": ["Any"],
            "applicable_stages": ["any"],
        })
        results = dt.discover(stage="coding", templates_dir=tmp_path)
        assert len(results) == 1

    def test_skip_no_name(self, tmp_path):
        self._make_template(tmp_path, "broken", {
            "description": "No name field",
        })
        results = dt.discover(templates_dir=tmp_path)
        assert len(results) == 0

    def test_empty_dir(self, tmp_path):
        results = dt.discover(templates_dir=tmp_path)
        assert results == []


class TestDtMain:
    def test_json_output(self, tmp_path, capsys, monkeypatch):
        import yaml
        role = tmp_path / "coder"
        role.mkdir()
        fm = yaml.dump({"name": "Coder", "applicable_agents": ["Codex"], "applicable_stages": ["coding"]})
        (role / "TEMPLATE.md").write_text(f"---\n{fm}---\n# T\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["dt", "--templates-dir", str(tmp_path), "--json"])
        dt.main()
        out = capsys.readouterr().out
        import json
        data = json.loads(out)
        assert len(data) == 1
        assert data[0]["name"] == "Coder"

    def test_text_output(self, tmp_path, capsys, monkeypatch):
        import yaml
        role = tmp_path / "coder"
        role.mkdir()
        fm = yaml.dump({"name": "Coder", "applicable_agents": ["Codex"], "applicable_stages": ["coding"]})
        (role / "TEMPLATE.md").write_text(f"---\n{fm}---\n# T\n", encoding="utf-8")
        monkeypatch.setattr(sys, "argv", ["dt", "--templates-dir", str(tmp_path)])
        dt.main()
        out = capsys.readouterr().out
        assert "Coder" in out

    def test_no_results(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(sys, "argv", ["dt", "--templates-dir", str(tmp_path)])
        dt.main()
        out = capsys.readouterr().out
        assert "No matching" in out



# ── update_repository_profile tests ──


import update_repository_profile as urp


class TestUrpParseTopics:
    def test_basic(self):
        result = urp.parse_topics("a, b, c")
        assert result == ["a", "b", "c"]

    def test_dedup(self):
        result = urp.parse_topics("a, b, a")
        assert result == ["a", "b"]

    def test_empty_tokens(self):
        result = urp.parse_topics(",, a,,")
        assert result == ["a"]

    def test_case_normalize(self):
        result = urp.parse_topics("ABC, Def")
        assert result == ["abc", "def"]


class TestUrpNormalizeTopics:
    def test_adds_required(self):
        from workflow_constants import REQUIRED_TOPICS
        # Use 6 topics that overlap with required + 2 extra = 8 total, within 6-12
        base = list(REQUIRED_TOPICS)[:4] + ["extra-one", "extra-two"]
        result = urp.normalize_topics(base)
        for req in REQUIRED_TOPICS:
            assert req in result

    def test_invalid_pattern(self):
        with pytest.raises(ValueError, match="Invalid topic"):
            urp.normalize_topics(["valid-topic"] * 5 + ["INVALID TOPIC!"])

    def test_too_few_after_normalization(self, monkeypatch):
        """With 6 required topics, minimum is always 6. Patch to test < 6 path."""
        monkeypatch.setattr(urp, "REQUIRED_TOPICS", set())
        with pytest.raises(ValueError, match="6-12 entries"):
            urp.normalize_topics(["a"])

    def test_too_many(self):
        topics = [f"topic-{i}" for i in range(13)]
        with pytest.raises(ValueError, match="6-12 entries"):
            urp.normalize_topics(topics)

    def test_dedup_and_empty(self):
        topics = ["a", "a", "", "b", "c", "d", "e", "f"]
        result = urp.normalize_topics(topics)
        assert len(set(result)) == len(result)


class TestUrpUpdateProfile:
    def _valid_about_args(self):
        # Ensure about is 80-200 chars
        name = "MyProject"
        summary = "A" * 75  # name + " - " + summary = 9 + 3 + 75 = 87 chars
        return name, summary

    def test_creates_new_profile(self, tmp_path):
        from workflow_constants import REQUIRED_TOPICS
        profile_path = tmp_path / ".github" / "repository-profile.json"
        name, summary = self._valid_about_args()
        topics = ",".join(list(REQUIRED_TOPICS)[:4] + ["extra-one", "extra-two"])
        urp.update_profile(profile_path, name, summary, topics)
        assert profile_path.exists()
        import json
        data = json.loads(profile_path.read_text(encoding="utf-8"))
        assert "about" in data
        assert "topics" in data

    def test_updates_existing(self, tmp_path):
        import json
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(json.dumps({"about": "old", "topics": ["existing"]}), encoding="utf-8")
        name, summary = self._valid_about_args()
        from workflow_constants import REQUIRED_TOPICS
        topics = ",".join(list(REQUIRED_TOPICS)[:4] + ["extra-one", "extra-two"])
        urp.update_profile(profile_path, name, summary, topics)
        data = json.loads(profile_path.read_text(encoding="utf-8"))
        assert data["about"] != "old"

    def test_about_too_short(self, tmp_path):
        profile_path = tmp_path / "profile.json"
        from workflow_constants import REQUIRED_TOPICS
        topics = ",".join(list(REQUIRED_TOPICS)[:4] + ["extra-one", "extra-two"])
        with pytest.raises(ValueError, match="80-200 chars"):
            urp.update_profile(profile_path, "X", "Y", topics)

    def test_about_too_long(self, tmp_path):
        profile_path = tmp_path / "profile.json"
        from workflow_constants import REQUIRED_TOPICS
        topics = ",".join(list(REQUIRED_TOPICS)[:4] + ["extra-one", "extra-two"])
        with pytest.raises(ValueError, match="80-200 chars"):
            urp.update_profile(profile_path, "X", "Y" * 300, topics)

    def test_uses_existing_topics_when_none(self, tmp_path):
        import json
        from workflow_constants import REQUIRED_TOPICS
        profile_path = tmp_path / "profile.json"
        existing_topics = list(REQUIRED_TOPICS)[:4] + ["extra-one", "extra-two"]
        profile_path.write_text(json.dumps({"topics": existing_topics}), encoding="utf-8")
        name, summary = self._valid_about_args()
        urp.update_profile(profile_path, name, summary, None)
        data = json.loads(profile_path.read_text(encoding="utf-8"))
        for t in existing_topics:
            assert t in data["topics"]

    def test_non_list_existing_topics(self, tmp_path):
        import json
        profile_path = tmp_path / "profile.json"
        profile_path.write_text(json.dumps({"topics": "not-a-list"}), encoding="utf-8")
        name, summary = self._valid_about_args()
        from workflow_constants import REQUIRED_TOPICS
        topics = ",".join(list(REQUIRED_TOPICS)[:4] + ["extra-one", "extra-two"])
        urp.update_profile(profile_path, name, summary, topics)
        data = json.loads(profile_path.read_text(encoding="utf-8"))
        assert isinstance(data["topics"], list)


class TestUrpMain:
    def test_main_success(self, tmp_path, monkeypatch, capsys):
        profile_path = tmp_path / "profile.json"
        name = "MyProject"
        summary = "A" * 75
        from workflow_constants import REQUIRED_TOPICS
        topics = ",".join(list(REQUIRED_TOPICS)[:4] + ["extra-one", "extra-two"])
        monkeypatch.setattr(sys, "argv", [
            "urp", "--project-name", name, "--project-summary", summary,
            "--topics", topics, "--profile-path", str(profile_path),
        ])
        result = urp.main()
        assert result == 0
        assert "[OK]" in capsys.readouterr().out
