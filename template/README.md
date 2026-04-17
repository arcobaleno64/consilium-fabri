<div align="center">

# Consilium Fabri

<p>
  A production-minded multi-agent AI workflow for teams that want traceability, control, and engineering-grade delivery.
</p>

<p>
  <img src="https://img.shields.io/badge/Workflow-Multi--Agent-111111?style=flat-square" alt="Multi-Agent Workflow" />
  <img src="https://img.shields.io/badge/Architecture-Artifact--First-0A66C2?style=flat-square" alt="Artifact First" />
  <img src="https://img.shields.io/badge/Validation-Gate--Guarded-8A2BE2?style=flat-square" alt="Gate Guarded" />
  <img src="https://img.shields.io/badge/Agents-Claude%20Code%20%7C%20Gemini%20CLI%20%7C%20Codex%20CLI-2F855A?style=flat-square" alt="Agents" />
  <img src="https://img.shields.io/badge/Python-Validator-3776AB?style=flat-square&logo=python&logoColor=white" alt="Python Validator" />
</p>

<p>
  Turn AI-assisted development from scattered chat into a durable operating system for research, planning, implementation, and verification.
</p>

**[繁體中文](README.zh-TW.md)** | English

</div>

---

## Product Positioning

Consilium Fabri is a multi-agent AI workflow framework designed to live inside the repository itself. It is not built around "asking a model to code faster"; it is built around creating a delivery system with explicit boundaries, reviewable checkpoints, durable artifacts, and hard verification.

It is especially useful when you need to:

- keep engineering discipline while collaborating with AI
- separate research, planning, implementation, and verification into explicit stages
- prevent key decisions from disappearing into chat history
- reduce the risk of untraceable, unreviewable, or unreproducible AI output
- add an AI workflow layer to an existing project without adopting an entirely new platform

This project is not a prompt pack, and it is not a single-agent chat script. It is a workflow harness oriented toward engineering governance.

---

## Why This Project Exists

Most multi-agent AI development breaks down in familiar ways:

- research findings never land in a stable place
- plans and implementation drift apart until ownership becomes unclear
- verification stops at verbal claims instead of evidence
- agent roles overlap and task boundaries become blurry
- too much documentation gets stuffed into every prompt, increasing cost and instability

Consilium Fabri exists to compress those failure modes into an explicit operating model with state, artifacts, and gates.

---

## Core Capabilities

<table>
  <tr>
    <td width="33%" valign="top">
      <h3>Multi-Agent Collaboration</h3>
      <p>Claude Code, Gemini CLI, and Codex CLI each own a distinct responsibility so research, orchestration, and implementation stay focused instead of collapsing into a single blurry prompt.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Artifact First</h3>
      <p>Every task is anchored in task, research, plan, code, verify, decision, and status artifacts rather than hidden chat memory, making the workflow traceable, reviewable, and restartable.</p>
    </td>
    <td width="33%" valign="top">
      <h3>Gate Validation</h3>
      <p>Workflow gates and the validator enforce legal state transitions, required artifacts, and verification expectations so work cannot move forward on confidence alone.</p>
    </td>
  </tr>
</table>

---

## Product Highlights

### 1. Role Separation For Real Development Work
- Claude Code acts as the orchestrator and workflow driver
- Gemini CLI handles research and evidence gathering
- Codex CLI handles implementation and delivery
- Clear ownership reduces collisions, duplicated effort, and role drift

### 2. A Strict Gate-Guarded Workflow
- Tasks move through Intake, Research, Planning, Coding, Verification, and Done
- Each stage has explicit prerequisites
- Required steps cannot be skipped arbitrarily
- Delivery becomes easier to review, replay, and audit

### 3. Artifact-First Design You Can Audit
- research findings live in research artifacts instead of chat summaries
- implementation requires an approved plan artifact
- verification requires a verify artifact
- decisions can be recorded as decision artifacts
- status is tracked in machine-readable files that support automation

### 4. Validation As A Mechanism, Not A Slogan
- `guard_status_validator.py` is built in
- `guard_contract_validator.py` is built in
- legal state transitions can be checked automatically
- required artifacts, metadata, and research / PDCA contracts can be checked automatically
- root / `template/` / Obsidian workflow drift can be checked automatically
- it reduces the risk of work being declared done without being genuinely verified

