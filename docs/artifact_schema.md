# ARTIFACT_SCHEMA

本文件定義 artifact-first workflow 的檔案命名、欄位、狀態、驗證規則與最小品質要求。

目標有三個：

1. 讓不同代理可透過固定 schema 接手工作。
2. 讓狀態可追蹤、可驗證、可重跑。
3. 避免 artifact 退化成不可機讀、不可審計的自由散文。

## 1. 通用規則

### 1.1 命名規範

所有 artifacts 必須使用一致命名：

`TASK-<流水號>.<artifact-type>.<ext>`

範例：

- `TASK-001.task.md`
- `TASK-001.research.md`
- `TASK-001.plan.md`
- `TASK-001.code.md`
- `TASK-001.test.md`
- `TASK-001.verify.md`
- `TASK-001.decision.md`
- `TASK-001.status.json`

### 1.2 目錄規範

建議目錄：

```text
/artifacts
  /tasks
  /research
  /plans
  /code
  /test
  /verify
  /decisions
  /improvement
  /status
```

### 1.3 任務識別碼

- 任務識別碼格式：`TASK-001`、`TASK-002`。
- 一個任務可有多個關聯 artifacts，但只能有一個主 status artifact。
- 同一任務的 artifacts 必須使用相同 task id。

### 1.4 時間格式

- 所有時間使用 ISO 8601。
- 所有 workflow / template / root 長期維護 artifacts 的時間戳必須使用 `Asia/Taipei`，並帶 `+08:00`。
- 不接受只有日期或缺少時區的 `Last Updated`。
- 範例：`2026-04-09T14:30:00+08:00`

### 1.5 文件語言與風格

- artifact 以清晰、可驗證、可接手為原則。
- 用語必須具體，避免模糊詞如「可能沒問題」「應該可行」。
- 若不確定，必須明確標示 `uncertain` 或對應欄位中的未確認事項。

## 2. Artifact 類型總表

| 類型 | 副檔名 | 主要作者 | 目的 |
|---|---|---|---|
| task | `.task.md` | Claude | 定義任務目標、限制、驗收條件 |
| research | `.research.md` | Gemini | 提供規格依據、查詢結果、實作約束 |
| plan | `.plan.md` | Claude | 定義實作範圍、影響面、風險 |
| code | `.code.md` | Codex | 記錄修改內容、變更檔案、已做測試 |
| test | `.test.md` | Codex subagent 或 Claude | 記錄測試結果與失敗摘要 |
| verify | `.verify.md` | Claude 或 verifier | 對照驗收條件判定 pass/fail |
| decision | `.decision.md` | Claude | 記錄衝突、決策理由、取捨 |
| status | `.status.json` | Claude | 提供機讀狀態與下一步 |
| improvement | `.improvement.md` | Claude | PDCA 改進記錄：失敗分析、矯正與預防措施 |

## 3. 必填通用欄位

所有 markdown 型 artifact 必須至少包含以下通用區段：

- `Task ID`
- `Artifact Type`
- `Owner`
- `Status`
- `Last Updated`

建議固定寫法：

```md
## Metadata
- Task ID: TASK-001
- Artifact Type: task
- Owner: Claude
- Status: drafted
- Last Updated: 2026-04-09T14:30:00+08:00
```

若缺少上述欄位，該 artifact 視為不合法。

## 4. 狀態值規範

### 4.1 通用狀態值

不同 artifact 可使用以下狀態值的子集合：

- `drafted`
- `in_progress`
- `ready`
- `approved`
- `blocked`
- `pass`
- `fail`
- `done`
- `superseded`

### 4.2 狀態使用原則

- task: `drafted`, `approved`, `blocked`, `done`
- research: `in_progress`, `ready`, `blocked`, `superseded`
- plan: `drafted`, `ready`, `approved`, `blocked`, `superseded`
- code: `in_progress`, `ready`, `blocked`, `superseded`
- test: `in_progress`, `pass`, `fail`, `blocked`, `superseded`
- verify: `pass`, `fail`, `blocked`, `superseded`
- decision: `done`
- improvement: `draft`, `approved`, `applied`

## 5. 各 artifact schema

---

## 5.1 Task Artifact Schema

檔名：`artifacts/tasks/TASK-001.task.md`

用途：任務的單一權威定義。

必填區段：

