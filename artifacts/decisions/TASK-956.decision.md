# Decision Log: TASK-956

## Metadata

- Task ID: TASK-956
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-13T14:14:56+08:00

## Issue

Residual risk 目前集中在 historical diff evidence 的可追溯強度：是要先接 provider-based PR diff，還是先把現有 repo-local `commit-range` evidence 做到更強的 pinning 與 integrity 驗證。

## Options Considered

- 直接接入 PR diff evidence，讓歷史 diff reconstruction 能依賴 provider-backed PR 資訊
- 保留 repo-local `commit-range` 路徑，但加入 immutable commit pinning、changed-files snapshot 與 checksum 驗證
- 維持現況，只在 backlog 中保留 refs retention 風險

## Chosen Option

保留 repo-local `commit-range` 路徑，並加入 immutable commit pinning、changed-files snapshot 與 checksum 驗證。

## Reasoning

這條路徑不需要外部認證或 provider API，能在本 repo 與 red-team fixture 中穩定重放；同時它直接對準目前最可操作的殘餘風險，也就是 refs 可變與 artifact evidence 自身可被漂移。PR diff evidence 的確能再往前一步，但會立刻把整個 guard 拉進 provider 相依、網路可用性與 token 管理，對這一輪的風險收斂不是最小增量。

## Implications

- `## Diff Evidence` schema 需要擴充 pinned commit 與 snapshot checksum 欄位
- status guard 需要驗證 replayed diff 與 snapshot 之間的一致性
- red-team 需要新增 evidence corruption 案例，而不只是單純未宣告 drift
- backlog 的殘餘風險描述要更新成「objects retention / provider gap」，而不是單純 refs 漂移

## Follow Up

- 先實作 immutable commit pinning 與 snapshot checksum
- 用新的 static drill 驗證 evidence corruption 會被直接攔下
- PR diff evidence 保留為後續選項，等 repo-local evidence 收斂完成後再評估