### 5. A More Disciplined Context Loading Strategy
- agents do not need to read the entire documentation set on every run
- documentation is loaded by role and phase
- token usage stays lower and more predictable
- prompt pollution and instability are reduced across longer task chains

### 6. Documentation And Timestamp Discipline
- long-lived Markdown defaults to Traditional Chinese (Taiwan) unless a specific exception is needed
- commands, file paths, placeholders, schema literals, and status values remain in English
- recorded times and `Last Updated` values must use `Asia/Taipei` in ISO 8601 format with `+08:00`
- root docs, `template/` docs, and Obsidian entry docs must stay semantically aligned

### 7. Clear Guard Boundaries
- `guard_status_validator.py` validates task / artifact / state rules
- plan/code scope drift is now a default hard failure: dirty task-owned files are checked against actual git changed files, clean tasks can replay pinned `commit-range` evidence, use an `archive fallback` via `Archive Path` / `Archive SHA256` when git objects are gone, or use `github-pr` evidence against the GitHub PR files API; `Snapshot SHA256` still guards the reconstructed file list, `GITHUB_TOKEN` / `GH_TOKEN` covers private or rate-limited GitHub access, and `--allow-scope-drift` still only downgrades true drift, not corrupted evidence
- `guard_contract_validator.py` validates workflow docs, bootstrap rules, template sync, and Obsidian sync
- when `CLAUDE.md` / `GEMINI.md` / `CODEX.md` changes, prompt regression cases must be updated together
- a workflow rule change is incomplete until README, `template/`, and Obsidian entry docs are updated together

### 8. Built-In Red-Team Exercises
- `docs/red_team_runbook.md` defines the static attacks, live drills, and replay workflow
- `docs/red_team_scorecard.md` provides the scoring matrix
- `docs/red_team_backlog.md` tracks follow-up hardening work
- `python artifacts/scripts/run_red_team_suite.py --phase all` reruns the built-in red-team suite and live drill samples
- `python artifacts/scripts/prompt_regression_validator.py --root .` runs fixed prompt regression cases for `CLAUDE.md`, `GEMINI.md`, `CODEX.md`, and critical workflow contracts
- the fixed prompt regression suite now also covers artifact-only truth/completion, workflow sync completeness, Gemini blocked preconditions, Codex summary discipline, conflict-to-decision routing, decision schema integrity, external failure STOP, decision-gated scope waivers, historical diff evidence contracts, pinned diff evidence integrity, GitHub provider-backed diff evidence, and archive retention fallback contracts
- `python artifacts/scripts/run_red_team_suite.py --phase prompt` runs prompt regression through the same report pipeline

---

## Use Cases

This project is especially suitable for:

| Use Case | Description |
|---|---|
| Personal AI development framework | A solo developer can still manage AI collaboration with engineering discipline |
| Small team collaboration | Build a controlled workflow without adopting a large platform |
| Traceable AI delivery | Preserve a full trail across research, planning, implementation, and verification |
| Existing repository adoption | Add this as a workflow layer to an existing repo |
| Open source showcase | Demonstrate a practical methodology for AI-assisted engineering |

---

## Workflow Overview

```text
Intake
  |
  v
Research
  |
  v
Planning
  |
  v
Coding
  |
  v
Verification
  |
  v
Done
```

The model is simple on purpose: each stage produces the artifact that justifies the next stage. That keeps collaboration inspectable and prevents "magic progress" that only exists inside a chat transcript.

---

## Getting Started

### Prerequisites

- **Python 3.10+** (for validator scripts)
- **Git** (version control)
- **Claude Code** (orchestrator agent — via VS Code extension or CLI)
- **Gemini CLI** (research agent — optional, for full workflow)
- **Codex CLI** (implementation agent — optional, for full workflow)
- **PyYAML** (`pip install -r requirements.txt`)

### Quick Start — New Project

