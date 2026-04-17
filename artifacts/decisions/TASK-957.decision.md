# Decision Log: TASK-957

## Metadata

- Task ID: TASK-957
- Artifact Type: decision
- Owner: Claude
- Status: done
- Last Updated: 2026-04-13T14:40:02+08:00

## Issue

provider-backed PR diff evidence 的第一版要選哪一種 GitHub 來源格式，才能最小化 parser 複雜度、保留可測試性，且足夠拿來做 scope drift guard。

## Options Considered

- 使用 PR 的 `.diff` 或 `.patch` URL，自己解析 unified diff 取出 file list
- 使用 `GET /repos/{owner}/{repo}/pulls/{pull_number}/files`，直接讀取 JSON response 的 `filename`
- 使用 compare API 或 merge commit metadata 推導 changed files

## Chosen Option

採用 GitHub PR files endpoint，將新 evidence type 定義為 `github-pr`，並保留可覆蓋的 `API Base URL` 以支援本地 fixture 與 GHES 類環境。

## Reasoning

PR files endpoint 已直接回傳結構化 `filename`，避免 diff parser 與 patch corner cases；它也自然支援 pagination，適合在 guard 中實作 deterministic file-list reconstruction。相較之下，`.diff` / `.patch` parser 太脆弱，而 compare API 更偏 branch/commit compare，不如 PR files 直接對應 provider-backed PR evidence 的語意。

## Implications

- `guard_status_validator.py` 需要新增 GitHub API fetch path、pagination、auth header 與錯誤回報
- red-team static suite 需要提供本地假 GitHub API server，避免把測例綁到真實網路
- schema 與 prompt regression 需要鎖住 `github-pr` evidence contract，避免只改 code 不改文件

## Follow Up

- 先做 `github-pr` evidence 與本地 fake provider drill
- 讓 backlog 將 provider gap 從「未支援」更新為「已支援 GitHub，其他 provider 尚未支援」
- 之後若要支援 GitLab / Azure，再用新的 decision artifact 做 provider matrix 取捨