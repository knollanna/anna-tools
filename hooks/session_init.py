#!/usr/bin/env python3
"""SessionStart hook — tell the session where it is and which rules apply.

This is what makes anna-tools useful outside its own directory. A session opened
in `farewatch/` never loads `anna-tools/CLAUDE.md`, so without this the rules are
a library nobody opens. Here they arrive with absolute paths, already resolved,
before the first prompt.

It emits pointers, never content. Loading four rule files into every session
would cost tokens in every conversation that doesn't need them; naming them costs
almost nothing and the model reads what's relevant.

Silent on anything unexpected.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

RULES = [
    ("writing.md", "Voice. Before anything Anna will publish, commit, or read."),
    ("design-system.md", "The a11y and type bar. Before any CSS, color, type, or markup."),
    ("github.md", "Branches, commits, review. Before committing or pushing."),
    ("job-search.md", "Interviews, transcripts, applications, pipeline changes."),
]


def main() -> int:
    data = _lib.payload()
    cwd = data.get("cwd") or data.get("workspace", {}).get("current_dir") or ""

    root = _lib.plugin_root()
    home = _lib.data_home()
    lines = ["**anna-tools** is active."]

    project = _lib.project_for(cwd)
    if project:
        lines += ["", f"### You are in: {project.get('name')}", ""]
        if project.get("what"):
            lines.append(f"- {project['what']}")
        for label, key in (
            ("Stack", "stack"),
            ("Deploy", "deploy"),
            ("Status", "status"),
        ):
            if project.get(key):
                lines.append(f"- **{label}:** {project[key]}")
        if project.get("watch_out"):
            lines.append(f"- ⚠️ **Watch out:** {project['watch_out']}")
        docs = [project.get("architecture"), *(project.get("also_read") or [])]
        docs = [d for d in docs if d]
        if docs:
            joined = ", ".join(f"`{home.parent / d}`" for d in docs)
            lines.append(f"- **Read before changing anything here:** {joined}")

    lines += ["", "### Rules (read on demand, not preloaded)", ""]
    for filename, when in RULES:
        path = root / "rules" / filename
        if path.exists():
            lines.append(f"- `{path}` — {when}")

    lines += [
        "",
        f"Project catalog: `{home / 'projects.json'}`. "
        f"Anna's background: `{home / 'resume' / 'summary.md'}` "
        "(full history and interview stories alongside it, on demand).",
        "",
        "Never state a role, date, employer, metric, or credential about Anna that is not in "
        "`resume/full.md`. Ask instead.",
    ]

    _lib.emit("SessionStart", "\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
