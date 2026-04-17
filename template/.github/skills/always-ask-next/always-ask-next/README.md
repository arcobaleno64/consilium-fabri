# always-ask-next

這個 skill 會要求 Agent 在完成所有任務、宣告結束之前，先詢問使用者下一步要做什麼。

## 說明

always-ask-next 的核心目的，是避免 Agent 自行假設工作已完全結束，或漏掉最自然的後續操作。

## 安裝方式

### GitHub Copilot（VS Code）

要讓規則在所有工作區強制生效，需在 VS Code 使用者 prompts 目錄中放置 instructions 檔。

Windows 路徑：

C:/Users/arcobaleno/AppData/Roaming/Code/User/prompts

目前此環境已存在對應的全域指令檔，內容等效於 upstream 規則，會在完成任務前要求呼叫 AskUserQuestion。

### Skill 路徑

本工作區 skill 位置如下：

.github/skills/always-ask-next/SKILL.md

## 目錄結構

always-ask-next/
|- SKILL.md
|- README.md

## Upstream

來源倉庫：
[endman100/skill-always-ask-next](https://github.com/endman100/skill-always-ask-next)
