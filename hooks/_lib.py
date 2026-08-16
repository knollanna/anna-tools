#!/usr/bin/env python3
"""Shared helpers for anna-tools hooks.

Two roots, and the distinction matters once this ships as a plugin:

- **plugin root** — where `rules/` live. When Claude Code installs a plugin from a
  marketplace it may copy the directory into a cache, so this is whatever
  `CLAUDE_PLUGIN_ROOT` says, falling back to this file's parent.
- **data home** — where Anna's own content lives (`projects.json`, `resume/`, `job/`).
  That never moves to a cache. Resolved from `ANNA_TOOLS_HOME`, then the known
  checkout, then the plugin root.

Collapsing the two would mean a cached plugin silently stops finding the job
pipeline, and the failure would be invisible — the hook would just go quiet.

Every helper here fails soft. A hook that raises is a hook that breaks a session.
"""

import json
import os
import sys
from pathlib import Path

FALLBACK_HOME = Path.home() / "Documents" / "Claude" / "Projects" / "anna-tools"


def plugin_root() -> Path:
    env = os.environ.get("CLAUDE_PLUGIN_ROOT")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p
    return Path(__file__).resolve().parent.parent


def data_home() -> Path:
    """Where Anna's content lives. May differ from plugin_root() when cached."""
    env = os.environ.get("ANNA_TOOLS_HOME")
    if env:
        p = Path(env).expanduser()
        if p.is_dir():
            return p
    if (FALLBACK_HOME / "projects.json").exists():
        return FALLBACK_HOME
    return plugin_root()


def payload() -> dict:
    try:
        data = json.load(sys.stdin)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def projects() -> list[dict]:
    path = data_home() / "projects.json"
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("projects", [])
    except Exception:
        return []


def project_for(cwd: str) -> dict | None:
    """Match a working directory to a catalog entry by longest path suffix."""
    if not cwd:
        return None
    try:
        here = Path(cwd).resolve()
    except Exception:
        return None
    parts = {p.name for p in [here, *here.parents]}
    best = None
    for entry in projects():
        name = Path(entry.get("path", "")).name or entry.get("name", "")
        if name and name in parts:
            if best is None or len(name) > len(
                Path(best.get("path", "")).name or best.get("name", "")
            ):
                best = entry
    return best


def emit(event: str, text: str) -> None:
    """Inject additional context for this event. Silent when there's nothing to say."""
    if not text.strip():
        return
    print(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": event,
                    "additionalContext": text,
                }
            }
        )
    )
