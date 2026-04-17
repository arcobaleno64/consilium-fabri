# Security Findings

## Prioritized Findings

| ID | Severity | Status | Title |
|----|----------|--------|-------|
| FIND-01 | High | Open | Mutable artifact contracts drive high-trust workflow decisions |
| FIND-02 | High | Open | Artifact ingestion lacks schema and size ceilings |
| FIND-03 | High | Open | Agent dispatch sends untrusted task context to external CLIs |
| FIND-04 | High | Open | GitHub PR replay path accepts arbitrary API base URLs |
| FIND-05 | High | Open | Override and waiver flow lacks separation of duties |
| FIND-06 | High | Open | Red-team suite dynamically executes repo Python modules |
| FIND-07 | Medium | Open | GitHub credentials persist in local process context |
| FIND-08 | High | Open | Publish automation trusts local remotes and credentials too broadly |
| FIND-09 | Medium | Open | No sandboxing for subprocess and CLI execution |
| FIND-10 | Medium | Open | Generated artifacts can retain sensitive operational context |
| FIND-11 | Medium | Mitigated | Repo-local secrets regression scan closes a prior blind spot |
| FIND-12 | Medium | Mitigated | Focused static regression scan closes a prior workflow/script blind spot |

## FIND-01 — Mutable artifact contracts drive high-trust workflow decisions

- Severity: High
- Status: Open
- CWE: CWE-345, CWE-20
- OWASP: A08 Software/Data Integrity Failures, A06 Insecure Design
- Affected Components: Workflow Controller, Artifact Store
- Related Threats: WC-T2-01, AS-T2-01
- Evidence: Workflow truth is stored as ordinary Markdown/JSON artifacts and orchestration docs under `artifacts/`, `CLAUDE.md`, `AGENTS.md`, and `docs/orchestration.md`.
- Risk: A contributor can modify the same files that define workflow authority, causing downstream automation and reviewers to operate on attacker-shaped truth.
- Remediation: Add stronger integrity controls for the highest-trust contracts, such as signed bundles, content hashes, or stricter promotion gates for critical workflow files.

## FIND-02 — Artifact ingestion lacks schema and size ceilings

- Severity: High
- Status: Open
- CWE: CWE-400, CWE-770
- OWASP: A10 Mishandling of Exceptional Conditions, A06 Insecure Design
- Affected Components: Workflow Controller, Guard Validators, Artifact Store
- Related Threats: WC-T2-02, GV-T2-02, AS-T2-03
- Evidence: Artifact validation enforces presence and structure, but there is no consistent global ceiling for artifact size, archive snapshot size, or replay payload size.
- Risk: Oversized Markdown, JSON, or archive inputs can slow or break local validation, CI jobs, and human review.
- Remediation: Define per-artifact size ceilings, fail fast on oversize inputs, and cap remote replay payload handling.

## FIND-03 — Agent dispatch sends untrusted task context to external CLIs

- Severity: High
- Status: Open
- CWE: CWE-20, CWE-201
- OWASP: A06 Insecure Design, A04 Cryptographic Failures
- Affected Components: Agent Dispatch
- Related Threats: AD-T2-01, AD-T2-02, AD-T3-01
- Evidence: `Invoke-GeminiAgent.ps1` and `Invoke-CodexAgent.ps1` package task context for external CLIs, while workflow truth is assembled from mutable repo artifacts.
- Risk: Malicious or malformed artifacts can influence external CLI execution, and more repository context than necessary may be disclosed upstream.
- Remediation: Reduce the context set, validate high-trust sections before dispatch, and redact internal-only workflow state.

## FIND-04 — GitHub PR replay path accepts arbitrary API base URLs

- Severity: High
- Status: Open
- CWE: CWE-918
- OWASP: A10 Mishandling of Exceptional Conditions, A06 Insecure Design
- Affected Components: Guard Validators, GitHub Platform
- Related Threats: GV-T2-01, GHP-T2-01
- Evidence: `guard_status_validator.py` accepts any absolute `http(s)` API base URL in `normalize_api_base_url(...)` and uses it in `collect_github_pr_files(...)`.
- Risk: Diff-evidence replay can be redirected to attacker-controlled or unintended endpoints, turning a validation path into outbound request capability.
- Remediation: Allow only `https://api.github.com` by default and require explicit allowlists for trusted GitHub Enterprise hosts.