```md
# Task: TASK-001

## Metadata
- Task ID:
- Artifact Type: task
- Owner:
- Status:
- Last Updated:

## Objective

## Background

## Inputs

## Constraints

## Acceptance Criteria

## Dependencies

## Out of Scope

## Current Status Summary
```

欄位規則：

- `Objective`: 一句到數句，清楚描述任務最終目標。
- `Inputs`: 指出可用檔案、模組、文件或使用者需求。
- `Constraints`: 必須明確列出不可違反條件。
- `Acceptance Criteria`: 必須條列且可驗證。
- `Out of Scope`: 避免 Codex 擴大實作範圍。

最低驗收標準：

- 驗收條件不可空白。
- 至少一條 `Out of Scope` 或明確寫 `None`。
- `Constraints` 不可省略。

---

## 5.2 Research Artifact Schema

檔名：`artifacts/research/TASK-001.research.md`

用途：將外部知識、規格、版本差異與實作約束落地。

必填區段：

```md
# Research: TASK-001

## Metadata
- Task ID:
- Artifact Type: research
- Owner:
- Status:
- Last Updated:

## Research Questions

## Confirmed Facts

## Relevant References

## Sources

## Uncertain Items

## Constraints For Implementation
```

欄位規則：

- `Research Questions`: 至少一條。
- `Confirmed Facts`: 必須是可採用於規劃或實作的事實。
- `Relevant References`: 需標明來源名稱或文件名稱。
- `Sources`: 每行格式必須為 `[N] Author/Org. "Title." URL (YYYY-MM-DD retrieved)`。
- `Sources`: 至少 2 筆。
- `Sources` failure_grade:
  - `CRITICAL`: 缺少 `## Sources` 區段，或 0 筆來源。
  - `MAJOR`: 格式違規（例如缺少 URL、整體格式不符）。
  - `MINOR`: 日期缺失或只提供 partial date。
- `Uncertain Items`: 沒有時要寫 `None`。
- `Constraints For Implementation`: 要可直接被 plan 使用。
- research artifact 是 fact-only 契約，不得包含 `Recommendation`、implementation approach、PR title/body，或任何 solution 設計建議。

最低驗收標準：

- 不可只有連結或文件名，必須有整理後結論。
- 不可把推測寫進 `Confirmed Facts`。
- `Confirmed Facts` 的每一條 claim 都必須在同一條目內附上 inline citation（URL、`gh api` 指令或 artifact / doc path）。
- `Uncertain Items` 若非 `None`，每條都必須以 `UNVERIFIED:` 開頭並說明原因。
- 至少要有一個可供 implementation 使用的約束。

---

## 5.3 Plan Artifact Schema

檔名：`artifacts/plans/TASK-001.plan.md`

用途：將需求與研究轉成可控實作範圍。

必填區段：

```md
# Plan: TASK-001

## Metadata
- Task ID:
- Artifact Type: plan
- Owner:
- Status:
- Last Updated:

## Scope

## Files Likely Affected

## Proposed Changes

## Risks

## Validation Strategy

## Out of Scope

## Ready For Coding
```

欄位規則：

- `Scope`: 明確描述此次計畫包含哪些內容。
- `Files Likely Affected`: 至少列出模組、目錄或檔案群。若 task 專屬 artifact 仍位於 dirty git worktree 中，`guard_status_validator.py` 也會用實際 git changed files 自動比對這個欄位。
- `Proposed Changes`: 條列具體改動。
- `Risks`: 不可省略。必須執行 premortem 分析（見 `docs/premortem_rules.md`）。每條風險必須包含 R 編號 + Risk / Trigger / Detection / Mitigation / Severity 五欄位。Severity 只能填 `blocking` 或 `non-blocking`。一般任務至少 2 條風險；安全性 / 依賴升級 / upstream PR 至少 4 條且至少 1 條 blocking。品質規則見 `docs/premortem_rules.md` §4。`guard_status_validator.py` 在 `planned → coding` 時會自動檢查。
- `Validation Strategy`: 必須說明如何驗證成功。
- `Ready For Coding`: 只能填 `yes` 或 `no`。

最低驗收標準：

- 未列影響範圍的 plan 不可進 coding。
- `Ready For Coding` 為 `yes` 前，必須已有對應 task artifact。
- 若 task 需要 research，則 plan 建立前必須已有 research artifact。

---

