# Task: TASK-980 Root Repo Threat Model And Security Regression Scans

## Metadata
- Task ID: TASK-980
- Artifact Type: task
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-17T20:46:20+08:00

## Objective
為 root repo 建立一份可追溯的 threat model，並把兩條最直接對應控制面風險的安全回歸檢查落地到既有 CI：

1. 先完成 root repo 的正式威脅模型輸出，聚焦 artifact boundary、subprocess / agent dispatch、token handling、GitHub API、path handling 與 guard waiver 濫用風險。
2. 補上一條 repo 內建的 secrets 掃描，攔截高信心憑證外洩樣式。
3. 補上一條聚焦式靜態規則掃描，專門守住 workflow / Python / PowerShell 腳本裡最容易造成控制面退化的高風險模式。

## Background
- root repo 目前已有 [.github/workflows/security-scan.yml](https://github.com/arcobaleno64/consilium-fabri/blob/master/.github/workflows/security-scan.yml) 以 `pip-audit` 提供 dependency baseline，但尚未覆蓋 secrets 洩漏與 repo-specific control-plane foot-guns。
- 目前 workspace 內找不到既有的 threat-model-YYYYMMDD-HHmmss 報告資料夾，也找不到 formal `security-review` 風格的 root-repo 應用面安全報告。
- root repo 的主要風險不是傳統 web app 的 SQL injection / XSS，而是 workflow orchestrator 本身對 artifact、filesystem、GitHub API 與本地腳本執行邊界的處理方式。
- root repo 已有 supply-chain baseline 與 red-team / guard 驗證鏈，因此這次新增的掃描必須與既有 `security-scan` / `workflow-guards` 思路整合，而不是平行再造另一套流程。

## Inputs
- 使用者需求：先做 root repo threat model，再補 secrets 掃描與聚焦式靜態規則掃描。
- [.github/workflows/security-scan.yml](https://github.com/arcobaleno64/consilium-fabri/blob/master/.github/workflows/security-scan.yml)
- [.github/workflows/workflow-guards.yml](https://github.com/arcobaleno64/consilium-fabri/blob/master/.github/workflows/workflow-guards.yml)
- [artifacts/scripts/guard_status_validator.py](https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/guard_status_validator.py)
- [artifacts/scripts/run_red_team_suite.py](https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/run_red_team_suite.py)
- [artifacts/scripts/github_publish_common.ps1](https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/github_publish_common.ps1)
- [docs/artifact_schema.md](https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/artifact_schema.md)
- [docs/premortem_rules.md](https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/premortem_rules.md)

## Constraints
- 不得把真實 token、PAT、connection string 或其他 secret 寫入 repo、artifact、memory 或測試 fixture。
- secrets / static scans 需優先採 repo-local 腳本與可驗證規則，避免再引入不必要第三方 action 依賴。
- threat model 必須只針對 root repo，不能把 `external/hermes-agent/` 的架構與風險混入同一份結論。
- 若修改 `.github/`、`artifacts/scripts/`、README 或 workflow 說明，屬於 workflow 變更，必須同步 `template/`。
- 新增掃描不能靠大量已知誤報通過；規則必須夠聚焦，能在目前 root repo 與 template 下穩定綠燈。

## Acceptance Criteria
- [ ] AC-1: root repo 新增一份 timestamped threat model 報告資料夾，至少包含 `0-assessment.md`、`0.1-architecture.md`、`1-threatmodel.md`、`1.1-threatmodel.mmd`、`2-stride-analysis.md`、`3-findings.md` 與 `threat-inventory.json`。
- [ ] AC-2: 既有 `security-scan` workflow 擴充為同時執行 dependency baseline、secrets scan 與 focused static rules scan，且權限維持 least privilege。
- [ ] AC-3: secrets scan 能攔截高信心 secret patterns，並避免把 repo 內示例 / placeholder 字串誤判成真實洩漏。
- [ ] AC-4: focused static rules scan 至少覆蓋 workflow unpinned actions、`persist-credentials: true`、`pull_request_target`、Python `shell=True` / `exec` / `eval`、PowerShell `Invoke-Expression` 與明顯 secret logging 樣式。
- [ ] AC-5: root 與 `template/` 的 workflow、腳本與 README 同步完成。
- [ ] AC-6: 驗證證據至少包含 unit tests、contract guard 與對應 task status guard。

## Dependencies
- None

## Out of Scope
- 對 `external/hermes-agent/` 套用同一份 threat model 或掃描規則
- 新增 GitHub Advanced Security / CodeQL / org-level security policy 設定
- 對所有既有腳本做全面 refactor 或一次性修完所有 threat model findings
- 取代既有 `pip-audit` baseline 或變更 release / wiki publish 功能需求

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
盤點已完成：root repo 目前沒有正式 threat model 輸出，也沒有針對 workflow / script control plane 的 secrets 與 focused static regression scan。現有最佳切入點是以 repo-local threat model 補上風險地圖，再把兩條最直接的掃描整合進既有 `security-scan` workflow。