## FIND-05 — Override and waiver flow lacks separation of duties

- Severity: High
- Status: Open
- CWE: CWE-269, CWE-285
- OWASP: A01 Broken Access Control, A06 Insecure Design
- Affected Components: Human Maintainer, Guard Validators, Publish Automation
- Related Threats: HM-T2-01, GV-T2-04, GV-T3-01, PA-T2-03
- Evidence: Override logs are written back into repo-controlled status paths, and publish operations can be executed by a single privileged maintainer.
- Risk: The same trust domain can request, approve, and record exceptions or publishes, weakening non-repudiation and allowing policy bypass.
- Remediation: Introduce peer approval requirements or a remote append-only approval log for overrides and publish operations.

## FIND-06 — Red-team suite dynamically executes repo Python modules

- Severity: High
- Status: Open
- CWE: CWE-94
- OWASP: A08 Software/Data Integrity Failures, A06 Insecure Design
- Affected Components: Red Team Runner
- Related Threats: RTR-T2-01, RTR-T3-01
- Evidence: `run_red_team_suite.py` loads modules via `spec_from_file_location(...)` and `spec.loader.exec_module(...)` before running subprocess-based cases.
- Risk: A compromised helper module or fixture path is executed with the invoking user's privileges.
- Remediation: Replace dynamic execution with allowlisted imports or isolated runner environments for higher-trust drill execution.

## FIND-07 — GitHub credentials persist in local process context

- Severity: Medium
- Status: Open
- CWE: CWE-312, CWE-522
- OWASP: A04 Cryptographic Failures
- Affected Components: Human Maintainer, Publish Automation
- Related Threats: HM-T2-02, PA-T2-01
- Evidence: `github_publish_common.ps1` probes `GH_TOKEN` and `GITHUB_TOKEN`, then reuses the current shell context for git/gh operations.
- Risk: Local process inspection, operator mistakes, or verbose debugging can expose credentials with repository mutation capability.
- Remediation: Prefer short-lived tokens, minimize echo paths, and scrub sensitive env variables after high-trust operations.

## FIND-08 — Publish automation trusts local remotes and credentials too broadly

- Severity: High
- Status: Open
- CWE: CWE-441, CWE-441
- OWASP: A01 Broken Access Control, A08 Software/Data Integrity Failures
- Affected Components: Publish Automation, GitHub Platform
- Related Threats: PA-T2-02, PA-T3-01, GHP-T2-02
- Evidence: Publish tooling reads repo metadata and remotes from the current worktree, then uses whichever credential source passes preflight.
- Risk: A redirected remote or tampered local repo context can send wiki/release side effects to an unintended target while still passing local checks.
- Remediation: Verify expected owner/repo targets explicitly before mutation and prefer CI-mediated publishing for release-grade operations.

## FIND-09 — No sandboxing for subprocess and CLI execution

- Severity: Medium
- Status: Open
- CWE: CWE-250, CWE-77
- OWASP: A06 Insecure Design
- Affected Components: Agent Dispatch, Red Team Runner
- Related Threats: AD-T3-01, RTR-T2-02, RTR-T3-01
- Evidence: The repository runs external CLIs and subprocesses from local scripts and test harnesses without isolation boundaries beyond the current user session.
- Risk: Once local repo content or environment is compromised, the same execution path can be reused to run attacker-shaped commands and helpers.
- Remediation: Use isolated environments for higher-trust runs and narrow the set of commands/modules eligible for execution.

## FIND-10 — Generated artifacts can retain sensitive operational context

- Severity: Medium
- Status: Open
- CWE: CWE-200
- OWASP: A09 Security Logging and Alerting Failures
- Affected Components: Git Worktree
- Related Threats: GWT-T3-01
- Evidence: Threat-model outputs, coverage reports, red-team reports, and verification artifacts are stored as plain repo files and can reveal workflow structure, hostnames, and operational timing.
- Risk: A local attacker or compromised workstation gains additional context for targeted abuse of the control plane.
- Remediation: Minimize retained runtime metadata and treat generated operational artifacts as sensitive local outputs.

