# Plan: TASK-980

## Metadata
- Task ID: TASK-980
- Artifact Type: plan
- Owner: Claude
- Status: ready
- Last Updated: 2026-04-17T21:18:00+08:00

## Scope

本次計畫分成三條主線，但都只服務同一個目標：替 root repo 的控制面建立可追溯的安全基線，而不是做泛用掃描堆疊。

1. 依 threat-model-analyst 的輸出格式，為 root repo 建立正式威脅模型報告，明確標示元件、資料流、trust boundaries、STRIDE-A threats 與 prioritized findings。
2. 在 repo 內新增一支 focused security scanner，包含 `secrets` 與 `static` 兩種掃描模式，直接檢查 root / template 內最重要的工作流與腳本檔案。
3. 擴充 root / template 的 `security-scan.yml`、測試與 README，讓新增掃描成為既有安全檢查的一部分。

Threat model 的焦點限定為 root repo 的 control plane：artifact markdown/json、agent dispatch、validator、publish automation、local git worktree 與 GitHub API 整合，不延伸到 generic web app threat catalog 或 `external/` 內第三方專案。

## Files Likely Affected

| 檔案 | 操作 |
|---|---|
| `artifacts/tasks/TASK-980.task.md` | 新增 task artifact |
| `artifacts/plans/TASK-980.plan.md` | 新增 plan artifact |
| `artifacts/code/TASK-980.code.md` | 新增 code artifact |
| `artifacts/verify/TASK-980.verify.md` | 新增 verify artifact |
| `artifacts/status/TASK-980.status.json` | 新增 status artifact |
| `threat-model-20260417-124620/0-assessment.md` | 新增 threat model assessment |
| `threat-model-20260417-124620/0.1-architecture.md` | 新增 architecture overview |
| `threat-model-20260417-124620/1-threatmodel.md` | 新增 DFD report |
| `threat-model-20260417-124620/1.1-threatmodel.mmd` | 新增 DFD source |
| `threat-model-20260417-124620/2-stride-analysis.md` | 新增 STRIDE-A analysis |
| `threat-model-20260417-124620/3-findings.md` | 新增 prioritized findings |
| `threat-model-20260417-124620/threat-inventory.json` | 新增 threat inventory |
| `.github/workflows/security-scan.yml` | 擴充 secrets / static scan jobs |
| `artifacts/scripts/repo_security_scan.py` | 新增 repo-local security scanner |
| `artifacts/scripts/test_security_scans.py` | 新增 unit tests |
| `.github/workflows/workflow-guards.yml` | 納入新增測試檔 |
| `README.md` | 更新 security automation 說明 |
| `README.zh-TW.md` | 更新 security automation 說明 |
| `template/.github/workflows/security-scan.yml` | 同步擴充 |
| `template/.github/workflows/workflow-guards.yml` | 同步測試命令 |
| `template/artifacts/scripts/repo_security_scan.py` | 同步新增 |
| `template/artifacts/scripts/test_security_scans.py` | 同步新增 |
| `template/README.md` | 同步更新 |
| `template/README.zh-TW.md` | 同步更新 |

## Proposed Changes

### P1: Root repo threat model package

- 建立 `threat-model-20260417-124620/` 目錄，輸出 root repo 專屬 threat model 報告。
- 元件至少涵蓋：Human Maintainer、Workflow Controller、Agent Dispatch、Guard Validators、Red Team Runner、Publish Automation、Artifact Store、Git Worktree、GitHub Platform。
- STRIDE-A 分析以 artifact injection、path traversal / symlink escape、GitHub API SSRF、token exposure、dynamic execution、guard exception abuse、resource exhaustion 為主軸。
- Findings 需明確區分已存在控制與仍開放風險，並把本次新增的 secrets / static scans 納入 remediation 路線圖。

### P2: Repo-local secrets and focused static scanner

- 新增 `artifacts/scripts/repo_security_scan.py`，提供 `secrets` 與 `static` 子命令。
- `secrets` 模式：掃描高信心 secret patterns，例如 GitHub PAT、fine-grained PAT、AWS access key、private key block、OpenAI-style key 與高風險 generic credential assignment，並用 placeholder / low-entropy heuristics 避免把示例字串誤判成真實洩漏。
- `static` 模式：聚焦掃描 root / template 的 workflow、Python、PowerShell 腳本，規則至少包含 unpinned actions、`persist-credentials: true`、`pull_request_target`、`shell=True`、`exec(`、`eval(`、`Invoke-Expression`、顯式 secret logging。
- 掃描輸出要同時適合 CLI 與 GitHub Actions log 閱讀；若有 findings，exit code 應 fail。

