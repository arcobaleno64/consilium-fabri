# Plan: TASK-963

## Metadata
- Task ID: TASK-963
- Artifact Type: plan
- Owner: Claude
- Status: ready
- Last Updated: 2026-04-16T21:51:20+08:00

## Scope

本計畫分三個實作面向，目標是先把目前最明顯的供應鏈與發布流程風險收斂成可重跑、可驗證、可維護的最低完整面：

1. GitHub Actions action references 改成 full SHA pinning，並加入 Dependabot 來維持後續更新。
2. 新增一條獨立的 dependency / security scan，基線選型為 pip-audit；CodeQL 保留為 repo entitlement 確認後的 follow-up。
3. 將 Wiki / Release 發布流程抽成帶 preflight 的可重跑腳本，統一 auth probe、檢查條件、退出碼與文件說明。

這次 planning 的建議結論如下：

- **Action hardening**：採用「full SHA pinning + Dependabot」而不是二選一。若只能先落地一件，先做 full SHA pinning。
- **Independent scan**：先做 pip-audit，理由是它不依賴 public repo 或 GitHub Code Security entitlement；CodeQL 作為後續強化選項。
- **Wiki bootstrap**：視為 one-time manual prerequisite；腳本必須把它顯式化，而不是假設 clone 一定成功。

## Files Likely Affected

| 檔案 | 操作 |
|---|---|
| `.github/workflows/workflow-guards.yml` | 更新 action pins |
| `.github/workflows/security-scan.yml` | 新增 pip-audit workflow |
| `.github/dependabot.yml` | 新增 Dependabot 設定 |
| `artifacts/scripts/push-wiki.ps1` | 重構為 preflight-aware 可重跑腳本 |
| `artifacts/scripts/publish-release.ps1` | 新增 release publish 腳本 |
| `artifacts/scripts/github_publish_common.ps1` | 新增共用 auth / preflight helper |
| `README.md` | 更新 publish / security automation 說明 |
| `README.zh-TW.md` | 更新 publish / security automation 說明 |
| `template/.github/workflows/workflow-guards.yml` | 同步更新 |
| `template/.github/workflows/security-scan.yml` | 同步新增 |
| `template/.github/dependabot.yml` | 同步新增 |
| `template/artifacts/scripts/push-wiki.ps1` | 同步更新 |
| `template/artifacts/scripts/publish-release.ps1` | 同步新增 |
| `template/artifacts/scripts/github_publish_common.ps1` | 同步新增 |
| `template/README.md` | 同步更新 |
| `template/README.zh-TW.md` | 同步更新 |

## Proposed Changes

### P1: GitHub Actions action hardening

- 將 root 與 template 的 workflow 內所有 external action 改成 full commit SHA pin，並保留同一行 version comment 供 Dependabot 識別，例如 `actions/checkout@<40-char-sha> # v4`。
- 新增 `.github/dependabot.yml`，至少包含 `github-actions` ecosystem；若要順手維護 Python tooling，也可加入 `pip` ecosystem。
- 保持 workflow permissions 最小化，延續目前 `contents: read` / `pull-requests: read` 的策略，避免因 hardening 反而擴權。

### P2: Independent security scan baseline

- 新增獨立 workflow `.github/workflows/security-scan.yml`，觸發建議包含 `pull_request`、`push` 到 `master`、`workflow_dispatch`。
- 以 `actions/checkout` + `actions/setup-python` 為唯一 GitHub Actions 依賴，直接在 job 內 `python -m pip install pip-audit`，避免額外再引入第三方 action。
- 執行 `pip-audit -r requirements.txt --format=json`，並將 JSON 結果作為 artifact 或 log evidence；初始策略預設以 non-zero exit code 阻擋已知漏洞。
- 在 plan 與 README 註記：若日後確認 repo 為 public 或具備 GitHub Code Security，CodeQL 可作為 follow-up workflow，因其能額外涵蓋 Python 與 GitHub Actions workflow 靜態分析。

### P3: Wiki / Release 發布流程腳本化

- 抽出共用 helper（建議 `artifacts/scripts/github_publish_common.ps1`），統一處理：
  - owner / repo 解析
  - `GITHUB_TOKEN` / `GH_TOKEN` / `gh auth` fallback probe
  - `gh` CLI 可用性檢查
  - API / git remote reachable 檢查
  - 可重用的錯誤碼與訊息格式
- 重構 `artifacts/scripts/push-wiki.ps1`：
  - 先做 preflight，不直接一上來 clone。
  - 顯式檢查 wiki source 目錄是否存在、auth 是否可用、wiki remote 是否存在。
  - 若 wiki remote 尚未初始化，輸出明確 remediation：「先在 GitHub Wiki 建立第一頁，再重跑腳本」，並以固定退出碼結束。
  - 若沒有變更，回傳成功且不 push。
  - 保留 idempotent 行為，重跑不應產生額外副作用。
- 新增 `artifacts/scripts/publish-release.ps1`：
  - 支援 `-Tag`, `-Title`, `-NotesFile`, `-Draft`, `-PreRelease`, `-WhatIf` / `-DryRun`。
  - 先做 tag / existing release / auth / permission preflight，再執行 `gh release create` 或 REST API。
  - 對 release 已存在、tag 不存在、權限不足等情境回傳明確錯誤。

