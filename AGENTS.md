# AGENTS -- Documentation Index

本檔案是 artifact-first multi-agent workflow 的文件索引。每個 agent 只需載入自己的入口檔 + 當前階段所需的參考文件。

## Agent Entry Points

| Agent | Entry File | Role | Auto-Loaded |
|---|---|---|---|
| Claude Code | `CLAUDE.md` | Orchestrator | Yes (project instruction) |
| Gemini CLI | `GEMINI.md` | Research-only | Yes (passed via prompt) |
| Codex CLI | `CODEX.md` | Implementation lead | Yes (passed via prompt) |

## Documentation Modules

| File | Purpose | ~Tokens | Load When |
|---|---|---|---|
| `docs/orchestration.md` | System prompt: goals, principles, workflow stages, gates, sync protocol | 2200 | Claude: session start; before template sync |
| `docs/artifact_schema.md` | Schema for all 8 artifact types (§5.1-§5.8) | 3300 | Before writing any artifact |
| `docs/subagent_roles.md` | Role definitions for 7 agents (§3-§9) | 3000 | Before dispatching subagent |
| `docs/workflow_state_machine.md` | 8 states + legal transitions | 600 | Before state transition |
| `docs/premortem_rules.md` | Risk analysis format + quality guard | 1900 | Before coding gate |
| `docs/subagent_task_templates.md` | Ready-to-use prompt templates | 650 | When dispatching subagent |
| `docs/lightweight_mode_rules.md` | Simplified flow for small tasks | 350 | For lightweight mode tasks |

## Phase Loading Matrix

| Phase | Claude Code loads | Gemini loads | Codex loads |
|---|---|---|---|
| **Intake** | `docs/orchestration.md` | -- | -- |
| **Research** | `docs/subagent_roles.md` §4, `docs/subagent_task_templates.md` | (GEMINI.md has all needed rules) | -- |
| **Planning** | `docs/artifact_schema.md` §5.3, `docs/workflow_state_machine.md`, `docs/premortem_rules.md` | -- | -- |
| **Coding** | `docs/subagent_roles.md` §5, `docs/subagent_task_templates.md` | -- | (CODEX.md has all needed rules) |
| **Verification** | `docs/artifact_schema.md` §5.5-§5.6, `docs/workflow_state_machine.md` | -- | -- |
| **Closure** | `docs/workflow_state_machine.md` | -- | -- |
| **Template Sync** | `docs/orchestration.md` §9 | -- | -- |

## Cross-Reference Convention

- Use `see docs/X.md §N` to reference specific sections without duplicating content.
- Example: "Research artifact format: see `docs/artifact_schema.md` §5.2"
- Agent entry files (CLAUDE/GEMINI/CODEX.md) inline critical rules that the agent cannot load on its own.
- Reference files in `docs/` are loaded on-demand by the orchestrator (Claude Code).

## Section Quick Reference

### docs/artifact_schema.md
- §5.1 Task / §5.2 Research / §5.3 Plan / §5.4 Code / §5.5 Test / §5.6 Verify / §5.7 Decision / §5.8 Status

### docs/subagent_roles.md
- §3 Claude Code / §4 Gemini CLI / §5 Codex CLI / §6 Implementer / §7 Tester / §8 Verifier / §9 Reviewer

### docs/premortem_rules.md
- §1-2 When & where / §3 Required fields / §4 Quality rules (P1-P8) / §5 Violation levels / §6 Minimum counts