## FIND-11 — Repo-local secrets regression scan closes a prior blind spot

- Severity: Medium
- Status: Mitigated
- CWE: CWE-798
- OWASP: A04 Cryptographic Failures, A08 Software/Data Integrity Failures
- Affected Components: Git Worktree
- Related Threats: GWT-T2-01
- Evidence: TASK-980 adds `artifacts/scripts/repo_security_scan.py secrets` to `.github/workflows/security-scan.yml` for both root and template.
- Risk: Before this task, secret-like patterns in root/template files could land without a dedicated repo-local regression check.
- Remediation: Keep the secrets scan mandatory and periodically tune placeholder filters against real repo patterns.

## FIND-12 — Focused static regression scan closes a prior workflow/script blind spot

- Severity: Medium
- Status: Mitigated
- CWE: CWE-829, CWE-94
- OWASP: A08 Software/Data Integrity Failures, A06 Insecure Design
- Affected Components: Git Worktree
- Related Threats: GWT-T2-02
- Evidence: TASK-980 adds `artifacts/scripts/repo_security_scan.py static` to `.github/workflows/security-scan.yml` and unit-tests its workflow/script rules.
- Risk: Before this task, unsafe patterns such as unpinned actions, `shell=True`, or `Invoke-Expression` could regress without a repo-specific guard.
- Remediation: Keep the static scan narrow, high-signal, and synchronized with the template workflow.# Security Findings

## Summary

| ID | Severity | Title | Affected Components | Related Threats | Status |
|----|----------|-------|---------------------|-----------------|--------|
| FIND-01 | High | Mutable artifact contracts drive high-trust workflow decisions | Workflow Controller, Artifact Store | WC-T2-01, AS-T2-01 | Open |
| FIND-02 | High | Artifact ingestion lacks schema and size ceilings | Workflow Controller, Guard Validators, Artifact Store | WC-T2-02, GV-T2-03, AS-T2-02 | Open |
| FIND-03 | High | Agent dispatch forwards untrusted task context to external CLIs | Agent Dispatch | AD-T2-01, AD-T2-02 | Open |
| FIND-04 | High | GitHub PR replay path accepts arbitrary API base URLs | Guard Validators, GitHub Platform | GV-T2-01, GV-T2-02, GHP-T2-01 | Open |
| FIND-05 | High | Override and waiver flow lacks separation of duties | Human Maintainer, Guard Validators | HM-T2-01, GV-T2-04, GV-T3-01 | Open |
| FIND-06 | High | Red-team suite dynamically executes repo Python modules | Red Team Runner | RTR-T2-01 | Open |
| FIND-07 | Medium | GitHub credentials persist in local publish and validation contexts | Human Maintainer, Publish Automation | HM-T2-02, PA-T2-01 | Open |
| FIND-08 | High | Publish automation trusts local remotes and credentials too broadly | Publish Automation, GitHub Platform | PA-T2-02, PA-T2-03, GHP-T2-02 | Open |
| FIND-09 | Medium | No sandboxing for subprocess and CLI execution | Agent Dispatch, Red Team Runner | RTR-T2-02 | Open |
| FIND-10 | Medium | Generated reports and evidence can retain sensitive operational context | Git Worktree | GW-T3-01 | Open |
| FIND-11 | Medium | Repo-local secrets regression scan now closes a prior blind spot | Git Worktree | GW-T2-01 | Mitigated |
| FIND-12 | Medium | Focused static regression scan now closes a prior workflow blind spot | Git Worktree | GW-T2-02 | Mitigated |

## FIND-01 Mutable Artifact Contracts Drive High-Trust Workflow Decisions

- Severity: High
- CWE: CWE-345 Insufficient Verification of Data Authenticity
- OWASP: A06 Insecure Design, A08 Software/Data Integrity Failures
- Affected Components: Workflow Controller, Artifact Store
- Related Threats: WC-T2-01, AS-T2-01
- Evidence: The repo treats Markdown and JSON artifacts as workflow truth, while validators primarily check structure, presence, and transitions rather than authenticity.
- Impact: A contributor who can alter high-trust artifacts can steer planning, verification, and downstream agent behavior without breaking the basic artifact schema.
- Remediation: Add stronger integrity controls for critical workflow contracts, such as signed checksums, stricter branch protection, or explicit privileged-artifact classes.
- Status: Open

