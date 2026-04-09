# Artifact-First Multi-Agent Workflow Template

A battle-tested, gate-guarded workflow harness for multi-agent software development with Claude Code (orchestrator), Gemini CLI (research), and Codex CLI (implementation).

## Quick Start

### 1. Copy template to your project

```bash
cp -r template/ /path/to/your/project/
```

### 2. Replace placeholders

The template uses `{{PLACEHOLDER}}` syntax. Replace the following in `CLAUDE.md`:

| Placeholder | Description | Example |
|---|---|---|
| `{{PROJECT_NAME}}` | Your project name | `MyApp` |
| `{{REPO_NAME}}` | Upstream repository name (if using fork model) | `my-upstream-repo` |
| `{{UPSTREAM_ORG}}` | Upstream GitHub org/user (if using fork model) | `original-author` |

```bash
# Example: one-liner replacement (Linux/macOS/Git Bash)
sed -i 's/{{PROJECT_NAME}}/MyApp/g; s/{{REPO_NAME}}/my-upstream-repo/g; s/{{UPSTREAM_ORG}}/original-author/g' CLAUDE.md
```

If your project does not use a fork model, you may remove or simplify the "Repository boundaries" section in `CLAUDE.md`.

### 3. Validate setup

```bash
python artifacts/scripts/guard_status_validator.py --task-id TASK-900
```

Expected output: `[OK] Validation passed`

### 4. Set up hooks (optional)

```bash
cp .claude/settings.json.example .claude/settings.json
# Edit to match your OS and formatter preferences
```

## File Structure

```
├── CLAUDE.md                          # Claude Code entry point (auto-loaded)
├── GEMINI.md                          # Gemini CLI entry point (passed via prompt)
├── CODEX.md                           # Codex CLI entry point (passed via prompt)
├── AGENTS.md                          # Master index + phase loading matrix
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
└── README.md                          # This file
```

## Token-Efficient Loading

Each agent only loads its entry file. Reference docs are loaded on demand:

| Agent | Entry File | Tokens | Additional docs loaded by orchestrator per phase |
|---|---|---|---|
| Claude Code | `CLAUDE.md` | ~800 | See `AGENTS.md` phase loading matrix |
| Gemini CLI | `GEMINI.md` | ~1500 | None (all critical rules inlined) |
| Codex CLI | `CODEX.md` | ~1300 | None (all critical rules inlined) |

Compared to loading all docs (~16K tokens), this saves 81-92% on initial load.

## Workflow Overview

Every task follows a strict gate-guarded pipeline:

```
Intake → Research → Planning → Coding → Verification → Done
  │         │          │         │          │
  └─ Gate A ┘   Gate B ┘  Gate C ┘   Gate D ┘
```

- **Gate A (Research)**: Task artifact must exist before research begins
- **Gate B (Planning)**: Research artifact must exist before planning begins
- **Gate C (Coding)**: Plan must have `Ready For Coding: yes` AND pass premortem quality check before coding begins
- **Gate D (Verification)**: Code artifact must exist; verify must include `## Build Guarantee`

The `guard_status_validator.py` enforces these gates programmatically.

## Agent Roles

| Agent | Role | Can Write Code? |
|---|---|---|
| **Claude Code** | Orchestrator — reads artifacts, dispatches tasks, writes artifacts | Yes (artifact files) |
| **Gemini CLI** | Research-only — produces verified findings and constraints | No |
| **Codex CLI** | Implementer — writes production code per plan | Yes (production code) |

See `docs/subagent_roles.md` for detailed role definitions, quality hard constraints, and collaboration patterns.

## Key Concepts

### Premortem Analysis
Before entering coding, the plan's `## Risks` section must contain structured risk entries (R1, R2, ...) each with Risk, Trigger, Detection, Mitigation, and Severity fields. The validator hard-blocks `planned → coding` if premortem quality is insufficient. See `docs/premortem_rules.md`.

### Build Guarantee
Every `verify` artifact must include a `## Build Guarantee` section proving that modified build units were actually built. This prevents false-positive verification.

### Negative Testing
Intentionally break something to prove the pipeline catches it. Example: remove a required marker from a verify artifact and confirm the validator rejects it.

### Repo Boundary Discipline
If using a fork model, maintain strict separation between your dirty workbench (`external/{{REPO_NAME}}/`) and upstream PR directory (`external/{{REPO_NAME}}-upstream-pr/`).

## Customization

### Adding build tools
Edit `docs/artifact_schema.md` section 5.6 to add your project's build/test commands to the Build Guarantee rules.

### Extending the validator
Edit `artifacts/scripts/guard_status_validator.py`:
- `LEGAL_TRANSITIONS` dict — add custom state transitions
- `required_markers` dict — add required section headers per artifact type
- `STATE_REQUIRED_ARTIFACTS` dict — adjust which artifacts are needed per state

### Agent quality rules
Edit `docs/subagent_roles.md` section 4.5 to add project-specific quality constraints for research agents.

## Future Iterations

- [ ] Copier integration (`copier.yml`) for lifecycle-managed template updates
- [ ] CI/CD pipeline templates (GitHub Actions / Azure DevOps)
- [ ] MCP server integration examples
- [ ] Interactive bootstrap wizard
- [ ] Multi-language support

## Origin

Extracted from the [Antigravity/CLI](https://github.com/arcobaleno64) project's battle-tested artifact-first workflow (TASK-002 through TASK-008). Lessons learned from false-positive verification incidents, Gemini role drift, and upstream PR moot scenarios are baked into the template's constraints and quality rules.
