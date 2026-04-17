---
name: always-ask-next
description: Always ask the user what to do next before finishing all tasks. Use AskUserQuestion with 3 dynamically generated relevant suggestions. This is a mandatory rule.
---

# Always Ask Next

## 此 Skill 適用於

在 Agent 完成所有任務之前，強制詢問使用者接下來想做什麼，避免 Agent 自行假設結束點或遺漏後續行動。

## 規則

Before finishing all tasks, always use one AskUserQuestion to ask the user what to do next.

Question: What would you like to do next?
Header: Next Action

根據當前脈絡動態生成 3 個最相關的後續行動選項，並固定加入 Other (please specify) 作為第 4 個選項。

## 執行方式

1. 在完成當前所有任務後、宣告完成前，呼叫 AskUserQuestion。
2. header 固定為 Next Action。
3. question 固定為 What would you like to do next?
4. 依照目前任務脈絡，動態產生 3 個最相關的選項。
5. 第 4 個選項固定為 Other (please specify)。
6. 等待使用者回應後再結束互動。

## 範例

AskUserQuestion(
	header: "Next Action",
	question: "What would you like to do next?",
	options: [
		"<動態生成選項 1>",
		"<動態生成選項 2>",
		"<動態生成選項 3>",
		"Other (please specify)"
	]
)

## 備註

完整安裝說明見 README.md；工作區補充規範見 .github/prompts/always-ask-next.skill.md。
