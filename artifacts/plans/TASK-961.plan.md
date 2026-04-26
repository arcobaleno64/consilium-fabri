# Plan: TASK-961

## Metadata
- Task ID: TASK-961
- Artifact Type: plan
- Owner: Claude
- Status: ready
- Last Updated: 2026-04-14T23:50:00+08:00
- PDCA Stage: P

## Scope

建立 `artifacts/scripts/discover_templates.py` 腳本，提供 CLI 與 Python importable 介面，讓 orchestrator 可按 agent type 與 workflow stage 自動掃描 `docs/templates/` 並回傳匹配的 template 清單。同步更新文件與 template/ 目錄。

## Files Likely Affected

| 檔案 | 操作 |
|------|------|
| `artifacts/scripts/discover_templates.py` | 新增 |
| `AGENTS.md` | 更新（文件模組表加入腳本說明） |
| `docs/orchestration.md` | 更新（Stage 4 加入 discovery 使用說明） |
| `template/artifacts/scripts/discover_templates.py` | 新增（sync） |
| `template/AGENTS.md` | 更新（sync） |
| `template/docs/orchestration.md` | 更新（sync） |

## Proposed Changes

### P1: discover_templates.py 腳本

遵循 `artifacts/scripts/` 現有模式：

```python
#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import yaml
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import List, Optional

TEMPLATES_DIR = Path("docs/templates")

@dataclass
class TemplateInfo:
    name: str
    description: str
    version: str
    applicable_agents: list[str]
    applicable_stages: list[str]
    prerequisites: list[str]
    path: str

def parse_frontmatter(md_path: Path) -> dict:
    content = md_path.read_text(encoding="utf-8")
    parts = content.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}

def discover(
    agent: Optional[str] = None,
    stage: Optional[str] = None,
    templates_dir: Path = TEMPLATES_DIR,
) -> List[TemplateInfo]:
    results = []
    for template_md in sorted(templates_dir.glob("*/TEMPLATE.md")):
        fm = parse_frontmatter(template_md)
        if not fm.get("name"):
            continue
        # Agent filter
        if agent:
            agents = [a.lower() for a in fm.get("applicable_agents", [])]
            if agent.lower() not in agents:
                continue
        # Stage filter
        if stage:
            stages = [s.lower() for s in fm.get("applicable_stages", [])]
            if stage.lower() not in stages and "any" not in stages:
                continue
        results.append(TemplateInfo(
            name=fm["name"],
            description=fm.get("description", ""),
            version=fm.get("version", ""),
            applicable_agents=fm.get("applicable_agents", []),
            applicable_stages=fm.get("applicable_stages", []),
            prerequisites=fm.get("prerequisites", []),
            path=str(template_md),
        ))
    return results

def main():
    parser = argparse.ArgumentParser(description="Discover subagent templates")
    parser.add_argument("--agent", help="Filter by agent (e.g. 'Codex CLI')")
    parser.add_argument("--stage", help="Filter by stage (e.g. 'coding')")
    parser.add_argument("--templates-dir", default=str(TEMPLATES_DIR))
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    
    results = discover(args.agent, args.stage, Path(args.templates_dir))
    
    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        for r in results:
            print(f"  {r.name} ({r.path})")
            print(f"    agents: {', '.join(r.applicable_agents)}")
            print(f"    stages: {', '.join(r.applicable_stages)}")

if __name__ == "__main__":
    main()
```

### P2: AGENTS.md 更新

文件模組表新增：
```
| `artifacts/scripts/discover_templates.py` | Template auto-discovery CLI | 200 | 派發 subagent 前 |
```

### P3: docs/orchestration.md 更新

在 Stage 4（Coding）區段加入 discovery 使用說明：
- 派發 subagent 前，可執行 `python artifacts/scripts/discover_templates.py --agent "Codex CLI" --stage coding` 查詢可用 templates

### P4: Template sync

同步 root → template/（腳本複製、文件更新泛化）

## Risks

R1
- Risk: PyYAML 在某些環境未安裝，腳本 import 失敗
- Trigger: 在全新 clone 環境執行腳本
- Detection: `ImportError: No module named 'yaml'` 錯誤訊息
- Mitigation: 在腳本開頭加入 try/except import with 清楚錯誤提示 `pip install pyyaml`；或改用純 string split 解析（frontmatter 結構簡單足以支撐）
- Severity: non-blocking

R2
- Risk: TEMPLATE.md frontmatter 格式不一致導致解析失敗（如缺少 `---` 分隔符）
- Trigger: 未來新增 template 時未遵循格式
- Detection: `parse_frontmatter()` 回傳空 dict，template 不出現在 discovery 結果中
- Mitigation: 腳本對 parse 失敗的檔案印出 warning 而非 crash；guard 驗證可在未來擴充
- Severity: non-blocking

R3
- Risk: discover_templates.py 輸出被 orchestrator 直接信任用於 dispatch 決策，若 frontmatter 中 applicable_agents 值拼寫不一致（如 "codex cli" vs "Codex CLI"），導致遺漏或多派 template
- Trigger: 新增 TEMPLATE.md 時 applicable_agents 值使用與既有 templates 不同的大小寫或全形空格
- Detection: `--agent "Codex CLI"` 過濾結果與預期不符（template 數量不一致）
- Mitigation: 在 discover() 函數中對 agent name 做 case-insensitive 比對（已在 P1 設計中以 `.lower()` 實作）；若未來出現其他變體，在 TEMPLATE.md schema 中定義 enum 約束
- Severity: blocking

## Validation Strategy

1. **基本功能測試**：`python artifacts/scripts/discover_templates.py` 無參數 → 列出全部 6 個 templates
2. **Agent 過濾**：`--agent "Codex CLI"` → 只列出 Codex CLI 適用的 templates
3. **Stage 過濾**：`--stage coding` → 只列出 coding 階段的 templates
4. **組合過濾**：`--agent "Codex CLI" --stage verifying` → 只列出 reviewer + verifier
5. **JSON 輸出**：`--json` → 合法 JSON 且包含所有欄位
6. **Wildcard 測試**：blocking template（stage: any）在任何 stage 過濾下都出現
7. **Template sync**：`diff` 比對 root vs template/ 腳本一致

## Out of Scope

- Config 變數注入
- Hot-reload 或 watch 機制
- GUI 或互動介面
- 與 guard_status_validator.py 整合

## Ready For Coding

yes
