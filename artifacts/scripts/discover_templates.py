#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import List, Optional

try:
    import yaml
except ImportError:
    print(
        "ERROR: PyYAML is required but not installed.\n"
        "Install it with: pip install pyyaml",
        file=sys.stderr,
    )
    sys.exit(1)

__version__ = "1.0.0"

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
    """Parse YAML frontmatter from a Markdown file delimited by --- fences."""
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
    """Scan templates_dir/*/TEMPLATE.md and return matching TemplateInfo list."""
    results: List[TemplateInfo] = []
    for template_md in sorted(templates_dir.glob("*/TEMPLATE.md")):
        fm = parse_frontmatter(template_md)
        if not fm.get("name"):
            continue
        # Agent filter
        if agent:
            agents = [a.lower() for a in fm.get("applicable_agents", [])]
            if agent.lower() not in agents:
                continue
        # Stage filter (respect 'any' as wildcard)
        if stage:
            stages = [s.lower() for s in fm.get("applicable_stages", [])]
            if stage.lower() not in stages and "any" not in stages:
                continue
        results.append(
            TemplateInfo(
                name=fm["name"],
                description=fm.get("description", ""),
                version=fm.get("version", ""),
                applicable_agents=fm.get("applicable_agents", []),
                applicable_stages=fm.get("applicable_stages", []),
                prerequisites=fm.get("prerequisites", []),
                path=str(template_md),
            )
        )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Discover subagent templates by agent and/or stage"
    )
    parser.add_argument("--agent", help="Filter by agent (e.g. 'Codex CLI')")
    parser.add_argument("--stage", help="Filter by stage (e.g. 'coding')")
    parser.add_argument("--templates-dir", default=str(TEMPLATES_DIR))
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    results = discover(args.agent, args.stage, Path(args.templates_dir))

    if args.json:
        print(json.dumps([asdict(r) for r in results], indent=2))
    else:
        if not results:
            print("No matching templates found.")
        else:
            for r in results:
                print(f"  {r.name} ({r.path})")
                print(f"    agents: {', '.join(r.applicable_agents)}")
                print(f"    stages: {', '.join(r.applicable_stages)}")


if __name__ == "__main__":
    main()
