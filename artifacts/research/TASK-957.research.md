# Research: TASK-957

## Metadata

- Task ID: TASK-957
- Artifact Type: research
- Owner: Gemini
- Status: ready
- Last Updated: 2026-04-13T14:40:02+08:00

## Research Questions

- GitHub 哪個 REST endpoint 最適合 provider-backed PR diff evidence，只取 changed files 而非整份 patch？
- public/private repo 的認證與權限邊界是什麼？
- pagination 與 response shape 對 guard 實作有什麼最小需求？

## Confirmed Facts

- GitHub 提供 `GET /repos/{owner}/{repo}/pulls/{pull_number}/files`，專門列出 pull request 的 files；response item 直接包含 `filename` 欄位，適合拿來重建 changed files，而不需要自己解析 diff patch。（source: https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files）
- GitHub 的 PR files endpoint 支援 pagination，`per_page` 最大 100，預設 30；整體回應最多 3000 files，因此 guard 必須至少支援逐頁抓取直到空頁或不足一頁。（source: https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files）
- GitHub 文件明確指出：public resources 可不帶認證讀取；private repo 則需要具備 `Pull requests` read permission 的 fine-grained token、App token 或安裝 token，因此本 repo 的 guard 不能假設一定有 token，但必須在需要時支援 `GITHUB_TOKEN` / `GH_TOKEN`。（source: https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files）
- `TASK-956` 的 verify 已確認目前 residual gap 包含 provider-backed PR diff evidence，表示本輪補強屬於既有 backlog 的直接延伸，而不是新增 unrelated scope。（source: `artifacts/verify/TASK-956.verify.md`）
- `docs/red_team_backlog.md` 目前將 provider-backed PR diff evidence 與 object retention / archive policy 並列為 `BKL-001` 的下一輪補強，代表實作時需要同步更新 backlog 的殘餘風險描述。（source: `docs/red_team_backlog.md`）

## Relevant References

- GitHub REST API: List pull request files
  - https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files
- Current backlog gap
  - `docs/red_team_backlog.md`
- Current verification gap summary
  - `artifacts/verify/TASK-956.verify.md`

## Uncertain Items

- UNVERIFIED: GitHub Enterprise Server 的最佳 `API Base URL` 慣例是否統一為 `/api/v3`，本輪會設計成可覆蓋的 `API Base URL` 欄位來避免硬編碼，但不另外研究各版本 GHES 差異。

## Constraints For Implementation

- provider-backed evidence 應優先使用結構化 JSON API，而不是解析 `.diff` 或 `.patch` 文本
- runner 的 static case 必須能在本地假 server 下重跑，不能依賴真實 GitHub repo 或網路連線
- private repo auth failure、404、403 / rate-limit 必須回報成明確 validator 錯誤，不可默默回退為 artifact-only

## Sources

[1] GitHub. "List pull request files." https://docs.github.com/en/rest/pulls/pulls?apiVersion=2022-11-28#list-pull-requests-files (2026-04-13 retrieved)
[2] Consilium Fabri. "TASK-956 Verify Artifact." https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/verify/TASK-956.verify.md (2026-04-13 retrieved)
[3] Consilium Fabri. "Red Team Backlog." https://github.com/arcobaleno64/consilium-fabri/blob/master/docs/red_team_backlog.md (2026-04-13 retrieved)
