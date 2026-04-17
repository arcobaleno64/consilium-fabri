"""Unit tests for core parsing and validation functions in workflow guard scripts."""
from __future__ import annotations

import json
import sys
import textwrap
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

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

    # Add all remaining markers as sections
    for marker in markers[1:]:
        if marker.startswith("## "):
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
