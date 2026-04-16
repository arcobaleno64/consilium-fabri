"""Shared constants for workflow guard scripts."""
from __future__ import annotations

import re

REQUIRED_TOPICS = {
    "multi-agent",
    "developer-tools",
    "workflow-template",
    "artifact-first",
    "gate-guarded",
    "premortem",
}

TOPIC_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
