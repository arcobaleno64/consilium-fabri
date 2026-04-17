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
