# Task: TASK-963 GitHub Actions Supply-Chain Hardening And Publish Automation

## Metadata
- Task ID: TASK-963
- Artifact Type: task
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-16T21:51:20+08:00

## Objective
為本 repo 制定並後續落地一套可驗證的 GitHub delivery hardening 方案：
1. 將 GitHub Actions 第三方 action 參照改為不可變版本策略。
2. 補上一條獨立的 dependency / security scan。
3. 將 Wiki / Release 發布前置檢查、認證來源與失敗路徑整理成可重跑腳本，特別是 wiki 尚未初始化時要有明確處置。

## Background
- 目前主 CI 僅有 [.github/workflows/workflow-guards.yml](https://github.com/arcobaleno64/consilium-fabri/blob/master/.github/workflows/workflow-guards.yml)，其中 `actions/checkout@v4` 與 `actions/setup-python@v5` 仍採 tag reference，而非 full commit SHA。
- repo 目前沒有 `.github/dependabot.yml`，也沒有獨立的 security / dependency scanning workflow。
- 現有 [artifacts/scripts/push-wiki.ps1](https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/push-wiki.ps1) 明確要求先在 GitHub Web UI 建立第一個 wiki page，否則 clone wiki repo 會失敗。
- `artifacts/scripts/` 內目前沒有對應 release publish 的 repo-local 腳本；release 發布條件與 auth 路徑尚未被整理成可重跑 preflight。

## Inputs
- 使用者需求：
  - GitHub Actions 加上 SHA pinning 或 Dependabot，降低 action supply-chain 風險。
  - 補一條獨立的 dependency / security scan，例如 pip-audit 或 CodeQL。
  - 整理 Wiki / Release 發布流程的認證與初始化條件，特別是 wiki repo 尚未初始化時的失敗路徑。
- [.github/workflows/workflow-guards.yml](https://github.com/arcobaleno64/consilium-fabri/blob/master/.github/workflows/workflow-guards.yml)
- [artifacts/scripts/push-wiki.ps1](https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/push-wiki.ps1)
- [requirements.txt](https://github.com/arcobaleno64/consilium-fabri/blob/master/requirements.txt)
- GitHub 官方文件與 pip-audit 官方文件（見 `artifacts/research/TASK-963.research.md`）

## Constraints
- 不得把 PAT、token 或任何 secret 寫入 repo、artifact 或 memory。
- 認證必須優先走環境變數 `GITHUB_TOKEN` / `GH_TOKEN` 或 `gh auth`，並採 least privilege。
- wiki 初始化不得依賴未驗證的 undocumented behavior；若 GitHub 官方只保證手動建立第一頁，腳本必須把該前置條件顯式化。
- security scan 的選型必須考量目前 repo 的實際可用性；若依賴 GitHub Code Security entitlement，需先確認 repo 類型或授權。
- 後續若修改 `.github/`、`artifacts/scripts/` 或文件，屬於 workflow 變更，實作階段必須同步 `template/`。

## Acceptance Criteria
- [ ] AC-1: 明確決定 action supply-chain hardening 的實作策略，至少涵蓋 full SHA pinning，並定義後續更新機制。
- [ ] AC-2: repo 新增一條獨立的 dependency / security scan，選型與觸發條件有明確理由與驗證方式。
- [ ] AC-3: Wiki publish 流程改為可重跑腳本，能在 auth 缺失、wiki 未初始化、無變更等情況下給出明確結果與退出路徑。
- [ ] AC-4: Release publish 流程改為可重跑腳本，能在 auth 缺失、tag / release 狀態不符、draft / publish 模式差異下給出明確結果與退出路徑。
- [ ] AC-5: 文件清楚列出需要的權限、環境變數、一次性手動步驟與不可自動化之處。
- [ ] AC-6: 若實作涉及 workflow 或腳本，root 與 `template/` 同步完成。

## Dependencies
- None

## Out of Scope
- 直接在 GitHub 網頁或組織層設定中手動啟用 security features
- 建立新的發佈通道（例如 GitHub Pages、package registry）
- 真正執行 live wiki push 或 live release publish
- 對 `external/` 內第三方專案做同步 hardening

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Research 與 planning 已完成。推薦方向為：action 採 full SHA pinning 並同時加入 Dependabot 維護更新；獨立掃描先以 pip-audit 作為 guaranteed baseline，CodeQL 視 repo 可用權限再列為 follow-up；Wiki / Release 流程需改成帶 preflight 的可重跑腳本，其中 wiki 未初始化視為明確 blocking path，而不是讓 git clone 直接失敗。