### P4: 文件與 template sync

- 更新 root / template README，說明：
  - 為何 action 使用 SHA pinning
  - Dependabot 如何維護 pins
  - security scan 的範圍與限制
  - Wiki / Release 腳本的環境變數、必要權限、一次性 manual bootstrap 條件

## Risks

R1
- Risk: 只做 SHA pinning、沒有同時提供可被 Dependabot 辨識的更新資訊，導致 pins 長期停留在舊 commit，hardening 退化成靜態凍結。
- Trigger: workflow 內改成 full SHA 後，沒有同一行 tag comment 或沒有 `.github/dependabot.yml`。
- Detection: Dependabot 長期沒有針對 workflow refs 開 PR；workflow 內版本註解與 upstream tag 脫鉤。
- Mitigation: 在每個 pinned action 後保留同一行 `# vX` 註解，並把 `github-actions` ecosystem 納入 Dependabot；驗證實作後是否能產生 update PR。
- Severity: blocking

R2
- Risk: 把 CodeQL 當成唯一獨立安全掃描，但實際 repo 類型或授權不支援，造成安全掃描需求落空。
- Trigger: 在未確認 repo visibility / entitlement 的前提下直接採用 CodeQL advanced setup。
- Detection: GitHub UI 無法啟用 CodeQL，或 workflow 執行時回報 feature unavailable / permission-related failure。
- Mitigation: 本輪 baseline 先採 pip-audit；只有在 repo public 或已確認 GH Code Security 可用時，才新增 CodeQL follow-up。
- Severity: blocking

R3
- Risk: wiki remote 尚未初始化時，腳本仍沿用直接 clone 的流程，讓使用者看到模糊的 git 失敗而不知道真正前置條件。
- Trigger: `git ls-remote` / `git clone` 對 `owner/repo.wiki.git` 失敗，且 repo 從未建立第一頁。
- Detection: preflight 無法取得 wiki remote refs，或 clone 回傳 404 / not found；現有終端紀錄已出現 `git ls-remote https://github.com/arcobaleno64/consilium-fabri.wiki.git` exit code 1。
- Mitigation: 將 wiki remote existence 檢查前移到 preflight，並以固定錯誤碼與 remediation message 指向「先在 GitHub Wiki 建立第一頁」。
- Severity: blocking

R4
- Risk: Release / Wiki 腳本各自實作不同的 auth 探測方式，導致本地與 CI 的行為不一致，出現難以重跑的 401 / 403 問題。
- Trigger: 某支腳本只接受 `GITHUB_TOKEN`，另一支腳本只依賴 `gh auth`，或 CI `GITHUB_TOKEN` 權限不足。
- Detection: 同一 repo 在本地可執行、CI 失敗，或相反；`gh auth status`、REST API、`gh release create` 的錯誤訊息彼此不一致。
- Mitigation: 抽共用 helper，統一 auth probe 順序為 `GH_TOKEN` / `GITHUB_TOKEN` → `gh auth`; 文件寫明 release 需要 `contents: write`，wiki push 需要可推送 wiki repo 的認證。
- Severity: blocking

R5
- Risk: pip-audit 初次導入後直接把既有 advisory 視為 hard fail，可能在未先建立 ignore policy 的情況下卡住所有 PR。
- Trigger: `pip-audit -r requirements.txt` 回傳現有 dependency advisory 或 noisy report。
- Detection: security-scan workflow 在導入當下即持續失敗；輸出含可重現的 vulnerability IDs。
- Mitigation: 在導入時保留 JSON 輸出與明確 ignore-list 機制；若首跑有既存漏洞，可先 decision 記錄後再決定是否短暫允許 non-blocking adoption。
- Severity: non-blocking

## Validation Strategy

1. **Action pinning validation**：檢查 root / template workflows 中所有 `uses:` 都改為 40-char SHA，並保留可供 Dependabot 識別的版本註解。
2. **Dependabot validation**：用 schema 檢查 `.github/dependabot.yml` 是否涵蓋 `github-actions` ecosystem，必要時補 `pip`。
3. **Security scan validation**：在本地或 CI 執行新 workflow 的核心命令，確認 `pip-audit` 能對 `requirements.txt` 產生可解析輸出，並驗證 exit code 行為。
4. **Wiki script validation**：至少覆蓋四條路徑：auth 缺失、wiki remote 未初始化、無變更、正常 dry-run/preflight pass。
5. **Release script validation**：至少覆蓋四條路徑：auth 缺失、tag 不存在、release 已存在、draft / dry-run success。
6. **Template sync validation**：比對 root 與 `template/` 的 workflow / scripts / README 同步一致。
7. **Workflow guard validation**：實作完成後，執行 `python artifacts/scripts/guard_contract_validator.py --root .` 與對應 task 的 status guard。

## Out of Scope

- 在本輪直接啟用 GitHub UI / org settings 裡的 CODEOWNERS、Actions policy 或 immutable releases
- 實作跨 repo 的發佈 orchestrator
- 把 wiki bootstrap 完全自動化成 GitHub 官方未保證的隱含行為
- 對 `external/hermes-agent/` 套用同一套 workflow hardening

## Ready For Coding

yes