```bash
# 1. Clone the template into your project
git clone https://github.com/arcobaleno64/consilium-fabri.git my-project
cd my-project

# 1.5. Initialize external integrations tracked as submodules
git submodule update --init --recursive

# 2. Replace placeholders in CLAUDE.md (remove fork section if not needed)
#    {{PROJECT_NAME}}, {{REPO_NAME}}, {{UPSTREAM_ORG}}

# 3. Bootstrap validation
python artifacts/scripts/guard_status_validator.py --task-id TASK-900 --auto-classify
python artifacts/scripts/update_repository_profile.py
python artifacts/scripts/guard_contract_validator.py --check-readme
python artifacts/scripts/guard_contract_validator.py
python artifacts/scripts/prompt_regression_validator.py --root .

# 4. (Optional) Run the red-team suite
python artifacts/scripts/run_red_team_suite.py --phase all
```

See `BOOTSTRAP_PROMPT.md` for the full bootstrapping guide.

### Quick Start — Existing Project

Copy the `template/` directory contents into your repository root, replace placeholders, and run the same bootstrap validation commands above.

If your repository keeps external integrations as Git submodules, run `git submodule update --init --recursive` after cloning so local development and CI operate on the same tree shape.

---

## Repository Structure

```
.
├── AGENTS.md                  # Document index and phase-loading matrix
├── CLAUDE.md                  # Orchestrator (Claude Code) entry file
├── GEMINI.md                  # Research agent (Gemini CLI) entry file
├── CODEX.md                   # Implementation agent (Codex CLI) entry file
├── OBSIDIAN.md                # Obsidian vault entry note
├── BOOTSTRAP_PROMPT.md        # New project bootstrapping guide
├── README.md / README.zh-TW.md
├── requirements.txt           # Python dependencies (PyYAML)
│
├── docs/                      # Workflow specification documents
│   ├── orchestration.md       # Full workflow: goals, principles, stages, gates
│   ├── artifact_schema.md     # 8 artifact type schemas (§5.1–§5.8)
│   ├── workflow_state_machine.md  # 8 states + legal transitions
│   ├── premortem_rules.md     # Risk analysis format + quality guardrails
│   ├── subagent_roles.md      # 7 agent role definitions
│   ├── subagent_task_templates.md
│   ├── lightweight_mode_rules.md
│   ├── red_team_runbook.md    # Red-team exercise playbook
│   ├── red_team_scorecard.md  # Scoring matrix
│   ├── red_team_backlog.md    # Hardening backlog
│   └── templates/             # Subagent task prompt templates
│
├── artifacts/                 # All workflow artifacts (the single source of truth)
│   ├── tasks/                 # Task artifacts
│   ├── research/              # Research artifacts
│   ├── plans/                 # Plan artifacts
│   ├── code/                  # Code artifacts
│   ├── verify/                # Verification artifacts
│   ├── decisions/             # Decision artifacts
│   ├── improvement/           # Improvement artifacts
│   ├── status/                # Machine-readable status + decision registry
│   ├── red_team/              # Red-team exercise reports
│   └── scripts/               # Validator and automation scripts
│       ├── guard_status_validator.py
│       ├── guard_contract_validator.py
│       ├── prompt_regression_validator.py
│       ├── run_red_team_suite.py
│       ├── repo_health_dashboard.py
│       ├── build_decision_registry.py
│       ├── github_publish_common.ps1  # Shared auth/preflight helpers
│       ├── push-wiki.ps1              # Wiki publish with preflight
│       ├── publish-release.ps1        # Release publish with preflight
│       └── drills/            # Prompt regression test cases
│
├── .github/
│   ├── copilot-instructions.md    # VS Code Copilot global rules
│   ├── repository-profile.json   # GitHub About / Topics profile
│   ├── memory-bank/               # Stable reference knowledge base
│   ├── prompts/                   # Prompt and skill files
│   ├── agents/                    # Agent definition files
│   ├── skills/                    # Skill metadata
│   ├── dependabot.yml             # Dependabot config (actions + pip)
│   └── workflows/                 # GitHub Actions CI
│       ├── workflow-guards.yml    # Main CI pipeline (SHA-pinned actions)
│       └── security-scan.yml     # pip-audit dependency scan
│
├── template/                  # Clean template for new projects (sync target)
└── external/                  # External project integrations
```

---

## Validator Commands