## FIND-02 Artifact Ingestion Lacks Schema And Size Ceilings

- Severity: High
- CWE: CWE-400 Uncontrolled Resource Consumption
- OWASP: A10 Mishandling of Exceptional Conditions
- Affected Components: Workflow Controller, Guard Validators, Artifact Store
- Related Threats: WC-T2-02, GV-T2-03, AS-T2-02
- Evidence: Artifact parsing and archive replay perform structural validation but do not consistently enforce hard file-size or section-size limits before expensive processing.
- Impact: Large or intentionally pathological artifacts can consume validator runtime, CI minutes, or model context and prevent stable task progress.
- Remediation: Add explicit byte, line, and section limits to trusted artifact readers and fail fast on oversized inputs.
- Status: Open

## FIND-03 Agent Dispatch Forwards Untrusted Task Context To External CLIs

- Severity: High
- CWE: CWE-20 Improper Input Validation
- OWASP: A06 Insecure Design, A08 Software/Data Integrity Failures
- Affected Components: Agent Dispatch
- Related Threats: AD-T2-01, AD-T2-02
- Evidence: Dispatch wrappers pass task context into external AI CLIs without a distinct schema boundary between privileged metadata and freeform artifact text.
- Impact: Malicious or over-broad artifact content can influence downstream model/tool behavior and leak more repo context than necessary.
- Remediation: Validate dispatch payload structure, minimize context, and separate sensitive system metadata from model-facing prompt text.
- Status: Open

## FIND-04 GitHub PR Replay Path Accepts Arbitrary API Base URLs

- Severity: High
- CWE: CWE-918 Server-Side Request Forgery
- OWASP: A10 Mishandling of Exceptional Conditions, A06 Insecure Design
- Affected Components: Guard Validators, GitHub Platform
- Related Threats: GV-T2-01, GV-T2-02, GHP-T2-01
- Evidence: `normalize_api_base_url()` accepts any absolute `http(s)` URL, and replay logic then performs outbound requests with optional bearer auth against that host.
- Impact: Diff evidence replay can be redirected to a hostile or unintended endpoint, causing outbound request abuse and error-detail leakage.
- Remediation: Restrict allowed API hosts, default to `https://api.github.com`, and require explicit approval for enterprise overrides.
- Status: Open

## FIND-05 Override And Waiver Flow Lacks Separation Of Duties

- Severity: High
- CWE: CWE-284 Improper Access Control
- OWASP: A01 Broken Access Control, A09 Security Logging and Alerting Failures
- Affected Components: Human Maintainer, Guard Validators
- Related Threats: HM-T2-01, GV-T2-04, GV-T3-01
- Evidence: Override logs are stored in the same mutable repo space as the task state they govern, and a single privileged operator can both initiate and justify an override.
- Impact: Genuine workflow failures can be suppressed without independent approval, and the audit trail can be rewritten by a sufficiently privileged actor.
- Remediation: Require dual approval, externalize override evidence, or sign approval records separately from mutable task artifacts.
- Status: Open

## FIND-06 Red-Team Suite Dynamically Executes Repo Python Modules

- Severity: High
- CWE: CWE-494 Download of Code Without Integrity Check
- OWASP: A08 Software/Data Integrity Failures
- Affected Components: Red Team Runner
- Related Threats: RTR-T2-01
- Evidence: `run_red_team_suite.py` loads Python modules dynamically with `importlib.util.spec_from_file_location(...); spec.loader.exec_module(module)`.
- Impact: Malicious code committed into expected helper paths executes inside the red-team harness during validation.
- Remediation: Replace generic dynamic loading with explicit allowlists or safer import paths for known helper modules.
- Status: Open

## FIND-07 GitHub Credentials Persist In Local Publish And Validation Contexts