## 5.4 Code Artifact Schema

檔名：`artifacts/code/TASK-001.code.md`

用途：記錄實作結果，避免主 thread 被 diff 與 log 淹沒。

必填區段：

```md
# Code Result: TASK-001

## Metadata
- Task ID:
- Artifact Type: code
- Owner:
- Status:
- Last Updated:

## Files Changed

## Summary Of Changes

## Mapping To Plan

## Tests Added Or Updated

## Known Risks

## Blockers
```

可選區段（若需支援 historical diff reconstruction）：

```md
## Diff Evidence
- Evidence Type: commit-range
- Base Ref:
- Head Ref:
- Base Commit:
- Head Commit:
- Diff Command:
- Changed Files Snapshot:
- Snapshot SHA256:
- Archive Path:
- Archive SHA256:

## Diff Evidence
- Evidence Type: github-pr
- Repository:
- PR Number:
- API Base URL:
- Changed Files Snapshot:
- Snapshot SHA256:
```

欄位規則：

- `Files Changed`: 至少列出實際修改檔案，沒有修改時不可建立 code artifact。若 task 專屬 artifact 仍位於 dirty git worktree 中，`guard_status_validator.py` 會用實際 git changed files 自動驗證這個欄位；若為 clean task 且存在合法 diff evidence，也會在 historical replay 中驗證這個欄位。
- `Mapping To Plan`: 每行格式必須為 `- plan_item: {N.N}, status: done|partial|skipped, evidence: "{short description}"`。
- `Mapping To Plan`: 每個 plan item 都必須有對應一行；若無計畫對應則必須寫 `status: skipped, evidence: "not required by plan"`。
- `Tests Added Or Updated`: 沒有時寫 `None`。
- `Known Risks`: 沒有時寫 `None`。
- `Blockers`: 沒有時寫 `None`。
- `Diff Evidence`: 沒有時可省略或寫 `None`。目前 `guard_status_validator.py` 支援 `Evidence Type: commit-range` 與 `Evidence Type: github-pr`。
- `commit-range`: 要求 immutable commit pinning：`Base Commit` 與 `Head Commit` 必須是完整 40 字元 git commit SHA；`Base Ref` 與 `Head Ref` 是可選便利欄位，只用於偵測 ref drift。`Diff Command` 應對應實際 replay 命令。若擔心長期 git objects retention 不足，可額外提供 `Archive Path` 與 `Archive SHA256`；兩者必須一起出現，`Archive Path` 必須是 repo-relative、UTF-8、每行一個 normalized relative path、排序後、LF 換行的 text file，`Archive SHA256` 則是該 archive file 原始 bytes 的 SHA-256。guard 只會在 local git replay 失敗時改用 archive fallback，且 archive 內容仍必須與 `Changed Files Snapshot` 完全一致。
- `github-pr`: `Repository` 必須是 `owner/repo`，`PR Number` 必須是正整數；`API Base URL` 可省略，省略時預設 `https://api.github.com`，若使用 GitHub Enterprise Server 或本地 fixture，可覆寫成其他 http(s) endpoint。guard 會透過 GitHub PR files API 逐頁抓取 changed files，public repo 可不帶 token；private repo 或 rate-limited 環境則應提供 `GITHUB_TOKEN` 或 `GH_TOKEN`。
- `Changed Files Snapshot`: 必須列出 replayed diff 或 provider response 的完整檔案清單（以逗號分隔）。
- `Snapshot SHA256`: 必須是 `Changed Files Snapshot` 排序後以換行串接所得內容的 SHA-256。

最低驗收標準：

- 不能只寫「已完成修改」。
- 必須能看出改了哪裡、為何而改。
- 若超出 plan，必須明確標示並阻止 closure；在 task 專屬 dirty worktree 中，status guard 會直接用 git changed files 攔截未宣告 drift；在 clean task 且存在合法 diff evidence 時，status guard 會先驗證 `Changed Files Snapshot` 與 `Snapshot SHA256`，再用 pinned `commit-range`、archive fallback 或 `github-pr` provider response 重建 changed files 後攔截未宣告 drift。`--allow-scope-drift` 只可降級真正的 scope drift，不能覆蓋 diff evidence 損毀、archive 損毀或 provider evidence 錯誤。

---

## 5.5 Test Artifact Schema

檔名：`artifacts/test/TASK-001.test.md`

