#!/usr/bin/env python3
"""Validate the AgentOps template without changing project files."""
from __future__ import annotations

import sys
from pathlib import Path
import tomllib

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "AGENTS.md",
    "README.md",
    ".codex/config.toml",
    ".agents/skills/agentops/SKILL.md",
    ".agents/skills/agentops/agents/openai.yaml",
    "docs/agentops/PROJECT.md",
    "docs/agentops/RESEARCH.md",
    "docs/agentops/REQUIREMENTS.md",
    "docs/agentops/ARCHITECTURE.md",
    "docs/agentops/TASKS.md",
    "docs/agentops/STATE.md",
    "docs/agentops/DECISIONS.md",
    "docs/agentops/EVIDENCE.md",
    "docs/agentops/OPEN_SOURCE.md",
    "docs/agentops/GITHUB_WORKFLOW.md",
    ".github/workflows/agentops-ci.yml",
    ".github/pull_request_template.md",
    "start-agentops.cmd",
    "new-agentops-project.cmd",
]
AGENT_FILES = [
    "orchestrator.toml",
    "market-manager.toml",
    "requirements-analyst.toml",
    "architect.toml",
    "coder.toml",
    "tester.toml",
]
REQUIRED_AGENT_FIELDS = ("name", "description", "developer_instructions")


def fail(message: str, errors: list[str]) -> None:
    errors.append(message)


def main() -> int:
    errors: list[str] = []

    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            fail(f"missing file: {relative}", errors)

    agent_dir = ROOT / ".codex" / "agents"
    for filename in AGENT_FILES:
        path = agent_dir / filename
        if not path.is_file():
            fail(f"missing agent: {filename}", errors)
            continue
        try:
            with path.open("rb") as handle:
                data = tomllib.load(handle)
        except Exception as exc:  # pragma: no cover - validation path
            fail(f"invalid TOML: {filename}: {exc}", errors)
            continue
        for field in REQUIRED_AGENT_FIELDS:
            value = data.get(field)
            if not isinstance(value, str) or not value.strip():
                fail(f"{filename}: missing or empty {field}", errors)

    skill = ROOT / ".agents" / "skills" / "agentops" / "SKILL.md"
    if skill.is_file():
        text = skill.read_text(encoding="utf-8")
        if not text.startswith("---\n"):
            fail("skill frontmatter must start on the first line", errors)
        if "name: agentops" not in text:
            fail("skill frontmatter must declare name: agentops", errors)
        if "description:" not in text:
            fail("skill frontmatter must declare description", errors)
        if "[TODO" in text or "TODO:" in text:
            fail("skill contains an unfinished TODO", errors)

    if errors:
        print("AgentOps validation failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print(f"AgentOps validation passed: {len(REQUIRED_FILES)} files, {len(AGENT_FILES)} agents.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())