- Severity: Medium
- CWE: CWE-798 Use of Hard-coded Credentials
- OWASP: A04 Cryptographic Failures, A09 Security Logging and Alerting Failures
- Affected Components: Human Maintainer, Publish Automation
- Related Threats: HM-T2-02, PA-T2-01
- Evidence: Publish helpers intentionally probe `GH_TOKEN`, `GITHUB_TOKEN`, then `gh auth`; the selected credential remains available to the running process for the full script lifetime.
- Impact: Local shell or process compromise can recover valid GitHub credentials from active publish/validation sessions.
- Remediation: Use the shortest-lived credential source possible, avoid verbose token-adjacent output, and clear sensitive environment variables when a flow finishes.
- Status: Open

## FIND-08 Publish Automation Trusts Local Remotes And Credentials Too Broadly

- Severity: High
- CWE: CWE-829 Inclusion of Functionality from Untrusted Control Sphere
- OWASP: A01 Broken Access Control, A06 Insecure Design
- Affected Components: Publish Automation, GitHub Platform
- Related Threats: PA-T2-02, PA-T2-03, GHP-T2-02
- Evidence: Wiki and release scripts trust locally resolved repo metadata, remotes, and available credentials before mutating remote GitHub state.
- Impact: A manipulated checkout or mistaken operator context can publish to an unintended repository or with unintended authority.
- Remediation: Pin expected owner/repo targets, surface them explicitly in preflight output, and require operator confirmation or peer approval for remote mutations.
- Status: Open

## FIND-09 No Sandboxing For Subprocess And CLI Execution

- Severity: Medium
- CWE: CWE-250 Execution with Unnecessary Privileges
- OWASP: A06 Insecure Design
- Affected Components: Agent Dispatch, Red Team Runner
- Related Threats: RTR-T2-02
- Evidence: Local CLIs and validation subprocesses run with the current shell/user privileges and direct access to the repo checkout.
- Impact: Any malicious or unexpectedly expensive helper behavior executes with full local repo authority.
- Remediation: Reduce trust in local helpers, scope runtime permissions where practical, and keep subprocess inputs narrow and explicit.
- Status: Open

## FIND-10 Generated Reports And Evidence Can Retain Sensitive Operational Context

- Severity: Medium
- CWE: CWE-200 Exposure of Sensitive Information to an Unauthorized Actor
- OWASP: A09 Security Logging and Alerting Failures
- Affected Components: Git Worktree
- Related Threats: GW-T3-01
- Evidence: Threat-model outputs, evidence files, and artifacts remain in the worktree unless explicitly cleaned up.
- Impact: Local host compromise or accidental sharing can expose workflow assumptions, repo topology, and operational context beyond the intended review window.
- Remediation: Add retention guidance, minimize sensitive details in generated files, and clean ephemeral outputs when they are no longer needed.
- Status: Open

## FIND-11 Repo-Local Secrets Regression Scan Now Closes A Prior Blind Spot

- Severity: Medium
- CWE: CWE-798 Use of Hard-coded Credentials
- OWASP: A02 Security Misconfiguration, A04 Cryptographic Failures
- Affected Components: Git Worktree
- Related Threats: GW-T2-01
- Evidence: `security-scan.yml` now runs `python artifacts/scripts/repo_security_scan.py secrets --root .`, and the scanner filters placeholders while flagging high-confidence credential patterns.
- Impact: Newly committed credential-like strings are much less likely to land unnoticed in root or template files.
- Remediation: Keep the scan mandatory and expand patterns carefully as real false negatives are discovered.
- Status: Mitigated

## FIND-12 Focused Static Regression Scan Now Closes A Prior Workflow Blind Spot

- Severity: Medium
- CWE: CWE-250 Execution with Unnecessary Privileges
- OWASP: A02 Security Misconfiguration, A06 Insecure Design
- Affected Components: Git Worktree
- Related Threats: GW-T2-02
- Evidence: `security-scan.yml` now runs `python artifacts/scripts/repo_security_scan.py static --root .`, blocking unpinned actions, `persist-credentials: true`, `pull_request_target`, `shell=True`, `Invoke-Expression`, and obvious secret logging.
- Impact: High-frequency workflow and script foot-guns become CI-visible regressions instead of review-time guesswork.
- Remediation: Keep the rule set narrow and high-signal; extend only when a new control-plane regression pattern becomes common.
- Status: Mitigated