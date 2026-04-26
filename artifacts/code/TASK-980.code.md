# Code Result: TASK-980

## Metadata
- Task ID: TASK-980
- Artifact Type: code
- Owner: Claude Code
- Status: ready
- Last Updated: 2026-04-17T21:18:00+08:00
- PDCA Stage: D

## Files Changed

- `artifacts/tasks/TASK-980.task.md`
- `artifacts/plans/TASK-980.plan.md`
- `artifacts/code/TASK-980.code.md`
- `artifacts/verify/TASK-980.verify.md`
- `artifacts/status/TASK-980.status.json`
- `threat-model-20260417-124620/0-assessment.md`
- `threat-model-20260417-124620/0.1-architecture.md`
- `threat-model-20260417-124620/1-threatmodel.md`
- `threat-model-20260417-124620/1.1-threatmodel.mmd`
- `threat-model-20260417-124620/2-stride-analysis.md`
- `threat-model-20260417-124620/3-findings.md`
- `threat-model-20260417-124620/threat-inventory.json`
- `.github/workflows/security-scan.yml`
- `.github/workflows/workflow-guards.yml`
- `artifacts/scripts/repo_security_scan.py`
- `artifacts/scripts/test_security_scans.py`
- `README.md`
- `README.zh-TW.md`
- `template/.github/workflows/security-scan.yml`
- `template/.github/workflows/workflow-guards.yml`
- `template/artifacts/scripts/repo_security_scan.py`
- `template/artifacts/scripts/test_security_scans.py`
- `template/README.md`
- `template/README.zh-TW.md`

## Summary Of Changes

- 建立 `threat-model-20260417-124620/` timestamped threat model package，聚焦 root repo control plane 的 trust boundaries、data flows、STRIDE-A threats 與 prioritized findings。
- 新增 repo-local security scanner `artifacts/scripts/repo_security_scan.py`，提供 `secrets` 與 `static` 子命令，涵蓋高信心 secret patterns、placeholder 過濾，以及 workflow / Python / PowerShell 的高風險 regression rules。
- 擴充 root / `template/` 的 `.github/workflows/security-scan.yml` 與 `.github/workflows/workflow-guards.yml`，把新增 secrets/static 掃描與測試納入既有 CI/guard 鏈。
- 新增 scanner 單元測試，並調整 CLI 指令文件與 workflow 參數順序，避免 `--root` 放在 subcommand 後方時造成誤用。
- 修正自我觸發誤報：測試樣本改為執行時組出 secret / `shell=True` 字串，`verify=False` 規則改為 word-boundary 比對，讓 repo 自掃保持綠燈。

## Mapping To Plan

- plan_item: 1.1, status: done, evidence: "Created threat-model-20260417-124620/ with assessment, architecture, DFD, STRIDE analysis, findings, and JSON inventory."
- plan_item: 2.1, status: done, evidence: "Implemented repo_security_scan.py with secrets/static modes, focused rules, placeholder heuristics, and readable CLI output."
- plan_item: 3.1, status: done, evidence: "Expanded security-scan/workflow-guards in root and template; added test_security_scans.py coverage and kept least-privilege workflow settings."
- plan_item: 4.1, status: done, evidence: "Updated README root/template security documentation and corrected command examples to the validated CLI syntax."

## Tests Added Or Updated

- 新增 `artifacts/scripts/test_security_scans.py`，覆蓋 secret placeholder、PAT detection、generic secret assignment、unpinned actions、Python `shell=True` 與 PowerShell `Invoke-Expression`。
- 新增 `template/artifacts/scripts/test_security_scans.py`，保持 template bootstrap 後可直接驗證同一批規則。
- 更新 root / `template/` 的 `.github/workflows/workflow-guards.yml`，將新增測試檔納入 pytest 命令。

## Known Risks

- threat model 中仍有未在本 task 內直接修補的殘餘風險，例如 artifact markdown 信任邊界、subprocess / publish automation 的更細粒度 hardening；這些已記錄在 `threat-model-20260417-124620/3-findings.md`。
- focused static scan 刻意維持窄範圍高訊號，屬於 regression guard，不等同完整 SAST 或 secrets platform 掃描。


## TAO Trace

Reconstructed from artifact history. This task predates the TAO schema (introduced in TASK-1000 Phase 2).

### Step 1
- Thought Log: (Reconstructed) Reviewed plan Proposed Changes and executed accordingly.
- Action Step: Implemented changes per plan scope.
- Observation: Completed (inferred from verify artifact AC checklist).
- Next-Step Decision: continue

## Blockers

None