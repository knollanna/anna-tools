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


def known_profiles() -> dict:
    """Valid archetype names. Empty dict means validation is unavailable, not that
    nothing is valid — callers must not warn on an empty registry."""
    try:
        path = data_home() / "profiles.json"
        return json.loads(path.read_text(encoding="utf-8")).get("profiles", {})
    except Exception:
        return {}


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


SKIP_DIRS = {
    ".git", "node_modules", ".venv", "venv", "__pycache__", ".next",
    "dist", "build", ".cache", "site-packages", ".mypy_cache", "vendor",
}
WALK_BUDGET = 4000  # entries; a SessionStart hook must not stall a session


def _scalar(raw: str):
    """Minimal YAML subset: bare scalars, quoted strings, and [a, b] lists."""
    raw = raw.strip()
    if raw.startswith("[") and raw.endswith("]"):
        items = [i.strip().strip("\"'") for i in raw[1:-1].split(",")]
        return [i for i in items if i]
    return raw.strip("\"'")


def frontmatter(path: Path) -> dict:
    """Parse the leading --- block. Returns {} on anything unexpected."""
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return {}
    if not text.startswith("---"):
        return {}
    end = text.find("\n---", 3)
    if end == -1:
        return {}
    out = {}
    for line in text[3:end].splitlines():
        line = line.strip()
        if not line or line.startswith("#") or ":" not in line:
            continue
        key, _, value = line.partition(":")
        out[key.strip()] = _scalar(value)
    return out


def rules() -> list[dict]:
    """Every rule file, with the applicability it declares about itself."""
    found = []
    for path in sorted((plugin_root() / "rules").glob("*.md")):
        meta = frontmatter(path)
        profiles = meta.get("profiles", [])
        detect = meta.get("detect", [])
        found.append(
            {
                "path": path,
                "name": path.name,
                "description": meta.get("description", ""),
                "profiles": [profiles] if isinstance(profiles, str) else profiles,
                "detect": [detect] if isinstance(detect, str) else detect,
            }
        )
    return found


def detected(cwd: str, patterns: list[str]) -> str | None:
    """Return the first pattern that matches something in the tree, else None.

    Bounded walk: a hook that scans a monorepo on every session start is a hook
    that gets disabled.
    """
    if not patterns or not cwd:
        return None
    try:
        root = Path(cwd).resolve()
        if not root.is_dir():
            return None
    except Exception:
        return None

    literals = [p for p in patterns if "*" not in p]
    globs = [p for p in patterns if "*" in p]

    for name in literals:
        if (root / name).exists():
            return name

    if not globs:
        return None

    seen = 0
    stack = [(root, 0)]
    while stack and seen < WALK_BUDGET:
        current, depth = stack.pop()
        if depth > 3:
            continue
        try:
            entries = list(current.iterdir())
        except Exception:
            continue
        for entry in entries:
            seen += 1
            if seen > WALK_BUDGET:
                break
            if entry.is_dir():
                if entry.name not in SKIP_DIRS and not entry.name.startswith("."):
                    stack.append((entry, depth + 1))
                continue
            for pattern in globs:
                if entry.match(pattern):
                    return pattern
    return None


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
