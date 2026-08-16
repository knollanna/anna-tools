#!/usr/bin/env python3
"""Convert the job-search tracker HTML artifact into markdown.

The tracker is a self-contained HTML artifact whose pipeline lives in a JS
`SEED` array. This pulls that array out and writes a grouped markdown board so
the data is greppable and diffable instead of locked inside a rendered page.

Reads and writes inside job/, which is gitignored. Nothing here touches the
repo's tracked files.

    python3 scripts/tracker_to_md.py [in.html] [out.md]
"""

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
DEFAULT_IN = REPO / "job" / "job_search_tracker.html"
DEFAULT_OUT = REPO / "job" / "tracker.md"

FIELD = re.compile(r'(\w+)\s*:\s*"((?:[^"\\]|\\.)*)"')


def unescape(value: str) -> str:
    return value.replace('\\"', '"').replace("\\\\", "\\").replace("\\n", " ")


def objects(src: str):
    """Yield each top-level `{...}` in an array, ignoring braces inside strings."""
    depth, start, in_str, esc = 0, None, False, False
    for i, ch in enumerate(src):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                yield src[start : i + 1]
                start = None


def block(html: str, name: str) -> str:
    """Return the source of a top-level `var <name> = [ ... ];` array."""
    start = html.index(f"var {name} = [")
    depth, i = 0, html.index("[", start)
    for j in range(i, len(html)):
        if html[j] == "[":
            depth += 1
        elif html[j] == "]":
            depth -= 1
            if depth == 0:
                return html[i : j + 1]
    raise ValueError(f"unterminated {name} array")


def parse(src: str) -> list[dict]:
    return [{k: unescape(v) for k, v in FIELD.findall(obj)} for obj in objects(src)]


def main() -> int:
    src_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_IN
    out_path = Path(sys.argv[2]) if len(sys.argv) > 2 else DEFAULT_OUT

    if not src_path.exists():
        print(f"no tracker at {src_path}", file=sys.stderr)
        return 1

    html = src_path.read_text(encoding="utf-8")
    stages = parse(block(html, "STAGES"))
    entries = parse(block(html, "SEED"))

    order = [s["key"] for s in stages]
    labels = {s["key"]: s["label"] for s in stages}
    by_stage: dict[str, list[dict]] = {k: [] for k in order}
    for e in entries:
        by_stage.setdefault(e.get("stage", "unknown"), []).append(e)

    lines = [
        "# Job search pipeline",
        "",
        f"Generated from `{src_path.name}` by `scripts/tracker_to_md.py`. "
        "The HTML artifact is the source of truth; regenerate rather than hand-editing.",
        "",
        f"**{len(entries)} entries.**",
        "",
    ]

    counts = " · ".join(
        f"{labels.get(k, k)} {len(by_stage.get(k, []))}"
        for k in order
        if by_stage.get(k)
    )
    lines += [counts, "", "---", ""]

    for key in order + [k for k in by_stage if k not in order]:
        rows = by_stage.get(key, [])
        if not rows:
            continue
        lines += [f"## {labels.get(key, key)} ({len(rows)})", ""]
        for e in rows:
            lines.append(f"### {e.get('company', '?')} — {e.get('role', '?')}")
            lines.append("")
            if e.get("contacts"):
                lines += [f"**Contacts:** {e['contacts']}", ""]
            if e.get("notes"):
                lines += [e["notes"], ""]
        lines.append("---")
        lines.append("")

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"{len(entries)} entries across {sum(1 for k in by_stage if by_stage[k])} stages -> {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
