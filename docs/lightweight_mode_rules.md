# LIGHTWEIGHT_MODE_RULES

本文件定義小型任務的簡化流程，避免 artifact-first 系統變成官僚地獄。

## 1. 適用條件

僅當符合以下全部條件時可使用：

- 修改範圍非常小（單一檔案或明確區塊）
- 不涉及外部 API 或新知識
- 不涉及架構變更
- 不影響多模組

若任一不符合，禁止使用 lightweight mode

## 2. 最小必要 artifacts

即使是小任務，仍必須有：

- task artifact
- code artifact
- status artifact

## 3. 可省略內容

在 lightweight mode 中可省略：

- research artifact（若不需查資料）
- test artifact（若已有既有測試覆蓋）
- verify artifact（低風險時）

## 4. 不可省略

- acceptance criteria
- scope 定義
- files changed

## 5. 流程

```text
1. Claude 建立 task（state: drafted）
2. Claude 建立簡化 plan（state: planned）
   -> 可從 drafted 直接轉移至 planned，略過 researched
   -> guard_status_validator.py 支援 drafted -> planned 合法轉移
3. Implementer 修改（state: coding）
4. 產出 code artifact（state: testing 或 verifying）
5. Claude 更新 status 至 done
```

狀態路徑範例：

```text
drafted -> planned -> coding -> verifying -> done
```

## 6. 強制限制

- 不可因為是小任務就不記錄範圍
- 不可直接在主 thread 宣稱完成
- 不可跳過 code artifact

## 7. 何時升級為完整模式

以下情況必須升級：

- 發現需要查文件
- 發現修改範圍擴大
- 測試失敗
- 出現副作用或風險

## 8. 設計原則

lightweight mode 的目標是降低負擔，而不是降低紀律

如果你用它來偷懶，那這套系統會在一週內崩掉

