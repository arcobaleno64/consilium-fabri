# STRIDE + Abuse Cases — Threat Analysis

## Exploitability Tiers

Threats are classified into three exploitability tiers based on the prerequisites an attacker needs:

| Tier | Label | Prerequisites | Assignment Rule |
|------|-------|---------------|----------------|
| **Tier 1** | Direct Exposure | `None` | Exploitable by unauthenticated external attacker with NO prior access. The prerequisite field MUST say `None`. |
| **Tier 2** | Conditional Risk | Single prerequisite: `Authenticated User`, `Privileged User`, `Internal Network`, or single `{Boundary} Access` | Requires exactly ONE form of access. The prerequisite field has ONE item. |
| **Tier 3** | Defense-in-Depth | `Host/OS Access`, `Admin Credentials`, `{Component} Compromise`, `Physical Access`, or MULTIPLE prerequisites joined with `+` | Requires significant prior breach, infrastructure access, or multiple combined prerequisites. |

## Summary

| Component | Link | S | T | R | I | D | E | A | Total | T1 | T2 | T3 | Risk |
|-----------|------|---|---|---|---|---|---|---|-------|----|----|----|------|
| Human Maintainer | [Human Maintainer](#human-maintainer) | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 2 | 0 | 2 | 0 | Medium |
| Workflow Controller | [Workflow Controller](#workflow-controller) | 0 | 1 | 0 | 0 | 1 | 0 | 1 | 3 | 0 | 3 | 0 | High |
| Agent Dispatch | [Agent Dispatch](#agent-dispatch) | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 3 | 0 | 2 | 1 | High |
| Guard Validators | [Guard Validators](#guard-validators) | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 5 | 0 | 4 | 1 | Critical |
| Red Team Runner | [Red Team Runner](#red-team-runner) | 0 | 1 | 0 | 0 | 1 | 1 | 0 | 3 | 0 | 2 | 1 | High |
| Publish Automation | [Publish Automation](#publish-automation) | 0 | 1 | 0 | 1 | 0 | 0 | 2 | 4 | 0 | 3 | 1 | High |
| Artifact Store | [Artifact Store](#artifact-store) | 0 | 1 | 1 | 0 | 1 | 0 | 1 | 4 | 0 | 3 | 1 | High |
| Git Worktree | [Git Worktree](#git-worktree) | 0 | 1 | 0 | 2 | 0 | 0 | 0 | 3 | 0 | 2 | 1 | Medium |
| GitHub Platform | [GitHub Platform](#github-platform) | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | High |

---

## Human Maintainer

**Trust Boundary:** Maintainer Endpoint  
**Role:** Human operator who authors artifacts, approves exceptions, and triggers publish flows  
**Data Flows:** DF01, DF13

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| HM-T2-01 | Abuse | A single maintainer can request and apply `--override` or publish actions without peer approval, allowing policy exceptions from the same trust domain that benefits from them. | Privileged User | DF01, DF13 | Require dual approval or out-of-band approval records for override/release paths. | Open |
| HM-T2-02 | Information Disclosure | Local terminal history and process environment can expose `GH_TOKEN` / `GITHUB_TOKEN` values used by publish and validation scripts. | Local Process Access | DF13 | Prefer short-lived credentials, minimize verbose output, and scrub env after high-trust operations. | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified*

## Workflow Controller

**Trust Boundary:** Local Control Plane  
**Role:** Orchestration contract layer that defines what work is allowed and which artifacts are authoritative  
**Data Flows:** DF01, DF02, DF04

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| WC-T2-01 | Tampering | Mutable workflow docs and prompt contracts can be edited to steer agent behavior or relax expected guard behavior without stronger integrity controls than normal repo review. | Authenticated User | DF01, DF02 | Add stronger integrity or signed bundles for the highest-trust contracts; keep prompt regression mandatory. | Open |
| WC-T2-02 | Denial of Service | Oversized or deliberately dense task context can exhaust model context, validator runtime, or reviewer capacity because there are no global artifact size ceilings. | Authenticated User | DF01, DF02, DF04 | Enforce file-size and section-size ceilings before artifact promotion or agent dispatch. | Open |
| WC-T2-03 | Abuse | Ambiguity across instructions, plans, and workflow contracts can be exploited to justify off-plan work until downstream validators catch it. | Authenticated User | DF01, DF02 | Keep contract guard and plan/code mapping strict; add clearer precedence and machine-checked schema markers. | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified*

## Agent Dispatch

**Trust Boundary:** Local Control Plane  
**Role:** Wrapper layer that packages repository context and invokes external AI CLIs  
**Data Flows:** DF02, DF03

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| AD-T2-01 | Tampering | Agent dispatch forwards task context assembled from mutable repo files to external CLIs without schema validation or content fencing, so malformed or malicious artifacts can shape downstream execution. | Authenticated User | DF02, DF03 | Validate high-trust artifact structure before dispatch and reduce the set of files eligible for automatic context packing. | Open |
| AD-T2-02 | Information Disclosure | Dispatch wrappers can send more repository context than strictly necessary to external providers, exposing operational metadata and internal workflow state. | Authenticated User | DF02, DF03 | Redact or minimize context before dispatch; separate internal-only artifacts from model-facing context. | Open |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| AD-T3-01 | Abuse | Automatic model fallback changes the assurance profile of the execution path after repeated CLI/API errors without an explicit policy gate or approver. | Local Process Access + Authenticated User | DF02 | Require an explicit policy or audit note when wrappers step down to weaker fallback models for privileged tasks. | Open |

## Guard Validators

**Trust Boundary:** Local Control Plane  
**Role:** High-trust validation scripts that enforce artifact schema, scope drift, diff evidence replay, and state transitions  
**Data Flows:** DF05, DF06, DF11

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| GV-T2-01 | Tampering | GitHub PR file replay accepts any absolute `http(s)` API base URL that passes syntax validation, enabling outbound requests to unintended hosts when diff evidence is attacker-controlled. | Authenticated User | DF11 | Restrict API replay to `https://api.github.com` or an explicit allowlist for trusted GitHub Enterprise hosts. | Open |
| GV-T2-02 | Denial of Service | Archive snapshots, artifact content, and replayed JSON do not have consistent global size ceilings, allowing oversized inputs to degrade CI or local validation performance. | Authenticated User | DF05, DF06 | Enforce maximum artifact, archive, and response sizes before parsing. | Open |
| GV-T2-03 | Information Disclosure | Validator error paths can include remote error detail, filenames, and repository metadata in logs, expanding operational disclosure during failed replay or override scenarios. | Authenticated User | DF05, DF06, DF11 | Bound logged remote details and distinguish operator-facing remediation from raw provider responses. | Open |
| GV-T2-04 | Abuse | Decision waivers and override logs are recorded within the same trust domain as the artifacts they excuse, so exception approval lacks true separation of duties. | Privileged User | DF05 | Move approval evidence or approver identity checks outside the same mutable artifact set. | Open |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| GV-T3-01 | Repudiation | A broader worktree compromise lets an attacker rewrite both the failing artifacts and the override log that claims to approve them, weakening forensic trust. | Host/OS Access | DF05, DF06 | Store approval evidence in append-only or remote audit trails instead of only in repo files. | Open |

## Red Team Runner

**Trust Boundary:** Local Control Plane  
**Role:** Exercise harness that loads modules, creates temp repos, and launches subprocess-based validations  
**Data Flows:** DF07, DF08

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| RTR-T2-01 | Tampering | `run_red_team_suite.py` dynamically loads repo Python using `importlib.util.spec_from_file_location(...).loader.exec_module(...)`, so compromised repo code is executed by the harness. | Authenticated User | DF08 | Replace dynamic module execution with narrower imports or allowlisted entry points. | Open |
| RTR-T2-02 | Denial of Service | Fixture cloning plus repeated subprocess execution can exhaust CI or local runner resources when fixtures or generated reports grow unchecked. | Authenticated User | DF07, DF08 | Add size/time ceilings and cap fixture/report growth in red-team paths. | Open |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| RTR-T3-01 | Elevation of Privilege | If a repo helper or imported module is already compromised, the red-team harness runs it with the invoking user's privileges. | Git Worktree Compromise | DF08 | Isolate the harness with lower privileges or containerized execution for higher-trust runs. | Open |

## Publish Automation

**Trust Boundary:** Local Control Plane  
**Role:** Scripts that validate auth, inspect repo state, and mutate wiki/release state on GitHub  
**Data Flows:** DF09, DF10, DF12, DF13

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| PA-T2-01 | Information Disclosure | Publish scripts reuse `GH_TOKEN` / `GITHUB_TOKEN` in the current shell and process space, increasing the chance of local token exposure via process inspection or operator mistakes. | Local Process Access | DF12, DF13 | Use short-lived credentials and isolate or scrub env after publish flows. | Open |
| PA-T2-02 | Tampering | Publish operations trust local repo metadata and remotes, so a locally redirected remote or altered repo context can send side effects to the wrong target. | Local Process Access | DF10, DF12 | Validate expected owner/repo and trusted remote targets before mutating GitHub state. | Open |
| PA-T2-03 | Abuse | Wiki and release flows can be executed by a single maintainer with no built-in peer approval gate or signed release intent. | Privileged User | DF13 | Require dual approval or a remote approval artifact for publish operations. | Open |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| PA-T3-01 | Abuse | A compromised workstation or repo config can silently redirect publish side effects while still satisfying local preflight checks. | Host/OS Access | DF10, DF12, DF13 | Add explicit trusted-target checks and prefer CI-mediated publish paths for high-trust releases. | Open |

## Artifact Store

**Trust Boundary:** Repository Data  
**Role:** File-based workflow truth used as the authoritative state for tasks, plans, code, decisions, and verification  
**Data Flows:** DF03, DF04, DF05, DF07, DF09

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| AS-T2-01 | Tampering | Markdown and JSON artifacts are mutable repo files but act as high-trust workflow truth without signatures or content hashes. | Authenticated User | DF03, DF04, DF05 | Add stronger integrity guarantees for the highest-trust workflow contracts and decision artifacts. | Open |
| AS-T2-02 | Repudiation | Artifact state changes rely on normal git history and local files, leaving no append-only ledger for approvals or exception usage. | Authenticated User | DF03, DF04, DF05 | Add append-only decision/audit records outside the mutable repo state. | Open |
| AS-T2-03 | Denial of Service | Missing artifact size ceilings let large reports, evidence files, or copied fixtures slow or break validation and review. | Authenticated User | DF03, DF05, DF07, DF09 | Enforce maximum artifact and evidence sizes per type. | Open |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| AS-T3-01 | Abuse | An attacker with broader repo control can rewrite task, decision, and verify artifacts together to create a self-consistent but misleading state. | Git Worktree Compromise | DF03, DF04, DF05 | Separate approval evidence and final verification attestations from ordinary editable artifacts. | Open |

## Git Worktree

**Trust Boundary:** Repository Data  
**Role:** Local checkout and template mirror that feed validators, publish tooling, and future project scaffolding  
**Data Flows:** DF06, DF08, DF10

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| GWT-T2-01 | Information Disclosure | Before TASK-980 there was no repo-local secret regression scan for root/template content, increasing the chance of credential-like strings landing unnoticed. | Authenticated User | DF06, DF10 | `repo_security_scan.py secrets` is now required in `security-scan.yml`. | Mitigated |
| GWT-T2-02 | Tampering | Before TASK-980 there was no focused static regression scan for workflow/script foot-guns such as unpinned actions, `shell=True`, or `Invoke-Expression`. | Authenticated User | DF06, DF08, DF10 | `repo_security_scan.py static` is now required in `security-scan.yml`. | Mitigated |

#### Tier 3 — Defense-in-Depth

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| GWT-T3-01 | Information Disclosure | Local reports, coverage output, and generated threat-model artifacts can retain operational context useful to a local attacker or compromised workstation. | Host/OS Access | DF06, DF08, DF10 | Limit retention of generated outputs and avoid storing sensitive runtime data in reports. | Open |

## GitHub Platform

**Trust Boundary:** GitHub Service  
**Role:** Remote API and git destination for PR replay, wiki publish, and release publish  
**Data Flows:** DF11, DF12

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk

| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| GHP-T2-01 | Tampering | Validator replay can be redirected away from `api.github.com` when artifact-controlled diff evidence supplies a custom API base URL. | Authenticated User | DF11 | Allowlist trusted GitHub API hosts and reject arbitrary endpoints. | Open |
| GHP-T2-02 | Information Disclosure | Publish and replay flows disclose repository metadata and operation timing to the remote endpoint chosen by local config or artifact input. | Authenticated User | DF11, DF12 | Restrict outbound endpoints and keep remote error logging bounded. | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified*# STRIDE + Abuse Cases — Threat Analysis

## Exploitability Tiers

Threats are classified into three exploitability tiers based on the prerequisites an attacker needs:

| Tier | Label | Prerequisites | Assignment Rule |
|------|-------|---------------|----------------|
| **Tier 1** | Direct Exposure | `None` | Exploitable by unauthenticated external attacker with NO prior access. The prerequisite field MUST say `None`. |
| **Tier 2** | Conditional Risk | Single prerequisite: `Authenticated User`, `Privileged User`, `Internal Network`, or single `{Boundary} Access` | Requires exactly ONE form of access. The prerequisite field has ONE item. |
| **Tier 3** | Defense-in-Depth | `Host/OS Access`, `Admin Credentials`, `{Component} Compromise`, `Physical Access`, or MULTIPLE prerequisites joined with `+` | Requires significant prior breach, infrastructure access, or multiple combined prerequisites. |

## Summary
| Component | Link | S | T | R | I | D | E | A | Total | T1 | T2 | T3 | Risk |
|-----------|------|---|---|---|---|---|---|---|-------|----|----|----|------|
| Human Maintainer | [Human Maintainer](#human-maintainer) | 0 | 0 | 0 | 1 | 0 | 0 | 1 | 2 | 0 | 2 | 0 | Medium |
| Workflow Controller | [Workflow Controller](#workflow-controller) | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 2 | 0 | High |
| Agent Dispatch | [Agent Dispatch](#agent-dispatch) | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | High |
| Guard Validators | [Guard Validators](#guard-validators) | 0 | 1 | 1 | 1 | 1 | 0 | 1 | 5 | 0 | 4 | 1 | Critical |
| Red Team Runner | [Red Team Runner](#red-team-runner) | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 2 | 0 | High |
| Publish Automation | [Publish Automation](#publish-automation) | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 3 | 0 | 3 | 0 | High |
| Artifact Store | [Artifact Store](#artifact-store) | 0 | 1 | 0 | 0 | 1 | 0 | 0 | 2 | 0 | 2 | 0 | High |
| Git Worktree | [Git Worktree](#git-worktree) | 0 | 1 | 0 | 1 | 0 | 0 | 1 | 3 | 0 | 2 | 1 | Medium |
| GitHub Platform | [GitHub Platform](#github-platform) | 0 | 1 | 0 | 1 | 0 | 0 | 0 | 2 | 0 | 2 | 0 | High |

---

## Human Maintainer

**Trust Boundary:** Maintainer Endpoint
**Role:** Human operator who edits artifacts, runs scripts, and decides whether to override or publish.
**Data Flows:** DF01, DF13

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| HM-T2-01 | Abuse | A privileged maintainer can use `--override` or publish commands without peer review, suppressing genuine workflow failures or pushing unintended remote state. | Privileged User | DF01, DF13 | Require dual approval or an out-of-band approval log for overrides and publish actions. | Open |
| HM-T2-02 | Information Disclosure | Local terminal sessions and process environments can expose GitHub credentials reused by publish and validator scripts. | Local Process Access | DF13 | Prefer short-lived credentials, minimize verbose output, and scrub sensitive environment variables after use. | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified*

## Workflow Controller

**Trust Boundary:** Local Control Plane
**Role:** Governs task lifecycle, prompt contracts, and which artifacts are considered authoritative for next-step execution.
**Data Flows:** DF01, DF02, DF04

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| WC-T2-01 | Tampering | Mutable prompt and orchestration documents can steer downstream agent behavior if a contributor changes workflow contracts in-band. | Authenticated User | DF01, DF02 | Add stronger integrity guarantees for critical workflow contracts and require review on orchestration files. | Open |
| WC-T2-02 | Denial of Service | Oversized task artifacts or prompt payloads can exhaust validator runtime or model context before a task reaches a stable state. | Authenticated User | DF01, DF02, DF04 | Add file-size and section-size ceilings for high-trust artifacts before dispatch. | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified*

## Agent Dispatch

**Trust Boundary:** Local Control Plane
**Role:** Bridges repo-local task context into external AI CLIs and receives outputs back into the repository.
**Data Flows:** DF02, DF03

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| AD-T2-01 | Tampering | Untrusted task content is forwarded to external CLIs without schema gating or explicit content class boundaries, letting malicious artifact text influence downstream tool behavior. | Authenticated User | DF02, DF03 | Validate task payload structure and separate high-trust metadata from freeform narrative before dispatch. | Open |
| AD-T2-02 | Information Disclosure | Dispatch payloads can include sensitive repo context that is then processed by external CLIs outside the validator boundary. | Authenticated User | DF02, DF03 | Add redaction/minimization for context sent to external CLIs and separate secret-bearing context from model prompts. | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified*

## Guard Validators

**Trust Boundary:** Local Control Plane
**Role:** Validates artifacts, replays diff evidence, classifies waivers, and fetches GitHub PR file metadata.
**Data Flows:** DF05, DF06, DF11

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| GV-T2-01 | Tampering | `API Base URL` replay inputs can redirect validator outbound HTTPS calls away from `api.github.com` to a GitHub-compatible but attacker-controlled endpoint. | Authenticated User | DF11 | Constrain replay endpoints to an allowlist or default-only mode and reject arbitrary host overrides. | Open |
| GV-T2-02 | Information Disclosure | Validator replay and error reporting can leak repo metadata or internal endpoint behavior to unintended targets once outbound requests are redirected. | Authenticated User | DF11 | Pair outbound target allowlisting with tighter remote error redaction. | Open |
| GV-T2-03 | Denial of Service | Archive snapshots, artifact bodies, and replay inputs lack uniform size ceilings, allowing expensive parsing and diff reconstruction paths. | Authenticated User | DF05, DF06 | Enforce file-size and line-count ceilings before parsing high-trust artifacts. | Open |
| GV-T2-04 | Abuse | Single-maintainer override and waiver flows can downgrade or suppress guard failures without independent approval. | Privileged User | DF05, DF06 | Require a second approver or out-of-band evidence for override-sensitive states. | Open |

#### Tier 3 — Defense-in-Depth
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| GV-T3-01 | Repudiation | Override logs and task status are stored in the same mutable repo state, so a sufficiently privileged user can rewrite both the decision and its audit trail together. | Privileged User + Host/OS Access | DF05, DF06 | Move approval evidence to append-only storage or signed attestations outside the mutable task tree. | Open |

## Red Team Runner

**Trust Boundary:** Local Control Plane
**Role:** Executes static/live drill suites by loading local modules, copying fixtures, and running subprocess-based validations.
**Data Flows:** DF07, DF08

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| RTR-T2-01 | Tampering | `exec_module` dynamically loads repo Python modules, so malicious code committed into expected paths is executed inside the red-team harness. | Authenticated User | DF08 | Prefer explicit import allowlists or signed test helpers for dynamic loads. | Open |
| RTR-T2-02 | Denial of Service | Fixture copying and repeated subprocess execution can be inflated with large inputs or expensive helper behaviors. | Authenticated User | DF07, DF08 | Add fixture-size ceilings and tighter execution budgets for the drill harness. | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified*

## Publish Automation

**Trust Boundary:** Local Control Plane
**Role:** Reads release/wiki state, probes auth, and writes remote GitHub state.
**Data Flows:** DF09, DF10, DF12, DF13

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| PA-T2-01 | Information Disclosure | GitHub credentials discovered through `GH_TOKEN`, `GITHUB_TOKEN`, or `gh auth` remain available to the local publish process for the full script lifetime. | Local Process Access | DF12, DF13 | Minimize credential lifetime and clear or isolate auth context after publish steps complete. | Open |
| PA-T2-02 | Tampering | Publish scripts trust local remotes and repository metadata, so a manipulated checkout can direct wiki or release actions at unintended destinations. | Local Process Access | DF10, DF12 | Pin expected owner/repo targets or require explicit operator confirmation before mutation. | Open |
| PA-T2-03 | Abuse | One operator with one credential can publish wiki or release state without a second control, increasing insider and mistake risk. | Privileged User | DF13 | Introduce dual-approval or attestable approval gates for remote mutations. | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified*

## Artifact Store

**Trust Boundary:** Repository Data
**Role:** Holds workflow truth, evidence, and execution history as mutable Markdown and JSON files.
**Data Flows:** DF03, DF04, DF05, DF07, DF09

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| AS-T2-01 | Tampering | Markdown and JSON artifacts are mutable workflow truth without signing or append-only guarantees, enabling in-repo manipulation of planning and verification state. | Authenticated User | DF03, DF04, DF05 | Add integrity or attestation controls for critical artifacts and treat some documents as privileged contracts. | Open |
| AS-T2-02 | Denial of Service | Artifact files do not have uniform schema-bound size ceilings, so large evidence blobs can degrade validator and report generation behavior. | Authenticated User | DF03, DF05, DF07, DF09 | Enforce file and section limits before ingesting artifact content. | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified*

## Git Worktree

**Trust Boundary:** Repository Data
**Role:** Local repository checkout, template mirror, git metadata, and generated reports used by validators and publish scripts.
**Data Flows:** DF06, DF08, DF10

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| GW-T2-01 | Information Disclosure | Prior to TASK-980 the repo had no dedicated regression guard for committed credentials in tracked files. | Authenticated User | DF06, DF10 | `repo_security_scan.py secrets` is now mandatory in `security-scan.yml`. | Mitigated |
| GW-T2-02 | Tampering | Prior to TASK-980 dangerous workflow/script foot-guns relied mostly on manual review and general testing. | Authenticated User | DF06, DF08, DF10 | `repo_security_scan.py static` now blocks unpinned actions, `persist-credentials: true`, `pull_request_target`, `shell=True`, `Invoke-Expression`, and similar regressions. | Mitigated |

#### Tier 3 — Defense-in-Depth
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| GW-T3-01 | Abuse | Generated reports, evidence files, and local artifacts can retain operationally sensitive context longer than intended on developer machines. | Host/OS Access | DF06, DF08, DF10 | Minimize retention, add cleanup guidance, and avoid storing unnecessary sensitive context in generated reports. | Open |

## GitHub Platform

**Trust Boundary:** GitHub Service
**Role:** Remote API and git endpoint used for diff replay, wiki reachability checks, and release mutations.
**Data Flows:** DF11, DF12

### STRIDE-A Analysis

#### Tier 1 — Direct Exposure (No Prerequisites)

*No Tier 1 threats identified*

#### Tier 2 — Conditional Risk
| ID | Category | Threat | Prerequisites | Affected Flow | Mitigation | Status |
|----|----------|--------|---------------|---------------|------------|--------|
| GHP-T2-01 | Tampering | GitHub replay logic will trust any GitHub-compatible host if the base URL is overridden through diff evidence inputs. | Authenticated User | DF11 | Restrict replay to trusted hosts and treat host overrides as exceptional configuration. | Open |
| GHP-T2-02 | Information Disclosure | Publish and replay paths trust outbound GitHub traffic to whichever remote or API base the local configuration specifies. | Local Process Access | DF11, DF12 | Verify expected targets before remote mutations and minimize error detail returned from outbound calls. | Open |

#### Tier 3 — Defense-in-Depth

*No Tier 3 threats identified*