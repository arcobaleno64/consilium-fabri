# Verification: TASK-963

## Metadata
- Task ID: TASK-963
- Artifact Type: verify
- Owner: Claude Code
- Status: pass
- Last Updated: 2026-04-17T22:35:00+08:00

## Verification Summary
Migrated from legacy verify artifact.

## Acceptance Criteria Checklist
- **criterion**: Action supply-chain hardening — full SHA pinning + 後續更新機制
- **method**: Artifact and command evidence review
- **evidence**: `workflow-guards.yml` 已將 `actions/checkout@v4` 改為 `actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4.3.1`，`actions/setup-python@v5` 改為 `actions/setup-python@a26af69be951a213d495a4c3e4e4022e16d87065 # v5.6.0`。新增 `.github/dependabot.yml` 設定 `github-actions` 與 `pip` ecosystem weekly 更新。`security-scan.yml` 同樣使用 SHA pinned actions。
- **result**: verified

- **criterion**: 獨立 dependency / security scan
- **method**: Artifact and command evidence review
- **evidence**: 新增 `.github/workflows/security-scan.yml`，觸發條件：PR、push to master、workflow_dispatch。使用 `pip-audit` 掃描 `requirements.txt`，輸出 JSON + columns 格式。選型理由：pip-audit 為 PyPI 官方支持、無需 GitHub Advanced Security 授權、適用 public repo。
- **result**: verified

- **criterion**: Wiki publish 可重跑腳本，auth / 未初始化 / 無變更明確處置
- **method**: Artifact and command evidence review
- **evidence**: `push-wiki.ps1` 重構為 preflight 架構：(1) `Test-GitHubAuth` 依序檢查 GH_TOKEN → GITHUB_TOKEN → gh auth status，缺失則 exit 10；(2) `Get-OwnerRepo` 動態解析 owner/repo（不再硬編碼）；(3) `Test-RemoteReachable` 透過 `git ls-remote` 探測 wiki 遠端，不可達則 exit 12 + 明確錯誤訊息列出 3 項可能原因；(4) 無變更時 exit 0 + 黃色提示；(5) 支援 `-WhatIf` 僅執行 preflight。
- **result**: verified

- **criterion**: Release publish 可重跑腳本，auth / tag / release 狀態明確處置
- **method**: Artifact and command evidence review
- **evidence**: `publish-release.ps1` preflight 涵蓋：(1) gh CLI 可用性 → exit 11；(2) auth 探測 → exit 10；(3) tag 存在檢查 → exit 14；(4) 既有 release 重複檢查 → exit 14；(5) notes file 存在檢查 → exit 14。支援 `-Tag`、`-Title`、`-NotesFile`、`-Draft`、`-PreRelease`、`-WhatIf` 參數。
- **result**: verified

- **criterion**: 文件清楚列出權限、環境變數、手動步驟
- **method**: Artifact and command evidence review
- **evidence**: `github_publish_common.ps1` 文件明確定義 exit codes（0/10/11/12/13/14/20）與 auth 優先順序（GH_TOKEN → GITHUB_TOKEN → gh CLI）。`push-wiki.ps1` synopsis 與錯誤訊息明確說明 wiki 需先手動建立第一頁。`publish-release.ps1` 錯誤訊息指引先建立 tag。
- **result**: verified

- **criterion**: root 與 template/ 同步
- **method**: Artifact and command evidence review
- **evidence**: 以下 6 個檔案已同步至 template/：dependabot.yml、security-scan.yml、workflow-guards.yml（SHA pin）、github_publish_common.ps1、push-wiki.ps1、publish-release.ps1。`guard_contract_validator.py` PASS，`validate_context_stack.py` PASS。
- **result**: verified

## Overall Maturity
poc

## Deferred Items
- CodeQL / GHAS integration 未實作（需 GitHub Advanced Security 授權，列為 follow-up）
- 腳本未在 live 環境執行過（wiki push 與 release creation）— 僅驗證 preflight 邏輯與結構正確性

## Evidence
- workflow-guards.yml SHA pin：`grep 'uses:' .github/workflows/workflow-guards.yml` 確認 2 行 SHA + comment
- security-scan.yml 存在性與結構：確認 `pip-audit` step 存在
- dependabot.yml 涵蓋 2 個 ecosystem
- push-wiki.ps1：確認 5 個 preflight 階段、3 種 exit code 路徑
- publish-release.ps1：確認 5 個 preflight 階段、4 種 exit code 路徑
- template/ 同步：6 個檔案 1:1 對應

## Evidence Refs
- `github/workflows/workflow-guards.yml`

## Decision Refs
None

## Build Guarantee
無 .csproj 建置。驗證方式：
- `guard_contract_validator.py --root .` → PASS
- `validate_context_stack.py --root .` → PASS
- YAML syntax：workflow-guards.yml 與 security-scan.yml 結構正確（已驗證 on/permissions/jobs/steps 完整性）

## Pass Fail Result
pass

## Recommendation
None