用途：承接測試與驗證輸出，不把原始 log 丟進主 thread。

必填區段：

```md
# Test Report: TASK-001

## Metadata
- Task ID:
- Artifact Type: test
- Owner:
- Status:
- Last Updated:

## Test Scope

## Commands Executed

## Result Summary

## Failures

## Evidence Files

## Recommendation
```

欄位規則：

- `Commands Executed`: 至少列出實際命令或測試類型。
- `Result Summary`: 必須有總結，不可只貼 log。
- `Failures`: 沒有時寫 `None`。
- `Evidence Files`: 若完整 log 落地到其他檔案，需在此列出。

最低驗收標準：

- 不可只貼 raw output。
- 必須明確指出是 pass、fail 或 blocked。

---

## 5.6 Verify Artifact Schema

檔名：`artifacts/verify/TASK-001.verify.md`

用途：對照 acceptance criteria 做最終驗收。

必填區段：

```md
# Verification: TASK-001

## Metadata
- Task ID:
- Artifact Type: verify
- Owner:
- Status:
- Last Updated:

## Acceptance Criteria Checklist

## Evidence

## Build Guarantee

## Pass Fail Result

## Remaining Gaps

## Recommendation
```

欄位規則：

- `Acceptance Criteria Checklist`: 必須逐條對照 task artifact。
- `Acceptance Criteria Checklist` item schema: `required_fields: [criterion, method, evidence, result, reviewer, timestamp]`
- `Acceptance Criteria Checklist` item schema: `timestamp` 必須為 `Asia/Taipei` 的 ISO 8601 並帶 `+08:00`。
- `Evidence`: 指向 code/test/research/decision artifacts。
- `Build Guarantee` (FUP-2)：針對本 task 修改過的**每一個** build 單元，明列 build 指令、exit code、與 output tail。
  - .NET 任務：對每個被修改的 `.csproj` 執行 `dotnet build <csproj> -c Debug` 並貼出結尾段落（含「建置成功/錯誤」或等價 summary）。
  - 非 .NET 任務（python / node / etc.）：列對應 build / type-check / lint 指令與結果。
  - 若本 task 未修改任何 `.csproj` 或等價 build 單元，寫 `None (no .csproj modified)` 並簡述原因（例如純文件變更、python-only 任務）。
  - **禁止**以「測試專案 build 成功」替代「被測專案 build 成功」—— 兩者不等價。若發生此類事故，應建立 decision artifact 記錄根因與修正。
- `Pass Fail Result`: 只能填 `pass` 或 `fail`。
- `Remaining Gaps`: 沒有時寫 `None`。

最低驗收標準：

- 未逐條對照 acceptance criteria 的 verify artifact 不合法。
- 若有未完成條件，不可標 `pass`。
- 缺少 `## Build Guarantee` 區段的 verify artifact 不合法；`guard_status_validator.py` 會在 `required_markers["verify"]` 擋下。

---

## 5.7 Decision Artifact Schema

檔名：`artifacts/decisions/TASK-001.decision.md`

用途：處理衝突、取捨、補查決策與流程分歧。

必填區段：

```md
# Decision Log: TASK-001

## Metadata
- Task ID:
- Artifact Type: decision
- Owner:
- Status: done
- Last Updated:

## Issue

## Options Considered

## Chosen Option

## Reasoning

## Implications

## Follow Up
```

若 decision 用於 guard waiver，需額外提供：

```md
## Guard Exception
- Exception Type:
- Scope Files:
- Justification:
- Override_Reason:
```

何時必須建立 decision artifact：

- 研究結果互相衝突
- 計畫需做取捨
- Codex 提出超出原計畫的必要修改
- 驗收未通過，需決定回退或補改
- 對話內容與 artifact 衝突
- 使用 `--allow-scope-drift` 將 drift 降級為 warning

`## Guard Exception` 規則：

- `Exception Type: allow-scope-drift` 代表此 decision 是 scope drift 的顯式豁免。
- `Scope Files`: 必須明列此次豁免涵蓋的 drift files，使用逗號分隔；不可只寫 `all` 或留白。
- `Justification`: 必須說明為何這次 drift 可以被受控接受。若 `guard_status_validator.py` 在 `--allow-scope-drift` 模式下找不到對應 waiver，仍會 fail。
- `Override_Reason`: 當使用 `guard_status_validator.py --override ... --override-approver ...` 時，decision artifact 應同步記錄人工核准的 override 理由；此欄位不得只寫 `test` 或空泛字眼，必須能對應 override log 中的 `reason`。

