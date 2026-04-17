# Research: TASK-963

## Metadata
- Task ID: TASK-963
- Artifact Type: research
- Owner: Claude (acting as research agent)
- Status: ready
- Last Updated: 2026-04-16T21:51:20+08:00

## Research Questions

1. GitHub Actions supply-chain 風險下降時，SHA pinning 與 Dependabot 各自解決什麼問題？是否應該二選一？
2. 目前 repo 適合先加 pip-audit 還是 CodeQL？兩者的可行性與限制是什麼？
3. Wiki / Release 發布流程有哪些 GitHub 官方定義的初始化與權限前提？哪些部分可完全腳本化，哪些不能？

## Confirmed Facts

- 目前 repo 的主 workflow [`.github/workflows/workflow-guards.yml`](https://github.com/arcobaleno64/consilium-fabri/blob/master/.github/workflows/workflow-guards.yml) 只使用 `actions/checkout@v4` 與 `actions/setup-python@v5` 這兩個 tag-based action reference，尚未使用 full commit SHA；repo 內也沒有 `.github/dependabot.yml`。（source: [.github/workflows/workflow-guards.yml](https://github.com/arcobaleno64/consilium-fabri/blob/master/.github/workflows/workflow-guards.yml)；repo tree inspection）
- GitHub 官方 security hardening 文件明確指出：將第三方 action pin 到 full-length commit SHA 是「目前唯一」能把 action 當成 immutable release 使用的方式；pin tag 雖常見，但 tag 可被移動或刪除，因此安全性較差。（source: https://docs.github.com/en/actions/reference/security/secure-use#using-third-party-actions）
- GitHub 同一份文件也明確建議用 Dependabot 維護 actions 與 reusable workflows 的版本；Dependabot version updates 可以更新 GitHub repository syntax 的 action reference，包含 commit-SHA 形式，但 Dependabot alerts 不會為 pinned-to-SHA 的 action 產生 vulnerability alerts。（source: https://docs.github.com/en/actions/reference/security/secure-use#keeping-the-actions-in-your-workflows-secure-and-up-to-date ; https://docs.github.com/en/actions/reference/security/secure-use#being-aware-of-security-vulnerabilities-in-actions-you-use）
- CodeQL 支援 Python 與 GitHub Actions workflows 掃描；在 GitHub.com 上 public repositories 可直接使用，但 private repositories 需要 organization-owned repo 且啟用 GitHub Code Security / GHAS 類能力，因此 CodeQL 的可行性取決於 repo 類型與授權，不是純 repo-local 決策。（source: https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning-with-codeql）
- pip-audit 有官方 GitHub Action，也可以直接在 CI 內安裝 CLI 執行；它會掃描 Python environment 或 requirements file，發現已知漏洞時 exit code 為 `1`。本 repo 的 [requirements.txt](https://github.com/arcobaleno64/consilium-fabri/blob/master/requirements.txt) 目前只有 `PyYAML>=6.0,<7.0`，代表 pip-audit 在本 repo 的初始覆蓋面較小，但選型不受 GitHub entitlement 影響，落地成本低且結果可重跑。（source: https://github.com/pypa/pip-audit ; [requirements.txt](https://github.com/arcobaleno64/consilium-fabri/blob/master/requirements.txt)）
- 現有 [artifacts/scripts/push-wiki.ps1](https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/push-wiki.ps1) 直接把「先在網頁建立第一頁 wiki」視為先決條件；GitHub 官方 wiki 文件也明確寫到「Once you've created an initial page on GitHub, you can clone the repository locally」，表示官方保證的本地 git 路徑是建立第一頁之後，而不是從不存在的 wiki remote 自動 bootstrap。（source: [artifacts/scripts/push-wiki.ps1](https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/push-wiki.ps1) ; https://docs.github.com/en/communities/documenting-your-project-with-wikis/adding-or-editing-wiki-pages#adding-or-editing-wiki-pages-locally）
- GitHub 官方 release 文件指出：有 write access 的 collaborator 可以建立、編輯、刪除 release，且 Releases API 可用於腳本化建立 / 修改 / 刪除 release。這表示 release 發布流程可以被可靠地整理成 preflight + publish 腳本，只要 auth 與 tag 狀態被顯式檢查。（source: https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository）

## Relevant References

| 來源 | 路徑 / 說明 |
|---|---|
| Current workflow | [`.github/workflows/workflow-guards.yml`](https://github.com/arcobaleno64/consilium-fabri/blob/master/.github/workflows/workflow-guards.yml) |
| Current wiki push script | [artifacts/scripts/push-wiki.ps1](https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/push-wiki.ps1) |
| Current Python dependency surface | [requirements.txt](https://github.com/arcobaleno64/consilium-fabri/blob/master/requirements.txt) |
| GitHub Actions secure use | https://docs.github.com/en/actions/reference/security/secure-use |
| CodeQL availability and language support | https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning-with-codeql |
| GitHub wiki local editing flow | https://docs.github.com/en/communities/documenting-your-project-with-wikis/adding-or-editing-wiki-pages |
| GitHub release management | https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository |
| pip-audit | https://github.com/pypa/pip-audit |

## Uncertain Items

- UNVERIFIED: `consilium-fabri` 目前在 GitHub.com 上的實際 code scanning entitlement 狀態；CodeQL 對 public repo 保證可用，但若後續在 private mirror 或不同 owner 下重用 workflow，仍可能需要額外授權確認。
- UNVERIFIED: GitHub 是否允許透過未公開或未保證的 git/HTTP 行為，在沒有第一頁的情況下自動建立 wiki remote；目前官方文件沒有提供這種保證，因此實作不應依賴它。

## Constraints For Implementation

1. **SHA pinning 與更新機制應視為互補，不是互斥**：full SHA pinning 解決 immutability，Dependabot 解決更新維護；若只能先做一件，優先順序應是 pinning。
2. **獨立掃描需先選擇 entitlement-neutral baseline**：在未確認 repo 類型或 GHAS 授權前，pip-audit 比 CodeQL 更適合作為第一條必落地的獨立掃描；CodeQL 可列為後續加強。
3. **Wiki bootstrap 必須顯式建模成 failure path**：腳本不能把 wiki 未初始化當成一般 git 失敗；應該在 preflight 就識別並給出明確 remediation。
4. **Release 與 Wiki 的 auth probe 需要統一**：環境變數 `GITHUB_TOKEN` / `GH_TOKEN` 與 `gh auth` 的 fallback 順序、scope / permission 說明與錯誤訊息必須一致，不能分散在多支腳本各自實作。

## Sources

[1] GitHub. "Secure use reference." https://docs.github.com/en/actions/reference/security/secure-use (2026-04-16 retrieved)
[2] GitHub. "About code scanning with CodeQL." https://docs.github.com/en/code-security/code-scanning/introduction-to-code-scanning/about-code-scanning-with-codeql (2026-04-16 retrieved)
[3] GitHub. "Adding or editing wiki pages." https://docs.github.com/en/communities/documenting-your-project-with-wikis/adding-or-editing-wiki-pages (2026-04-16 retrieved)
[4] GitHub. "Managing releases in a repository." https://docs.github.com/en/repositories/releasing-projects-on-github/managing-releases-in-a-repository (2026-04-16 retrieved)
[5] PyPA. "pip-audit." https://github.com/pypa/pip-audit (2026-04-16 retrieved)
[6] Consilium Fabri. "Workflow Guards workflow." https://github.com/arcobaleno64/consilium-fabri/blob/master/.github/workflows/workflow-guards.yml (2026-04-16 retrieved)
[7] Consilium Fabri. "push-wiki.ps1." https://github.com/arcobaleno64/consilium-fabri/blob/master/artifacts/scripts/push-wiki.ps1 (2026-04-16 retrieved)
[8] Consilium Fabri. "requirements.txt." https://github.com/arcobaleno64/consilium-fabri/blob/master/requirements.txt (2026-04-16 retrieved)