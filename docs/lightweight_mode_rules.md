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
- verify artifact（若任務需要進入 `done` 狀態）

## 3. 可省略或精簡內容

在 lightweight mode 中可省略或精簡：

- research artifact（若不需查資料）
- test artifact（若已有既有測試覆蓋）
- verify artifact 的詳細內容（低風險時可使用最精簡格式，但 **verify artifact 本身不可省略**）

> **重要**：`guard_status_validator.py` 對 `done` 狀態強制要求 verify artifact 存在且 Pass Fail Result = pass。
> 若省略 verify artifact，任務將無法透過 validator 合法轉移至 `done`。
> 「可精簡」是指 verify artifact 的內容可以簡短，而不是整份文件不存在。

## 4. 不可省略

- acceptance criteria
- scope 定義
- files changed

## 5. 流程

```text
1. Claude 建立 task（state: drafted）
2. Claude 完成必要 research 後建立簡化 plan（state: researched -> planned）
3. Implementer 修改（state: coding）
4. 產出 code artifact（state: testing 或 verifying）
5. Claude 更新 status 至 done
```

狀態路徑範例：

```text
drafted -> researched -> planned -> coding -> verifying -> done
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

