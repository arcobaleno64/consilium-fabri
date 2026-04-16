# Decision Log: TASK-958

## Metadata

- Task ID: TASK-958
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-13T14:40:02+08:00

## Issue

git object retention / archive policy 的第一版要採哪種 archive 形式，才能在本輪最小成本下保住 scope drift reconstruction，而不把 workflow 拉進更重的 git plumbing。

## Options Considered

- 使用 `git bundle` 或完整 patch archive，嘗試保留可還原的 git objects / patch
- 使用純文字 changed-files archive，內容只保存 normalized file list，並以 SHA256 驗證
- 只寫文件 policy，不實作 guard fallback

## Chosen Option

採用純文字 changed-files archive 作為第一版 archive fallback，並在文件中明文化它是當 local git objects retention 不足時的備援路徑。

## Reasoning

status guard 目前只需要重建 changed files 來做 scope drift 審計，不需要完整 patch 或 tree objects。用純文字 archive 能用最少的格式、最少的 tooling 成本達成 fallback，而且 red-team 可在 temp fixture 中穩定重跑。`git bundle` 雖然更接近真實 objects retention，但需要額外 git plumbing 與 restore 流程，會讓這一輪超出最小增量。

## Implications

- `## Diff Evidence` schema 需要新增 archive metadata 欄位
- status guard 需要在 commit-range replay 失敗時嘗試 archive fallback，而不是直接放棄
- 文件需要明確定義 archive file format，避免不同 agent 用不同格式寫出不可驗證的 archive

## Follow Up

- 先實作 archive metadata 驗證與 fallback
- 將 backlog 的 object retention gap 從「沒有 policy」更新為「有 archive fallback，但尚未保留完整 patch/object bundle」
- 若日後需要完整 git-level restore，再以新的 decision artifact 評估 bundle/patch 路徑