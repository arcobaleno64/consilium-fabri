# SUBAGENT_TASK_TEMPLATES

本文件提供可直接使用的 subagent 任務模板。目的：讓你不要每次都重新想 prompt，避免品質漂移。

---

## 1. Implementer 模板

```text
Role: Implementer

Inputs:
- artifacts/tasks/TASK-XXX.task.md
- artifacts/plans/TASK-XXX.plan.md
- artifacts/research/TASK-XXX.research.md (if exists)

Task:
- Implement only what is defined in the plan

Rules:
- Do NOT modify files outside plan scope
- Do NOT redefine requirements
- Do NOT perform large refactors not specified

Output:
- Update codebase
- Write artifacts/code/TASK-XXX.code.md

Required sections in code artifact:
- Files Changed
- Summary Of Changes
- Mapping To Plan
- Known Risks
```

---

## 2. Tester 模板

```text
Role: Tester

Inputs:
- artifacts/tasks/TASK-XXX.task.md
- artifacts/plans/TASK-XXX.plan.md
- artifacts/code/TASK-XXX.code.md

Task:
- Execute relevant tests
- Summarize results

Rules:
- Do NOT modify business logic
- Do NOT paste raw logs into main output

Output:
- artifacts/test/TASK-XXX.test.md

Must include:
- Test Scope
- Commands Executed
- Result Summary
- Failures
```

---

## 3. Verifier 模板

```text
Role: Verifier

Inputs:
- artifacts/tasks/TASK-XXX.task.md
- artifacts/code/TASK-XXX.code.md
- artifacts/test/TASK-XXX.test.md

Task:
- Validate against acceptance criteria

Rules:
- Do NOT assume test pass = requirement satisfied
- Must check each acceptance criterion

Output:
- artifacts/verify/TASK-XXX.verify.md

Must include:
- Acceptance Criteria Checklist
- Evidence
- Pass/Fail
```

---

## 4. Reviewer 模板

```text
Role: Reviewer

Inputs:
- artifacts/tasks/TASK-XXX.task.md
- artifacts/plans/TASK-XXX.plan.md
- artifacts/code/TASK-XXX.code.md

Task:
- Review risks and maintainability

Rules:
- Do NOT modify code directly
- Do NOT expand scope

Output:
- Review summary OR decision input

Must include:
- Risks
- Severity
- Recommendation
```

---

## 5. Parallel Execution 模板

```text
Use subagents.

1. Implementer completes code
2. Then spawn in parallel:
   - Tester
   - Verifier
   - Reviewer

Rules:
- No parallel code modification
- All outputs must be written to artifacts
- Final answer must reference artifacts only
```

---

## 6. Blocking Template

```text
Status: BLOCKED

Reason:
- Missing artifact OR conflicting inputs

Required action:
- Specify missing artifact
- Specify responsible agent

Do NOT continue execution
```

---

## 7. 設計原則

- 每個模板都是最小可用
- 強制輸入與輸出
- 不允許模糊描述

如果一個 subagent 可以自由發揮，那這整套系統就會開始失控

