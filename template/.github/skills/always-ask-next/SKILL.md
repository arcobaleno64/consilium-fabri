---
name: always-ask-next
description: 在標記任務完成前，使用 3 個符合上下文的下一步行動提示使用者。
---

# Always Ask Next — Skill Metadata

**Category**: Workflow UX / Task Completion  
**Version**: 1.0  
**Last Updated**: 2026-04-16 +08:00  
**Status**: production

## 說明

在標記任務完成前，使用 3 個符合上下文的下一步行動提示使用者。

## 何時使用

成功完成任務後  
在呼叫 task_complete 前  
當使用者可能受益於引導式下一步行動時

## 何時不使用

任務失敗或被阻擋  
使用者明確說「直接完成」  
沒有明確的下一步行動

## 實作

見 .github/prompts/always-ask-next.skill.md

## 呼叫方式

vscode_askQuestions 工具  
task_complete 工具

## 觸發範例

「I just completed setup」- 提示下一步  
「Testing passed」- 提示文件或部署選項  
「Did the changes work?」- 提示 regression 測試或部署選項

## 注意事項

每個選項應保持簡潔（3-5 個字）  
根據已完成的任務類型基礎化選項，而非泛用的「下一步是什麼」  
始終包含「Other」作為最後選項