| Command | Purpose |
|---|---|
| `python artifacts/scripts/guard_status_validator.py --task-id TASK-XXX` | Validate task state, artifacts, and scope drift |
| `python artifacts/scripts/guard_status_validator.py --task-id TASK-XXX --auto-classify` | Auto-classify task as lightweight or full-gate |
| `python artifacts/scripts/guard_contract_validator.py` | Validate root ↔ template ↔ Obsidian sync |
| `python artifacts/scripts/guard_contract_validator.py --check-readme` | Validate README structure compliance |
| `python artifacts/scripts/prompt_regression_validator.py --root .` | Run prompt regression test cases |
| `python artifacts/scripts/run_red_team_suite.py --phase all` | Run the full red-team exercise suite |
| `python artifacts/scripts/run_red_team_suite.py --phase prompt` | Run prompt regression via the report pipeline |
| `python artifacts/scripts/repo_health_dashboard.py` | Generate repository health dashboard |
| `python artifacts/scripts/build_decision_registry.py --root .` | Rebuild the decision registry |
| `python artifacts/scripts/update_repository_profile.py` | Update GitHub repository profile |
| `pwsh artifacts/scripts/push-wiki.ps1` | Push wiki/ to GitHub Wiki (with preflight) |
| `pwsh artifacts/scripts/push-wiki.ps1 -WhatIf` | Run wiki preflight only (no push) |
| `pwsh artifacts/scripts/publish-release.ps1 -Tag v0.4.0` | Create a GitHub Release (with preflight) |
| `pwsh artifacts/scripts/publish-release.ps1 -Tag v0.4.0 -WhatIf` | Run release preflight only |

---

## Security And Supply-Chain Hardening

- All GitHub Actions in `.github/workflows/` are pinned to full 40-character commit SHAs to prevent tag-mutation supply-chain attacks. Version comments (e.g. `# v4.3.1`) are preserved for Dependabot compatibility.
- `.github/dependabot.yml` is configured to automatically propose weekly updates for both `github-actions` and `pip` ecosystems.
- `.github/workflows/security-scan.yml` runs `pip-audit` against `requirements.txt` on every PR, push to master, and manual dispatch, producing both JSON and columnar output.
- Wiki and release publish scripts include mandatory preflight checks: auth probing (`GH_TOKEN` → `GITHUB_TOKEN` → `gh auth`), remote reachability, tag/release existence, and uninitialized wiki detection.
- All publish scripts support `-WhatIf` for dry-run validation without side effects.

---

## Operational Notes

- The default `workflow-guards` CI now runs with explicit read-only GitHub token permissions, disables persisted checkout credentials, cancels superseded runs per branch or pull request, and applies a job timeout to reduce avoidable runner exposure.
- `artifacts/scripts/load_env.ps1` and its `template/` counterpart now parse quoted `.env` values, ignore blank and commented lines, accept optional `export` prefixes, and preserve existing process environment variables by default.
- Use `pwsh -NoProfile -File artifacts/scripts/load_env.ps1 -Quiet` for silent loading in local automation, or add `-Force` only when you intentionally want `.env` values to overwrite variables that already exist in the current process.

---

## Context System

This project includes a layered context management system for VS Code Copilot:

- **`.github/copilot-instructions.md`** — Global stable rules, auto-loaded by VS Code
- **`.github/memory-bank/`** — Stable reference knowledge (artifact rules, workflow gates, prompt patterns, project facts)
- **`.github/prompts/`** — Task-scoped prompts (pack-context, context-review, remember-capture)
- **`.github/skills/`** — Reusable skill definitions (always-ask-next)

Agents load documentation by role and phase, not all at once. See `AGENTS.md` for the phase-loading matrix.

---

## Contributing

1. Fork the repository
2. Create a feature branch
3. Follow the artifact-first workflow: task → research → plan → code → verify
4. Run validators before submitting:
   ```bash
   python artifacts/scripts/guard_contract_validator.py
   python artifacts/scripts/prompt_regression_validator.py --root .
   ```
5. Open a Pull Request

All workflow documentation defaults to Traditional Chinese (Taiwan). Commands, file paths, placeholders, schema literals, and status values remain in English.

---

## License

This project is licensed under the [MIT License](LICENSE).