---

## 5.8 Status Artifact Schema

檔名：`artifacts/status/TASK-001.status.json`

用途：提供機器可讀狀態，作為流程主控依據。

JSON schema 範例：

```json
{
  "task_id": "TASK-001",
  "state": "planned",
  "current_owner": "Claude",
  "next_agent": "Codex",
  "required_artifacts": ["task", "research", "plan"],
  "available_artifacts": ["task", "research", "plan"],
  "missing_artifacts": [],
  "blocked_reason": "",
  "last_updated": "2026-04-09T14:30:00+08:00"
}
```

### state 合法值

- `drafted`
- `researched`
- `planned`
- `coding`
- `testing`
- `verifying`
- `done`
- `blocked`

### 欄位規則

- `task_id`: 必須對應既有 task artifact。
- `state`: 必須符合 workflow state machine。
- `required_artifacts`: 此狀態進入下一步所需類型。
- `missing_artifacts`: 實際缺件清單。
- `blocked_reason`: 若 state 為 `blocked`，不可空白。
- `Gate_E_passed` (新增)：Gate E 驗證是否通過。只有 state 為 `done` 且曾經歷 blocked 時才填寫。值為 `true` 或 `false`。
- `Gate_E_evidence` (新增)：proof of Gate E；當 `Gate_E_passed: true` 時必填。格式為 array of paths / artifact IDs（例如 `["artifacts/decisions/TASK-001.decision.md", "artifacts/improvement/TASK-001.improvement.md"]`）。
- `Gate_E_timestamp` (新增)：Gate E 驗證通過時間戳，採 ISO 8601+08:00 格式。當 `Gate_E_passed: true` 時必填。

### 完整範例（包含 Gate E）

```json
{
  "task_id": "TASK-001",
  "state": "done",
  "current_owner": "Claude",
  "next_agent": "Claude",
  "required_artifacts": ["code", "research", "status", "task", "verify"],
  "available_artifacts": ["code", "decision", "improvement", "plan", "research", "status", "task", "verify"],
  "missing_artifacts": [],
  "blocked_reason": "",
  "last_updated": "2026-04-11T11:10:00+08:00",
  "Gate_E_passed": true,
  "Gate_E_evidence": ["artifacts/decisions/TASK-001.decision.md", "artifacts/improvement/TASK-001.improvement.md"],
  "Gate_E_timestamp": "2026-04-11T11:10:00+08:00"
}
```

---

## 5.9 Improvement Artifact Schema (PDCA)

檔名：`artifacts/improvement/TASK-001.improvement.md`

用途：在任務發生 failure、blocked、或流程缺陷後，執行 PDCA Act 階段——分析根因、執行矯正、提出系統層級預防措施。

命名規則：

- 主要改進：`TASK-001.improvement.md`
- 同一任務多次改進：`TASK-001-IMP-002.improvement.md`

必填區段：

```md
# Process Improvement

## Metadata
- Task ID:
- Artifact Type: improvement
- Source Task:
- Trigger Type: (failure / blocked / inefficiency / guard miss)
- Owner: Claude
- Status: draft
- Last Updated:

## Risk Analysis (新增)
- Predicted Risks: [R1, R2, ...]  # 來自 plan artifact 的 premortem 預測
- Realized Risks: [R1]             # 此次 blocked/failure 中實際發生的
- Missed Risks: []                 # plan 未預測但實際發生的（若無填 None）

## 1. What Happened

## 2. Why It Was Not Prevented

## 3. Failure Classification

## 4. Corrective Action (Immediate)

## 5. Preventive Action (System Level)

## 6. Validation

## 7. Impact Scope

## 8. Final Rule

## 9. Status
```

欄位規則：

- `Trigger Type`: 必須為 `failure`、`blocked`、`inefficiency` 或 `guard miss` 之一。
- `## Risk Analysis` (新增)：追蹤 premortem 預測與實際風險的映射。
  - `Predicted Risks`: 從 plan artifact 中的 `## Risks` 區段複製所有 R 編號（例如 `[R1, R2, R3]`）。
  - `Realized Risks`: 此次故障中實際觸發的風險編號。必須是 Predicted Risks 的子集或超集。若為超集，說明是 missed risk。
  - `Missed Risks`: 若有未在 plan 預測但實際發生的風險，在此列舉；若無填 `None`。此欄用於評估 premortem 品質。
