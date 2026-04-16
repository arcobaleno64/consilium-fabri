# Always Ask Next — Skill Metadata

**Category**: Workflow UX / Task Completion  
**Version**: 1.0  
**Last Updated**: 2026-04-16 +08:00  
**Status**: production

## Description

Prompt you with 3 contextually relevant next actions before marking a task complete.

## When to Use

- After successfully completing a task
- Before calling `task_complete`
- When the user might benefit from guided next steps

## When NOT to Use

- Task failed or is blocked
- User explicitly said "just finish"
- No clear next action exists

## Implementation

See [`.github/prompts/always-ask-next.skill.md`](../../prompts/always-ask-next.skill.md)

## Invokes

- `vscode_askQuestions` tool
- `task_complete` tool

## Example Triggers

```
"I just completed setup"           → Ask about next steps
"Testing passed"                   → Ask about documentation / deployment
"Did the changes work?"            → Ask about regression testing / rollout
```

## Notes

- Options should be 3-5 words each (concise)
- Base options on **completed task type**, not generic "what's next"
- Always include "Other" as final option
