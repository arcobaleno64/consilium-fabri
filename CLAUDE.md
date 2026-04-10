你目前在一個採用嚴格驗證的 artifact-first workflow 下運作。

在執行任何任務前：

1. 讀取所有相關 artifacts（task、research、plan、status）。
2. 從 status.json 判定目前 workflow state。
3. 確認繼續前所需 artifacts 都存在。
4. 若任何必要 artifact 缺失或不一致，必須 STOP 並將任務標記為 blocked。

全域規則：

- 不得依賴 memory 或先前對話。只能信任 artifacts。
- 不得在定義的 artifact paths 之外建立檔案。
- 不得產出中間筆記、scratch files 或替代輸出。
- 不得猜測。若資訊缺失或不確定，必須明確標記為 UNVERIFIED。

Artifact 紀律：

- 每一份輸出都必須嚴格遵守 artifact schema。
- 每一個具體 claim 都必須附上支撐來源（URL 或 artifact reference）。
- Artifact status 只能使用標準化值（例如 ready、pass、fail）。
- Task state transitions 必須遵守 workflow state machine。不得跳步。

執行控制：

- 若 scope 不清楚，必須 STOP，並改寫 decision artifact，而不是猜測。
- 若 environment/build/test 因外部限制失敗，必須 STOP 並記錄結果。不得擴張範圍。
- 只能有一個 agent 可以修改程式碼，其他 agent 都必須保持 read-only。
- 進入 coding phase 前，必須在 plan artifact 的 `## Risks` 區段完成 premortem 分析（see `docs/premortem_rules.md`）。每個 risk 都必須包含 Risk、Trigger、Detection、Mitigation、Severity。若 premortem 缺失或內容含糊，不得進入 coding。

完成規則：

- No artifact = not done.
- No verification = not done.
- No evidence = not valid.

若違反任一規則，將任務視為 blocked，並說明原因。

Template sync protocol：

- 修改任何 workflow file（CLAUDE.md、GEMINI.md、CODEX.md、AGENTS.md、docs/*.md、guard_status_validator.py、BOOTSTRAP_PROMPT.md）後，必須同步變更到 `template/`，並推送到 GitHub。
- 寫入 `template/` 前，先將專案特定引用泛化為 placeholders。
- 若檔案結構、gates、agent roles 或 features 有變動，也必須同步更新 `template/README.md` 與 `template/README.zh-TW.md`。
- 完整同步規則請見 `docs/orchestration.md` §9。

文件載入規範：

- Session 開始時不得一次載入所有 documentation files。請依階段按需載入。
- 完整索引與階段載入矩陣請先讀 `AGENTS.md`。
- Session start：讀 `AGENTS.md` + `docs/orchestration.md`
- 派發 Gemini 前：讀 `docs/subagent_roles.md` §4、`docs/subagent_task_templates.md`
- 派發 Codex 前：讀 `docs/subagent_roles.md` §5、`docs/subagent_task_templates.md`
- Planning 前：讀 `docs/artifact_schema.md` §5.3、`docs/premortem_rules.md`
- 狀態轉移前：讀 `docs/workflow_state_machine.md`
- Verification 前：讀 `docs/artifact_schema.md` §5.5-§5.6

Repository boundaries（{{PROJECT_NAME}}）：

- `external/{{REPO_NAME}}/` = 本地 dirty workbench，供 experiments 與 integration 使用。除了 upstream PR 之外，其餘工作都在此進行。
- `external/{{REPO_NAME}}-upstream-pr/` = 僅供送往 `{{UPSTREAM_ORG}}/{{REPO_NAME}}` 的 upstream PR 使用。除非當前任務明確是 upstream PR task，否則不得修改這個目錄。每次 PR 前，都要透過 git remotes（fetch + reset --hard upstream/<default>）重設到乾淨的 upstream 狀態，不可重新 clone。任何本地 feature / refactor 程式碼都不得進入此處。
- 若當前任務不是 upstream PR task，Claude 與 Codex 都必須拒絕修改 `external/{{REPO_NAME}}-upstream-pr/` 下的任何內容。
- 不得混用這兩個目錄的 commits。
