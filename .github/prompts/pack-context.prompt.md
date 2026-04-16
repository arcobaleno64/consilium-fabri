---
applyTo: "**"
---

# Pack Context — 大型任務上下文收斂工具

## 何時用

任務涉及 3 個以上的 artifacts  
需要跨多個 docs 文件查詢  
在一次性大工作前想快速整理思路

## 用法

準備階段

提示詞範本：
我需要執行一個大任務。在實作前，請幫我整理上下文。
- 任務名稱：TASK-XXX
- 相關 artifacts：task.md、plan.md、research.md
- 涉及的 docs：artifact_schema.md §5.3, premortem_rules.md
- 主要問題：（描述關鍵問題）

輸出格式

Context Pack — TASK-XXX

1. 任務核心
目標：（提煉目標）  
輸入：（已有的 artifacts 或資料）  
輸出：（要產生什麼）  
驗收標準：（怎樣算完成）

2. 依賴與先決條件
Artifact 依賴：（哪些 artifact 必須先完成）  
文件引用：（涉及的 docs 章節）  
外部依賴：（環境變數、工具、服務）

3. 關鍵規則
Rule 1：（從 docs 摘錄的硬規則）  
Rule 2：（從 memory 提取的經驗法則）  
Rule 3：（從 premortem 識別的風險）

4. 快速檢查清單
所有 artifacts 到位（已完成）  
所有 docs 都讀了摘要（已完成）  
所有風險都識別了（已完成）  
所有依賴都就位了（已完成）
5. 進入點
若所有檢查通過，執行：（具體第一步）  
若缺失 artifact，停在：（哪個 artifact needs rebuild）

示例

完成 TASK-903（Guard Contract Validator 改進）。

相關 artifacts：
- artifacts/decisions/TASK-903.decision.md
- artifacts/plans/TASK-903.plan.md
- artifacts/research/TASK-903.research.md

涉及的 docs：
- docs/artifact_schema.md §5.6（verify schema）
- docs/premortem_rules.md（風險）

請先幫我整理上下文。

## 好處

減少無謂的 context 切換  
先驗證前置條件，再執行  
產生可複用的檢查清單  
對齐實作方向，減少中途修正
