# Security Threat Model Assessment

## Metadata
- Repository: arcobaleno64/consilium-fabri
- Branch: master
- Commit: 4090bce
- Head Author Date: 2026-04-17 18:37:50 +0800
- Hostname: ARCOBALENO
- Analysis Mode: full
- Deployment Classification: LOCALHOST_SERVICE
- Analyzed At UTC: 2026-04-17 12:46:20
- Output Folder: threat-model-20260417-124620

## Analysis Context And Assumptions

- Scope is limited to the root repository and its reusable template. `external/hermes-agent/` is explicitly out of scope.
- This repository is a workflow orchestrator and script collection, not a public network-facing application. The main attack surface is the control plane around artifacts, local execution, GitHub automation, and publish tooling.
- The expected operators are maintainers and contributors working from local machines plus GitHub Actions runners on `ubuntu-latest`.
- There are no long-lived inbound listeners defined in the root repo. The main network activity is outbound HTTPS and git traffic to GitHub.

## Executive Summary

The root repo already has several meaningful controls: GitHub Actions are SHA pinned, workflow permissions are read-only where possible, `pip-audit` provides dependency baseline coverage, and the guard / prompt-regression / red-team suite gives this repository stronger workflow validation than a typical docs-and-scripts repo. Those controls lower supply-chain and accidental workflow drift risk, but they do not remove the repository's main security problem: the repo is itself a trusted control plane.

That control plane ingests mutable Markdown / JSON artifacts, dispatches them to external CLIs, executes local helper scripts, calls the GitHub API, and can publish wiki / release state with whichever credential is present. The highest residual risks are therefore artifact tampering, outbound request abuse, local token exposure, unbounded input processing, and one-person waiver / publish decisions.

This task reduces two high-frequency regression paths by adding a repo-local secrets scan and a focused static rules scan. The threat model still identifies several open design-level risks that need follow-up hardening beyond regression scanning.

## Overall Risk Rating

| Dimension | Rating | Rationale |
|-----------|--------|-----------|
| Exposure | Medium | No public listener, but local runners and GitHub Actions execute trusted repo code and can make outbound requests. |
| Impact | High | The repo can alter workflow contracts, artifact validity, wiki state, release state, and CI behavior. |
| Likelihood | Medium | An attacker typically needs contributor, maintainer, or local-process foothold, but the repo's control-plane privileges make that meaningful. |
| Residual Risk | High | Regression scans help, but artifact integrity, waiver governance, token hygiene, and outbound target control remain open. |

## Verified Security Controls Already Present

| Control | Evidence | Effect |
|---------|----------|--------|
| SHA-pinned GitHub Actions | `.github/workflows/workflow-guards.yml`, `.github/workflows/security-scan.yml` | Reduces third-party action supply-chain drift. |
| Least-privilege workflow permissions | `.github/workflows/workflow-guards.yml`, `.github/workflows/security-scan.yml` | Keeps default CI jobs on read-only token scope. |
| Dependency baseline scan | `.github/workflows/security-scan.yml` | Detects vulnerable Python packages in `requirements.txt`. |
| Contract and status guards | `artifacts/scripts/guard_contract_validator.py`, `artifacts/scripts/guard_status_validator.py` | Validates workflow contracts, artifact presence, and scope drift. |
| Prompt regression and red-team suite | `artifacts/scripts/prompt_regression_validator.py`, `artifacts/scripts/run_red_team_suite.py` | Detects workflow/prompt regressions and drill failures. |
| Repo-local regression scans added in TASK-980 | `artifacts/scripts/repo_security_scan.py` | Blocks high-confidence secrets leaks and common workflow/script foot-guns. |

## Key Risk Themes

1. Mutable artifacts are treated as workflow truth without cryptographic integrity or schema-bound size limits.
2. Outbound GitHub API and publish operations can be redirected or misused through local configuration and artifact-controlled inputs.
3. Local credentials are reused across validators and publish scripts with limited scrubbing or separation of duties.
4. The red-team and agent toolchain executes local code and external CLIs without sandboxing.
5. Human override and publish authority is auditable only within the same mutable repo state it is meant to govern.

## Prioritized Action Plan

### Immediate

1. Keep the new repo-local `secrets` and `static` scans mandatory in `security-scan.yml`.
2. Constrain GitHub API targets to an allowlist or default-only mode for validator replay paths.
3. Add explicit size ceilings for archive snapshots, artifact files, and scanner inputs.

### Near Term

1. Require dual approval or an out-of-band approval log for `--override`, release, and wiki publish operations.
2. Add schema validation for high-trust JSON and Markdown sections before dispatching to agents or replaying diff evidence.
3. Redact or scrub credentials from long-lived shell/process environments after publish flows complete.

### Longer Term

1. Separate local convenience scripts from higher-trust CI/release paths.
2. Consider signing or checksumming critical workflow contracts and prompt bundles.
3. Reduce dynamic execution surfaces in `run_red_team_suite.py` and agent dispatch wrappers.

## Findings Snapshot

| ID | Severity | Title | Status |
|----|----------|-------|--------|
| FIND-01 | High | Mutable artifact contracts drive high-trust workflow decisions | Open |
| FIND-02 | High | Artifact ingestion lacks schema and size ceilings | Open |
| FIND-03 | High | Agent dispatch sends untrusted task context to external CLIs | Open |
| FIND-04 | High | GitHub PR replay path accepts arbitrary API base URLs | Open |
| FIND-05 | High | Override and waiver flow lacks separation of duties | Open |
| FIND-06 | High | Red-team suite dynamically executes repo Python modules | Open |
| FIND-07 | Medium | GitHub credentials persist in local process context | Open |
| FIND-08 | High | Publish automation trusts local remotes and credentials too broadly | Open |
| FIND-09 | Medium | No sandboxing for subprocess and CLI execution | Open |
| FIND-10 | Medium | Generated artifacts and reports can retain sensitive operational context | Open |
| FIND-11 | Medium | Repo-local secrets regression scan closes a prior blind spot | Mitigated |
| FIND-12 | Medium | Focused static regression scan closes a prior workflow/script blind spot | Mitigated |

## Conclusion

The repository is not in crisis, but it is high leverage. Any compromise of its artifacts, local execution flow, or publish tooling has outsized impact because the repository defines and enforces workflow truth for downstream work. The new scans added in TASK-980 are the right first hardening layer, but they are only a floor. The next most valuable engineering work is stronger outbound target control, stricter artifact validation, and more robust human approval boundaries.