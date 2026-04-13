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
- plan/code scope drift is now a default hard failure (use `--allow-scope-drift` only for controlled exceptions)
- `guard_contract_validator.py` validates workflow docs, bootstrap rules, template sync, and Obsidian sync
- when `CLAUDE.md` / `GEMINI.md` / `CODEX.md` changes, prompt regression cases must be updated together
- a workflow rule change is incomplete until README, `template/`, and Obsidian entry docs are updated together

### 8. Built-In Red-Team Exercises
- `docs/red_team_runbook.md` defines the static attacks, live drills, and replay workflow
- `docs/red_team_scorecard.md` provides the scoring matrix
- `docs/red_team_backlog.md` tracks follow-up hardening work
- `python artifacts/scripts/run_red_team_suite.py --phase all` reruns the built-in red-team suite and live drill samples
- `python artifacts/scripts/prompt_regression_validator.py --root .` runs fixed prompt regression cases for `CLAUDE.md`, `GEMINI.md`, and `CODEX.md`
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
