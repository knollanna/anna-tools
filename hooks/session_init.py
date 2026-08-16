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

def select(cwd: str, profile: str) -> tuple[list[tuple], list[str]]:
    """Pick rules two ways: declared by profile, or detected in the directory.

    A rule declares its own applicability in its frontmatter, so adding one
    needs no change here. Returns the selected rules plus the names of any that
    were considered and skipped, which is what makes a wrong selection
    debuggable instead of mysterious.
    """
    chosen, skipped = [], []
    for rule in _lib.rules():
        if "*" in rule["profiles"]:
            chosen.append((rule, "always"))
        elif profile and profile in rule["profiles"]:
            chosen.append((rule, f"profile: {profile}"))
        else:
            hit = _lib.detected(cwd, rule["detect"])
            if hit:
                chosen.append((rule, f"found {hit}"))
            else:
                skipped.append(rule["name"])
    return chosen, skipped


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

    profile = (project or {}).get("profile", "")
    chosen, skipped = select(cwd, profile)

    header = "### Rules that apply here (read on demand, not preloaded)"
    if profile:
        header += f"\n\n_Profile: **{profile}**._"
    lines += ["", header, ""]

    for rule, why in chosen:
        lines.append(f"- `{rule['path']}` _({why})_ — {rule['description']}")

    if not chosen:
        lines.append("- None matched. Rules live in "
                     f"`{root / 'rules'}` if you need one anyway.")
    if skipped:
        lines += [
            "",
            f"Not applicable here, do not read unless asked: {', '.join(skipped)}.",
        ]
    # Only a name outside the registry is an error. A valid profile that no rule
    # claims is fine — it means the universal and detected rules already cover it.
    registry = _lib.known_profiles()
    if registry:
        warnings = []
        if profile and profile not in registry:
            warnings.append(
                f"project profile `{profile}` is not in profiles.json"
            )
        for rule in _lib.rules():
            unknown = [
                p for p in rule["profiles"] if p != "*" and p not in registry
            ]
            if unknown:
                warnings.append(
                    f"`{rule['name']}` claims unknown profile(s): {', '.join(unknown)}"
                )
        if warnings:
            lines += ["", "⚠️ Catalog drift — a rule may be silently not loading:"]
            lines += [f"- {w}" for w in warnings]

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
