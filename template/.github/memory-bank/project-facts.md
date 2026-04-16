# Project Facts — 技術棧、集成點、部署約定

**Last Updated**: 2026-04-16 +08:00  
**Maintained by**: Core Team  
**Review Cycle**: Quarterly

技術棧
Language: Python 3.9+  
Framework: N/A (CLI utility)  
Testing: pytest  
Linting: pylint 加 black  
Version Control: Git 加 GitHub  
CI/CD: GitHub Actions (see .github/workflows/)  
Context Tooling: code2prompt (optional, 用於 pack-context CLI mode, `cargo install code2prompt`)

## 主要組件

| 組件 | 檔案 | 說明 |
|---|---|---|
| Guard Status Validator | artifacts/scripts/guard_status_validator.py | Artifact 流程檢查 |
| Guard Contract Validator | artifacts/scripts/guard_contract_validator.py | Prompt 和 README 同步檢查 |
| Red Team Suite | artifacts/scripts/run_red_team_suite.py | 自動化紅隊演練 |
| Regression Validator | artifacts/scripts/prompt_regression_validator.py | Prompt 變更檢測 |

## 已知集成點

### GitHub API
用途：讀取 PR 和 issue metadata, 推送 artifact 到 release notes  
認證：Personal access token（環境變數 GITHUB_TOKEN，勿寫進 memory）  
端點：api.github.com/repos/{{ORG}}/{{REPO}}/...

### Upstream Repo（若有 fork）
Location: external/{{REPO_NAME}}-upstream-pr/  
同步方式：Each PR reset to upstream/<default> via git fetch upstream 加 git reset --hard upstream/main  
Protected: 禁止本地特性分支進入此目錄

## 環境變數

| 變數 | 用途 | 示例 | 必需 |
|---|---|---|---|
| GITHUB_TOKEN | 驗證 GitHub API | ghp_xxx... | 否（fallback 為唯讀） |
| PYTHONPATH | Import artifacts/scripts | C:\...\CLI | 用於 guard scripts |
| .venv/ | Python venv | 在執行 guard 前啟動 | 是 |

## 構建和部署

本地測試：
python -m pytest tests/

執行 guard：
python artifacts/scripts/guard_status_validator.py --task-id TASK-900

執行紅隊演練：
python artifacts/scripts/run_red_team_suite.py --phase all

## 常見故障排查

| 問題 | 原因 | 解決 |
|---|---|---|
| Guard 找不到 task artifact | Filename 不符 TASK-XXX 格式 | 確認 artifacts/tasks/TASK-XXX.task.md |
| Prompt regression 失敗 | CLAUDE.md 或 GEMINI.md 變更了 | 執行 guard_contract_validator 檢查 diff |
| CI timeout on red-team | Phase all 太重 | 改用 --phase inference 或 --phase static |

## 版本歷史

v1.0 (2026-04-16): 初版，基於 workflow v3