### P3: CI integration and tests

- 擴充 root / template 的 `.github/workflows/security-scan.yml`，在既有 `pip-audit` 之外新增 `repo-secrets-scan` 與 `repo-static-scan` jobs。
- 保持 `permissions: contents: read` 與 `persist-credentials: false`，不新增 write 權限。
- 在 root / template 的 `workflow-guards.yml` 把新增測試檔一起納入 pytest 命令。
- 新增 `artifacts/scripts/test_security_scans.py`，覆蓋 placeholder filtering、secret finding detection、workflow pin detection、Python / PowerShell rule detection等主要分支。

### P4: Documentation and template sync

- 更新 root / template README，補上 threat model 產出位置、`security-scan.yml` 現在包含哪些 jobs、以及 repo-local scanner 的設計邊界。
- 說明 focused static scan 的定位是 regression guard，不是取代完整安全審查。

## Risks

R1
- Risk: threat model 範圍漂移到 `external/` 或 generic web app catalog，導致 findings 與實際 root repo 風險失焦。
- Trigger: architecture / STRIDE 直接引用 `external/hermes-agent/` 元件，或大量列出與 root repo 無關的 SQL injection / XSS findings。
- Detection: threat model 報告中的 component / finding 無法回指 root repo 內真實檔案與資料流。
- Mitigation: 所有元件、資料流與 finding 都必須錨定到 root repo 實際檔案；`external/` 明列為 out of scope。
- Severity: blocking

R2
- Risk: 新增的 secrets / static 規則過寬，導致目前 root 或 template 內大量誤報，security-scan 無法穩定綠燈。
- Trigger: 掃描把示例 token、文件 placeholder 或既有安全參考文字判成真實弱點。
- Detection: 本地測試或 CI 首跑即大量失敗，且 findings 主要落在假資料或文檔範例。
- Mitigation: 採高信心 pattern + placeholder/entropy 過濾；規則只鎖定明顯高風險 foot-guns。
- Severity: blocking

R3
- Risk: root / template workflow 與腳本同步不完整，contract guard 或後續使用者 bootstrap 失敗。
- Trigger: 只更新 root，漏掉 template 的 workflow、script 或 README。
- Detection: `guard_contract_validator.py` 回報 root/template drift，或 template 缺少新 scanner 腳本。
- Mitigation: 在 plan 中先把 root 與 template 對應檔列為同一批變更，驗證時固定跑 contract guard。
- Severity: blocking

R4
- Risk: secret placeholder 過濾太鬆，讓真實低熵或短格式 token 漏檢，造成 secrets scan 名存實亡。
- Trigger: 只依賴簡單字串黑名單，沒有同時考慮 key 前綴與結構。
- Detection: 測試中加入代表性 secret samples 時無法被抓到；規則只對極少數 pattern 生效。
- Mitigation: 混合使用結構型 regex、關鍵前綴與 placeholder 排除，不只依賴 entropy。
- Severity: non-blocking

## Validation Strategy

1. 執行 `python -m pytest artifacts/scripts/test_guard_units.py artifacts/scripts/test_security_scans.py -v`，確認新增掃描腳本與既有 guard 測試都通過。
2. 執行 `python artifacts/scripts/repo_security_scan.py --root . secrets`，確認目前 root repo 與 template 沒有被新規則誤判。
3. 執行 `python artifacts/scripts/repo_security_scan.py --root . static`，確認目前 workflow / scripts 通過 focused static rules。
4. 執行 `python artifacts/scripts/guard_contract_validator.py --root .`，確認 root / template 同步完整。
5. 執行 `python artifacts/scripts/guard_status_validator.py --task-id TASK-980`，確認 task artifacts 與 scope 符合 guard。
6. 需要時用 Mermaid renderer 驗證 DFD 語法可渲染。

## Out of Scope

- 直接修補所有 threat model findings 所指出的根因
- 引入新的第三方 scanning action 或 SaaS 平台
- 擴充 `workflow-guards.yml` 以外的 GitHub organizational policy
- 對 release / wiki publish 功能做需求外更動

## Ready For Coding

yes