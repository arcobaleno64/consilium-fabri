# Consilium Fabri

**[繁體中文](README.zh-TW.md)** | English

> *Consilium Fabri* — Latin for "Council of Craftsmen."
> Three cobblers with their wits combined equal Zhuge Liang the mastermind.

A battle-tested, gate-guarded workflow harness for **multi-agent AI development** with Claude Code (orchestrator), Gemini CLI (research), and Codex CLI (implementation).

## Quick Start

### 1. Clone and copy to your project

```bash
git clone https://github.com/arcobaleno64/consilium-fabri.git
cp -r consilium-fabri/ /path/to/your/project/
```

### 2. Replace placeholders

The template uses `{{PLACEHOLDER}}` syntax. Replace the following in `CLAUDE.md`:

| Placeholder | Description | Example |
|---|---|---|
| `{{PROJECT_NAME}}` | Your project name | `MyApp` |
| `{{REPO_NAME}}` | Upstream repo name (if using fork model) | `my-upstream-repo` |
| `{{UPSTREAM_ORG}}` | Upstream GitHub org/user (if using fork model) | `original-author` |

```bash
sed -i 's/{{PROJECT_NAME}}/MyApp/g; s/{{REPO_NAME}}/my-upstream-repo/g; s/{{UPSTREAM_ORG}}/original-author/g' CLAUDE.md
```

If your project does not use a fork model, remove the "Repository boundaries" section in `CLAUDE.md`.

### 3. Validate setup

```bash
python artifacts/scripts/guard_status_validator.py --task-id TASK-900
# Expected: [OK] Validation passed
```

### 4. Set up hooks (optional)

```bash
cp .claude/settings.json.example .claude/settings.json
```

## File Structure

```
├── CLAUDE.md                          # Claude Code entry point (auto-loaded)
├── GEMINI.md                          # Gemini CLI entry point (passed via prompt)
├── CODEX.md                           # Codex CLI entry point (passed via prompt)
├── AGENTS.md                          # Master index + phase loading matrix
├── BOOTSTRAP_PROMPT.md                # Ready-to-use prompt for starting new projects
├── docs/                              # Reference documentation (loaded on demand)
│   ├── orchestration.md               # System prompt: goals, principles, stages, gates
│   ├── artifact_schema.md             # Schema for all 8 artifact types
│   ├── subagent_roles.md              # Role definitions for 7 agents
│   ├── workflow_state_machine.md      # 8 states + legal transitions
│   ├── premortem_rules.md             # Risk analysis format + quality guard
│   ├── subagent_task_templates.md     # Prompt templates for subagents
│   └── lightweight_mode_rules.md      # Simplified flow for small tasks
├── artifacts/
│   ├── tasks/                         # Task definitions (TASK-XXX.task.md)
│   ├── status/                        # Machine-readable state (TASK-XXX.status.json)
│   ├── research/                      # Research findings (TASK-XXX.research.md)
│   ├── plans/                         # Implementation plans (TASK-XXX.plan.md)
│   ├── code/                          # Code change records (TASK-XXX.code.md)
│   ├── verify/                        # Verification results (TASK-XXX.verify.md)
│   ├── decisions/                     # Decision logs (TASK-XXX-DEC-XXX.md)
│   └── scripts/
│       └── guard_status_validator.py  # Gate validator (Python stdlib only)
├── .claude/
│   └── settings.json.example         # Hook examples (notification, auto-format)
└── README.md
```

## Token-Efficient Loading

Each agent loads only its entry file. Reference docs are loaded on demand per phase:

| Agent | Entry File | ~Tokens | Strategy |
|---|---|---|---|
| Claude Code | `CLAUDE.md` | 800 | Loads `docs/` per phase via `AGENTS.md` matrix |
| Gemini CLI | `GEMINI.md` | 1,500 | All critical rules inlined (no filesystem access) |
| Codex CLI | `CODEX.md` | 1,300 | All critical rules inlined |

**Saves 81–92%** compared to loading all docs (~16K tokens) at once.

## Workflow

Every task follows a strict gate-guarded pipeline:

```
Intake → Research → Planning → Coding → Verification → Done
  │         │          │         │          │
  Gate A    Gate B     Gate C    Gate D     ✓
```

| Gate | Requirement |
|---|---|
| **A — Research** | Task artifact must exist |
| **B — Planning** | Research artifact must exist |
| **C — Coding** | Plan `Ready For Coding: yes` + premortem quality check |
| **D — Verification** | Code artifact + `## Build Guarantee` in verify |

`guard_status_validator.py` enforces all gates programmatically.

## Agent Roles

| Agent | Role | Writes Code? |
|---|---|---|
| **Claude Code** | Orchestrator — dispatches tasks, writes artifacts | Artifacts only |
| **Gemini CLI** | Research — verified findings and constraints | No |
| **Codex CLI** | Implementer — production code per plan | Yes |

## Key Concepts

### Premortem Analysis
Before coding, the plan's `## Risks` must contain structured entries (R1, R2, ...) with Risk, Trigger, Detection, Mitigation, Severity. The validator hard-blocks insufficient premortems.

### Build Guarantee
Every verify artifact must prove that modified build units were actually built. Prevents false-positive "tests pass but build broken" scenarios.

### Negative Testing
Intentionally break something to prove the pipeline catches it — a lightweight form of mutation testing for workflow artifacts.

### Template Sync Protocol
When any workflow file is modified (entry files, `docs/*.md`, validator, bootstrap prompt), the orchestrator must sync changes to `template/` and push to GitHub. Project-specific references are generalized to `{{PLACEHOLDER}}` syntax. README updates are required when file structure, gates, agent roles, or features change. See `docs/orchestration.md` §9 for full rules.

## Customization

| What | Where |
|---|---|
| Build tools | `docs/artifact_schema.md` §5.6 |
| State transitions | `guard_status_validator.py` → `LEGAL_TRANSITIONS` |
| Required markers | `guard_status_validator.py` → `MARKERS` |
| Agent quality rules | `docs/subagent_roles.md` §4.5 |

## Roadmap

- [ ] Copier integration for lifecycle-managed updates
- [ ] CI/CD pipeline templates (GitHub Actions / Azure DevOps)
- [ ] MCP server integration examples
- [ ] Interactive bootstrap wizard

## License

[MIT](LICENSE)

---

*Extracted from battle-tested practice (TASK-002 through TASK-008). Lessons from false-positive verification, agent role drift, and upstream PR moot scenarios are baked into every constraint.*
