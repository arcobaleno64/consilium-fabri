# Red Team Backlog

本文件記錄紅隊演練後應追蹤的缺口。每一項都必須能對應到具體規則、guard、文件或樣本。

## BKL-001 Codex 超出 plan 範圍仍主要靠 verify / decision 收斂

- 目前狀態：`guard_status_validator.py` 可驗 premortem 與 state，但尚未直接把 code diff 對 plan 映射做成自動 guard。
- 風險：Codex 若擴大修改範圍，主要仍靠 verify evidence、decision artifact 與人工 review 發現。
- 建議補強：新增 diff-to-plan 或 changed-files-to-plan heuristic guard，至少先比對 `## Files Changed` 與 `## Files Likely Affected`。

## BKL-002 Contract guard 的 exact-sync 清單需人工維護

- 目前狀態：`guard_contract_validator.py` 以明確檔案清單驗證 root / template 同步。
- 風險：新增 workflow 文件或腳本時，若忘記把檔案加進 exact-sync 清單，就可能產生未受監控的漂移。
- 建議補強：增加 workflow docs registry，或將 `docs/` 內特定命名慣例自動納入 sync 驗證。

## BKL-003 Red-team runner 目前聚焦 repo 內建案例

- 目前狀態：`run_red_team_suite.py` 主要驗證 research contract、premortem、Gate E 與 contract drift。
- 風險：外部工具憑證失效、上游 repo 變動、或第三方 CLI 行為異常等情境仍需額外 drill。
- 建議補強：第二輪加入 environment-precondition drills 與 external dependency drills。

## BKL-004 Scorecard 的最終分數仍需人工判讀

- 目前狀態：runner 可驗證案例是否符合預期，但五個維度的成熟度分數仍需主持人與記錄者填寫。
- 風險：不同演練輪次之間，評分標準可能漂移。
- 建議補強：建立固定評語範本與「0 / 1 / 2」範例，降低主觀差異。
