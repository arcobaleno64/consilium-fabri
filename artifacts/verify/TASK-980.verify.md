# Verification: TASK-980

## Metadata
- Task ID: TASK-980
- Artifact Type: verify
- Owner: Claude Code
- Status: pass
- Last Updated: 2026-04-17T21:18:00+08:00

## Acceptance Criteria Checklist

### AC-1: root repo threat model package complete
- **Result**: PASS
- **Evidence**: 新增 `threat-model-20260417-124620/`，包含 `0-assessment.md`、`0.1-architecture.md`、`1-threatmodel.md`、`1.1-threatmodel.mmd`、`2-stride-analysis.md`、`3-findings.md` 與 `threat-inventory.json`。內容聚焦 root repo control plane，不混入 `external/` 專案。

### AC-2: security-scan workflow expanded with least-privilege scans
- **Result**: PASS
- **Evidence**: root / `template/` 的 `.github/workflows/security-scan.yml` 現在同時執行 `pip-audit`、`python artifacts/scripts/repo_security_scan.py --root . secrets` 與 `python artifacts/scripts/repo_security_scan.py --root . static`。workflow 保持 `contents: read` 權限，checkout 仍採 `persist-credentials: false`。

### AC-3: secrets scan catches high-confidence patterns without placeholder noise
- **Result**: PASS
- **Evidence**: `repo_security_scan.py` 的 `secrets` 模式同時檢查 GitHub PAT、fine-grained PAT、private key block、AWS access key、OpenAI-style key 與高風險 generic credential assignment，並以 placeholder / entropy heuristics 過濾示例值。`test_security_scans.py` 覆蓋 PAT、generic secret 與 placeholder 排除。實際執行 `--root . secrets` 結果為 `[OK] No findings detected`。

### AC-4: focused static rules cover requested control-plane foot-guns
- **Result**: PASS
- **Evidence**: `static` 模式覆蓋 workflow unpinned actions、`persist-credentials: true`、`pull_request_target`、`permissions: write-all`、Python `shell=True` / `exec(` / `eval(` / `verify=False`、PowerShell `Invoke-Expression` / `iex` 與明顯 secret logging。`test_security_scans.py` 已驗證 workflow / Python / PowerShell 規則；實際執行 `--root . static` 結果為 `[OK] No findings detected`。

### AC-5: root and template remain synchronized
- **Result**: PASS
- **Evidence**: 以下檔案已做 root / template 同步：`security-scan.yml`、`workflow-guards.yml`、`repo_security_scan.py`、`test_security_scans.py`、`README.md`、`README.zh-TW.md`。`guard_contract_validator.py --root .` 回報 `[OK] Contract validation passed`。

### AC-6: validation evidence includes unit tests, contract guard, and status guard
- **Result**: PASS
- **Evidence**: `python -m pytest artifacts/scripts/test_guard_units.py artifacts/scripts/test_security_scans.py -v` 結果為 `919 passed in 8.01s`。`guard_contract_validator.py --root .` 與 `guard_status_validator.py --task-id TASK-980` 皆回報 `[OK]`。

## Build Guarantee

驗證命令與結果：

- `python -m pytest artifacts/scripts/test_guard_units.py artifacts/scripts/test_security_scans.py -v` → `919 passed in 8.01s`
- `python artifacts/scripts/repo_security_scan.py --root . secrets` → `[OK] No findings detected`
- `python artifacts/scripts/repo_security_scan.py --root . static` → `[OK] No findings detected`
- `python artifacts/scripts/guard_contract_validator.py --root .` → `[OK] Contract validation passed`
- `python artifacts/scripts/guard_status_validator.py --task-id TASK-980` → `[OK] Validation passed`

## Evidence

- scanner 規則與測試已在 root / `template/` 同步存在，可在 bootstrap repo 內直接重放同一組驗證。
- CLI 參數順序已修正為 `python artifacts/scripts/repo_security_scan.py --root . <subcommand>`，workflow 與 README 範例一致。
- 自掃誤報已消除，代表新增掃描可在目前 repo 狀態下穩定作為 regression guard。

## Remaining Gaps

- 本次只建立 threat model 與兩條高訊號 regression scans，尚未逐項修補 `3-findings.md` 中列出的所有設計風險。
- 未引入 CodeQL、GHAS 或更重型的 org-level secret scanning；這仍屬後續策略選擇，而非本 task 範圍。

## Pass Fail Result

pass