- `## 1. What Happened`: 必須具體描述發生在哪個階段（Plan / Do / Check / Act）、哪個 agent、哪個 artifact，並用編號指出是哪條 Realized Risk。
- `## 2. Why It Was Not Prevented`: 必須指出哪條規則缺失、哪個 guard 沒覆蓋、哪個 prompt 太寬鬆。
- `## 3. Failure Classification`: 至少勾選一個分類（G1–G6、Premortem failure、Unknown gap）。
- `## 5. Preventive Action (System Level)`: **最重要區段**。必須至少包含一項：Prompt 修正、Guard 規則補強、Template 修正、或 Workflow 調整。
- `## 8. Final Rule`: 將改進轉成一句可執行規則。
- `## 9. Status`: `draft` → `approved` → `applied`。

工作流規則：

- **Gate E (PDCA)**：任何任務從 `blocked` 恢復前，必須先建立且通過驗證的 improvement artifact。`guard_status_validator.py` 在 `blocked → *` 轉移時自動檢查。
- 恢復前的 improvement artifact 必須為 `Status: applied`。`draft` 或 `approved` 不足以解除 blocked。

最低驗收標準：

- 不可只描述問題而無預防措施。
- Preventive Action 不可只寫「注意一下」，必須是可被 guard / prompt / template 執行的具體改動。
- Final Rule 必須是一句可直接加入 CLAUDE.md 或 guard script 的規則。
- `Validation` 不可空白，必須說明如何驗證該改善已落地。

---

## 5.10 Artifact Lineage MVP

用途：定義 artifact 間最小可查的 lineage 關係，供 registry 與後續自動化擴充使用。

最小 schema：

```yaml
lineage_entry:
  source_file: "artifacts/code/{task}.code.md"
  plan_item: "N.N"
  decision_refs:
    - "artifacts/decisions/{task}.decision.md"
  research_refs:
    - "artifacts/research/{task}.research.md"
  scope: "file-level only"
  generated_by: "build_decision_registry.py"
```

規則：

- `source_file`: 指向單一 code artifact，使用 repo-relative path。
- `plan_item`: 對應 code artifact `## Mapping To Plan` 的 `N.N` 項目。
- `decision_refs`: 指向相關 decision artifacts，使用 repo-relative path array。
- `research_refs`: 指向相關 research artifacts，使用 repo-relative path array。
- `scope`: 目前只支援 file-level only，不含行號、不含 commit hash。
- `generated_by`: 目前由 `build_decision_registry.py` 作為最小生成入口；未來可擴充其他 producer，但不得改變 MVP 的 file-level 邊界。

---

## 6. 合法性檢查規則

artifact 合法需同時符合：

1. 命名正確
2. 放在正確目錄
3. 包含必填欄位
4. 使用合法狀態值
5. 與上游 artifacts 的 task id 一致
6. 內容與角色責任一致
7. 沒有以模糊語句取代可驗證結論

若不合法，應：

- 視為缺件
- 不可作為下一步輸入
- 於 status artifact 記錄缺失

## 7. 版本與覆寫規則

- 同一 task 同一類型 artifact 原則上維持單一最新版本。
- 若需保留舊版，可另存備份，但主流程只認最新合法版本。
- 被新版本取代的 artifact，狀態應標記為 `superseded`。

## 8. 最小可用原則

對極小型任務可採 lightweight mode，但最少仍需：

- task artifact
- code artifact
- status artifact

若任務涉及外部知識，仍不可跳過 research artifact。
若任務需要驗收，仍不可跳過 verify artifact。

## 9. 禁止事項

以下 artifact 一律視為品質不合格：

- 只有標題沒有實質內容
- 用大量原始 log 取代摘要
- 把推測當成 confirmed fact
- 未列出 acceptance criteria
- 未列出 files changed
- 未列出風險或直接省略風險欄位
- status 與實際 artifacts 不一致

## 10. 最終原則

Artifact 的目的不是存檔，而是作為下一個代理的可用契約。

若某份 artifact 不能讓下一位代理不靠猜測就接手，那它就還不夠好。

