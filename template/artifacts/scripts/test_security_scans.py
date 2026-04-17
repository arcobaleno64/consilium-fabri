"""Unit tests for repo-local security scanning rules."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))

import repo_security_scan as rss


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


class TestSecretHelpers:
    def test_placeholder_secret_is_ignored(self):
        assert rss.is_placeholder_secret("ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx") is True

    def test_entropy_gate_for_generic_assignment(self):
        assert rss.generic_secret_is_actionable("AbCdEfGh1234567890") is True
        assert rss.generic_secret_is_actionable("xxxxxxxxxxxxxxxxxxxx") is False


class TestSecretScan:
    def test_detects_github_pat(self, tmp_path: Path):
        sample_secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
        _write(tmp_path / "artifacts" / "scripts" / "sample.py", f'token = "{sample_secret}"\n')
        findings = rss.scan_secrets(tmp_path)
        assert any(f.rule_id == "github-pat-classic" for f in findings)

    def test_ignores_placeholder_pat(self, tmp_path: Path):
        _write(tmp_path / "README.md", 'token = "ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"\n')
        findings = rss.scan_secrets(tmp_path)
        assert findings == []

    def test_detects_generic_secret_assignment(self, tmp_path: Path):
        secret_value = "AbCdEfGh" + "1234567890ZyXwVu"
        _write(tmp_path / "artifacts" / "scripts" / "config.py", f'client_secret = "{secret_value}"\n')
        findings = rss.scan_secrets(tmp_path)
        assert any(f.rule_id == "generic-secret-assignment" for f in findings)

    def test_excludes_skill_reference_tree(self, tmp_path: Path):
        sample_secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
        _write(tmp_path / ".github" / "skills" / "demo" / "reference.md", f'token = "{sample_secret}"\n')
        findings = rss.scan_secrets(tmp_path)
        assert findings == []


class TestStaticScan:
    def test_detects_unpinned_action(self, tmp_path: Path):
        _write(
            tmp_path / ".github" / "workflows" / "bad.yml",
            "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@v4\n",
        )
        findings = rss.scan_static(tmp_path)
        assert any(f.rule_id == "workflow-unpinned-action" for f in findings)

    def test_detects_python_shell_true(self, tmp_path: Path):
        shell_line = "subprocess.run('echo hi', shell" + "=True)"
        _write(
            tmp_path / "artifacts" / "scripts" / "bad.py",
            f"import subprocess\n{shell_line}\n",
        )
        findings = rss.scan_static(tmp_path)
        assert any(f.rule_id == "python-shell-true" for f in findings)

    def test_detects_powershell_invoke_expression(self, tmp_path: Path):
        _write(tmp_path / "artifacts" / "scripts" / "bad.ps1", "Invoke-Expression $Command\n")
        findings = rss.scan_static(tmp_path)
        assert any(f.rule_id == "powershell-invoke-expression" for f in findings)

    def test_scans_template_workflows_too(self, tmp_path: Path):
        _write(
            tmp_path / "template" / ".github" / "workflows" / "bad.yml",
            "jobs:\n  test:\n    steps:\n      - uses: actions/setup-python@v5\n",
        )
        findings = rss.scan_static(tmp_path)
        assert any(f.path.startswith("template/.github/workflows/") for f in findings)

    def test_reports_clean_repo(self, tmp_path: Path):
        _write(
            tmp_path / ".github" / "workflows" / "ok.yml",
            "jobs:\n  test:\n    steps:\n      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2\n        with:\n          persist-credentials: false\n",
        )
        _write(tmp_path / "artifacts" / "scripts" / "ok.py", "print('safe')\n")
        assert rss.scan_static(tmp_path) == []


def test_cli_json_output_for_secrets(tmp_path: Path, capsys: pytest.CaptureFixture[str]):
    sample_secret = "ghp_" + "A1b2C3d4E5f6G7h8I9j0K1l2M3n4O5p6Q7r8"
    _write(tmp_path / "artifacts" / "scripts" / "sample.py", f'token = "{sample_secret}"\n')
    exit_code = rss.main(["--root", str(tmp_path), "--json", "secrets"])
    captured = capsys.readouterr().out
    assert exit_code == 1
    assert "github-pat-classic" in captured