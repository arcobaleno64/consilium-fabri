# Task: TASK-982 GitHub PR API Host Allowlist Short Sprint

## Metadata
- Task ID: TASK-982
- Artifact Type: task
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-17T22:15:00+08:00

## Objective
針對 root repo threat model 的 FIND-04，完成一輪最小可驗證的短衝：把 `github-pr` diff evidence 的 API Base URL 從「任意 absolute http(s) URL」收斂為「預設只允許 `https://api.github.com`，企業 GitHub host 必須經顯式 allowlist」，並補上對應的 unit tests、紅隊案例與文件同步。

## Background
- [threat-model-20260417-124620/3-findings.md](threat-model-20260417-124620/3-findings.md) 的 FIND-04 指出 [artifacts/scripts/guard_status_validator.py](artifacts/scripts/guard_status_validator.py) 目前接受任意 absolute `http(s)` API Base URL，可能讓 GitHub PR replay 路徑變成對外連線能力。
- 現有紅隊案例 [docs/red_team_runbook.md](docs/red_team_runbook.md) 到 RT-023 為止，尚未覆蓋「未 allowlist 的自訂 GitHub API host 應拒絕」與「顯式 allowlist 的企業 host 應可通過」這兩個邊界。
- 這一輪目標是先收斂最直接的 guard 邊界與 coverage，不同時處理 artifact size ceiling、publish boundary 或 agent dispatch 的其他開放風險。

## Inputs
- [threat-model-20260417-124620/3-findings.md](threat-model-20260417-124620/3-findings.md)
- [artifacts/scripts/guard_status_validator.py](artifacts/scripts/guard_status_validator.py)
- [artifacts/scripts/test_guard_units.py](artifacts/scripts/test_guard_units.py)
- [artifacts/scripts/run_red_team_suite.py](artifacts/scripts/run_red_team_suite.py)
- [docs/red_team_runbook.md](docs/red_team_runbook.md)
- [README.md](README.md)
- [README.zh-TW.md](README.zh-TW.md)

## Constraints
- 預設行為必須維持可直接使用 `https://api.github.com`，不能破壞既有 GitHub.com replay 流程。
- 自訂 enterprise host 不得預設放行；必須依顯式 allowlist 機制才可接受。
- 若修改 guard、runbook 或 README，必須同步 `template/` 對應檔案。
- 本 task 只處理 API host allowlist guard 與 coverage，不新增 artifact size ceiling、publish automation 或 credential hygiene 的修補。

## Acceptance Criteria
- [ ] AC-1: `normalize_api_base_url(...)` 預設只接受空值對應的 `https://api.github.com` 與明確 allowlist 的自訂 GitHub API host；未 allowlist 的自訂 host 會回傳明確錯誤。
- [ ] AC-2: `test_guard_units.py` 新增或更新測試，覆蓋預設 GitHub.com、未 allowlist 自訂 host、allowlist 自訂 host，以及 `collect_github_pr_files(...)` 的拒絕路徑。
- [ ] AC-3: red-team suite 新增對應案例，至少涵蓋「未 allowlist host 被拒絕」與「allowlisted host 可成功通過 provider replay」其中一正一反邊界，並更新 runbook case matrix。
- [ ] AC-4: root / `template/` 的 guard script、tests、runbook 與 README 同步完成。
- [ ] AC-5: 驗證證據至少包含 guard 單元測試、紅隊靜態案例、contract guard 與 TASK-982 status guard。

## Dependencies
- Python 3
- 現有 `github-pr` diff evidence 與 `run_red_team_suite.py` 的 provider 模擬器

## Out of Scope
- Artifact size ceiling / replay payload size 上限
- Publish automation remote verification
- Agent dispatch prompt/context reduction
- Red-team runner dynamic import hardening

## Assurance Level
POC

## Project Adapter
generic

## Current Status Summary
Planned。這是一個 lightweight 短衝，先把 GitHub PR replay 的外部 host 邊界收斂成 allowlist 模式，再把該邊界落成 unit tests、紅隊案例與文件說明。
