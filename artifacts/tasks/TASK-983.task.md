# Task: TASK-983 Artifact Size Ceilings And Replay Byte Caps

## Metadata
- Task ID: TASK-983
- Artifact Type: task
- Owner: Claude
- Status: approved
- Last Updated: 2026-04-17T23:45:00+08:00

## Objective

針對 root repo threat model 的 FIND-02，完成一輪最小可驗證的短衝：為高信任 artifact 讀取與 diff-evidence replay 加上明確 size ceilings / byte caps，避免 oversized Markdown、JSON、archive snapshot 或 provider response 把 validator 與紅隊流程拖進高成本解析路徑。

## Background

- [threat-model-20260417-124620/3-findings.md](threat-model-20260417-124620/3-findings.md) 的 FIND-02 指出目前缺少一致的 artifact size ceiling、archive snapshot size ceiling 與 replay payload size ceiling。
- [artifacts/scripts/guard_status_validator.py](artifacts/scripts/guard_status_validator.py) 目前會直接讀取 task / plan / code / verify 文字 artifact、status JSON、archive fallback 檔案與 GitHub PR provider response，但缺少明確的 byte cap。
- 上一輪 TASK-982 已收斂 GitHub API host allowlist；這一輪只延伸到 resource-boundary hardening，不碰 separation of duties、publish boundary 或 agent dispatch 問題。

## Inputs

- [threat-model-20260417-124620/3-findings.md](threat-model-20260417-124620/3-findings.md)
- [artifacts/scripts/guard_status_validator.py](artifacts/scripts/guard_status_validator.py)
- [artifacts/scripts/test_guard_units.py](artifacts/scripts/test_guard_units.py)
- [artifacts/scripts/run_red_team_suite.py](artifacts/scripts/run_red_team_suite.py)
- [docs/red_team_runbook.md](docs/red_team_runbook.md)
- [README.md](README.md)
- [README.zh-TW.md](README.zh-TW.md)

## Constraints

- size ceilings 必須 fail-closed，但不能低到破壞目前 repo 正常 task artifacts 與既有紅隊案例。
- replay byte cap 必須同時涵蓋 `commit-range` archive fallback 與 `github-pr` provider response，避免只補單一路徑。
- 若修改 guard、runbook 或 README，必須同步 `template/` 對應檔案。
- 本 task 只處理 artifact size ceiling 與 replay byte cap，不處理 publish boundary、override governance 或 agent dispatch hardening。

## Acceptance Criteria

- [ ] AC-1: `guard_status_validator.py` 對高信任 text / JSON artifact 讀取加入明確 byte ceiling，超限時回傳清楚錯誤。
- [ ] AC-2: `commit-range` archive fallback 與 `github-pr` provider response 都有 byte cap，超限時在解析前 fail。
- [ ] AC-3: `test_guard_units.py` 新增或更新測試，覆蓋 oversized artifact、oversized archive fallback 與 oversized provider response。
- [ ] AC-4: red-team suite 新增對應 static cases，至少涵蓋 oversized artifact 與 oversized replay input 邊界，並更新 runbook case matrix。
- [ ] AC-5: root / `template/` 的 guard、tests、runbook、README 與 generated outputs 同步完成。
- [ ] AC-6: 驗證證據至少包含 guard 單元測試、red-team 靜態案例、full red-team report、contract guard 與 TASK-983 status guard。

## Dependencies

- Python 3
- 現有 `TASK-900` sample artifacts、archive fallback 路徑與 GitHub PR provider 模擬器

## Out of Scope

- Publish automation remote verification
- Override / waiver dual-control 設計
- Agent dispatch context minimization
- Red-team runner dynamic import hardening

## Current Status Summary

Planned。這一輪只補 resource-boundary guard：先把 artifact / archive / provider response 的 size ceiling 收斂，再把這些 fail-closed 邊界落成 unit tests、紅隊案例與文件同步。