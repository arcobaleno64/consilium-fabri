---
applyTo: "**"
---

# Skill：Always Ask Next

## 目標

在任務完成後，在結束工作前，自動提示使用者下一步方向。

## 規則

在宣告任務完成之前，必須：

1. 輸出簡潔的工作摘要（1-3 句）
2. 提出「Next Action」問句：
   header: "Next Action"
   question: "What would you like to do next?"
3. 提供 3 個動態相關的選項（基於剛完成的任務）
4. 第 4 個選項固定為 "Other (please specify)"

## 範例

### 完成「實作 Guard Validator」後

Next Action 選項：
1. Review the implementation with code review
2. Run regression tests for all artifacts
3. Update README with new validator usage
4. Other (please specify)

### 完成「文件翻譯」後

Next Action 選項：
1. Proofread translated sections
2. Add translations to Obsidian YAML headers
3. Regenerate README TOC
4. Other (please specify)

## 觸發條件

任務成功完成
所有驗證通過
所有 artifact 到位

在宣告完成前執行問卷。

## 禁止項

不要沉悶無聊的選項（「做更多」、「全部檢查」）。
不要問「要不要改這裡」這類依賴使用者決定的空洞問題。
不要在 task 失敗或被 block 時問（只在成功時問）。
