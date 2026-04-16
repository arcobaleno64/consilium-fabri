# Decision Log: TASK-955

## Metadata

- Task ID: TASK-955
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-13T13:55:35+08:00

## Issue

本輪要在 historical diff reconstruction 與 scope-drift waiver 之間補上可執行的治理機制，但需要先決定 evidence 形式與 waiver 的結構化方式。

## Options Considered

- 直接整合 PR diff evidence，依賴 GitHub / `gh` 或外部 API 回放已提交 task 的變更範圍
- 在 code artifact 增加 `commit-range` snapshot 型的 `## Diff Evidence`，並讓 status guard 在 clean worktree 時直接重放 `git diff --name-only <base>..<head>`
- 維持 dirty-worktree heuristic，不新增 historical evidence，只在文件中保留 backlog

## Chosen Option

採用 `commit-range` snapshot 作為第一版 historical diff evidence，並把 `--allow-scope-drift` 的例外收斂為必須附 decision artifact 的結構化 guard waiver。

## Reasoning

`commit-range` snapshot 只依賴 repo-local git 物件，無需外部憑證、PR 編號或網路存取，最容易在本 repo 與 temp fixture 中穩定重放。相較之下，PR diff evidence 牽涉遠端 provider、授權與 API 可用性，適合作為下一輪補強而不是這一輪的最小可行 hardening。另一方面，若 `--allow-scope-drift` 只是單純降級 warning，例外會停留在口頭或命令列層級；把它綁到 decision artifact 的結構化 waiver，才有可審計的邊界。

## Implications

- code artifact schema 需要新增可選的 `## Diff Evidence` 契約，至少定義 `commit-range` 的欄位
- decision artifact schema 需要新增可選但可機器判讀的 waiver 區段，讓 `--allow-scope-drift` 能驗證是否有顯式豁免
- `guard_status_validator.py` 需要在 dirty-worktree heuristic 之外，再補一條 clean-task 的 historical diff replay 路徑
- red-team 與 prompt regression 都要同步覆蓋新 contract，避免文件與 guard 漂移

## Follow Up

- 先實作 `commit-range` snapshot replay 與 decision-gated waiver
- 將 PR diff evidence 保留在 backlog 作為下一輪補強選項
- 若後續要支援 provider-backed PR diff，再建立新的 decision artifact 說明取捨
