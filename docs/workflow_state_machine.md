# WORKFLOW_STATE_MACHINE

本文件定義 artifact-first workflow 的狀態機。目的不是好看，而是讓流程「不能亂跳」。

沒有 state machine 的系統，本質上就是聊天。

## 1. 狀態總覽

| 狀態 | 說明 |
|---|---|
| drafted | 任務已建立但尚未研究 |
| researched | 已完成 research artifact |
| planned | 已完成 plan artifact |
| coding | 正在或已完成程式修改 |
| testing | 測試進行中或完成 |
| verifying | 驗收進行中 |
| done | 任務完成 |
| blocked | 任務卡住 |

## 2. 狀態轉移圖（文字版）

```text
drafted
  -> researched
  -> planned (若任務不需要 research)
  -> blocked

researched
  -> planned
  -> blocked

planned
  -> coding
  -> blocked

coding
  -> testing
  -> verifying
  -> blocked

testing
  -> verifying
  -> coding (若需修復)
  -> blocked

verifying
  -> done
  -> coding (驗收失敗)
  -> blocked

blocked
  -> 任意前一合法狀態（需先建立 improvement artifact — Gate E）
```

## 3. 每個狀態的進入條件

### drafted
- 已建立 task artifact

### researched
- 存在合法 research artifact

### planned
- 存在合法 plan artifact
- 若需要 research，則 research 必須已完成
- 若任務不需要外部知識，可從 drafted 直接轉移至 planned（略過 researched）

### coding
- plan artifact 存在且 Ready For Coding = yes

### testing
- code artifact 存在

### verifying
- code artifact 存在
- 若有測試需求，test artifact 存在

### done
- verify artifact 存在
- verify result = pass

### blocked
- 任一必要 artifact 缺失
- 或發現衝突/風險/無法繼續

## 4. 非法轉移（必須阻止）

以下行為一律視為錯誤：

- drafted -> coding
- researched -> coding（跳過 plan）
- planned -> done
- coding -> done（未驗證）
- testing -> done（未驗證）
- verifying -> done（未 pass）

## 5. Blocked 規則

進入 blocked 時必須：

- 記錄 blocked_reason
- 指出缺失 artifact
- 指定下一個負責 agent

解除 blocked 條件：

- 缺失 artifact 補齊
- 或 decision log 解決衝突
- **且**必須建立 improvement artifact（Gate E, PDCA）
  - 記錄根因分析、矯正措施、與系統層級預防措施
  - `guard_status_validator.py` 在 `blocked → *` 轉移時自動檢查

## 6. 強制規則

1. 每次狀態變更必須更新 status.json
2. 狀態必須與實際 artifacts 一致
3. 不允許「口頭完成」狀態
4. 不允許跳過中間狀態
5. Every plan must be testable and mappable to code and verification artifacts
6. Implementation must not introduce changes not explicitly mapped to plan
7. verify 必須逐條對應 acceptance criteria
8. After any failure or blocked state, a Process Improvement artifact must be created before resuming workflow (Gate E)

## 7. 設計原則

- 狀態數量刻意少，避免複雜化
- 每個狀態對應明確 artifact
- 任何人都能從 artifacts 重建狀態

如果一個狀態不能用檔案證明存在，那它就不該存在

