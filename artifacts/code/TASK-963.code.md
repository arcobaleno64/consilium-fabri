# Code Result: TASK-963

## Metadata
- Task ID: TASK-963
- Artifact Type: code
- Owner: Claude Code
- Status: ready
- Last Updated: 2026-04-17T22:30:00+08:00

## Files Changed

### 新增（root）
- `.github/dependabot.yml` — Dependabot 設定（github-actions + pip ecosystem）
- `.github/workflows/security-scan.yml` — pip-audit CI workflow（pinned actions）
- `artifacts/scripts/github_publish_common.ps1` — 共用 auth/preflight 輔助函式
- `artifacts/scripts/publish-release.ps1` — GitHub Release 建立腳本（含 preflight）

### 修改（root）
- `.github/workflows/workflow-guards.yml` — actions pinned to full SHA
- `artifacts/scripts/push-wiki.ps1` — 重構：加入 preflight（auth probe、wiki 遠端可達性檢查、動態 owner/repo 解析）、移除硬編碼 URL、加入 `-WhatIf` 支援

### 同步（template）
- `template/.github/dependabot.yml`
- `template/.github/workflows/security-scan.yml`
- `template/.github/workflows/workflow-guards.yml` — SHA pin 同步
- `template/artifacts/scripts/github_publish_common.ps1`
- `template/artifacts/scripts/push-wiki.ps1`
- `template/artifacts/scripts/publish-release.ps1`

## Summary Of Changes

1. **P1 — Pin GitHub Actions to SHA**：workflow-guards.yml 的 `actions/checkout@v4` 改為完整 40 字元 SHA `34e114876b0b11c390a56381ad16ebd13914f8d5` (v4.3.1)，`actions/setup-python@v5` 改為 `a26af69be951a213d495a4c3e4e4022e16d87065` (v5.6.0)。新增 `.github/dependabot.yml` 自動追蹤 actions 與 pip 更新。
2. **P2 — pip-audit workflow**：新增 `.github/workflows/security-scan.yml`，於 PR/push/workflow_dispatch 觸發，使用 pinned actions，執行 `pip-audit` 掃描 `requirements.txt`，產出 JSON + columns 格式報告。
3. **P3 — Wiki publish preflight**：新增共用函式庫 `github_publish_common.ps1`（Get-OwnerRepo、Test-GitHubAuth、Test-GhCli、Test-RemoteReachable + 標準化 exit codes）。重構 `push-wiki.ps1` 以使用共用函式、新增 preflight 階段（auth probe → owner/repo 解析 → wiki 目錄檢查 → ls-remote 遠端探測）、支援 `-WhatIf`、移除硬編碼 URL。
4. **P4 — Release publish script**：新增 `publish-release.ps1`（-Tag、-Title、-NotesFile、-Draft、-PreRelease、-WhatIf）、preflight（gh CLI、auth、tag 存在、重複 release 檢查）。

## Mapping To Plan

| Plan 步驟 | 對應實作 |
|-----------|---------|
| P1: Pin GitHub Actions → SHA | workflow-guards.yml pinned + dependabot.yml 建立 |
| P2: pip-audit CI workflow | security-scan.yml 建立 |
| P3: Wiki publish preflight | github_publish_common.ps1 + push-wiki.ps1 重構 |
| P4: Release publish script | publish-release.ps1 建立 |
| Template sync | 全部 6 個檔案同步至 template/ |
