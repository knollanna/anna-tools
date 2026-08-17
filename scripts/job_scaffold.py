#!/usr/bin/env python3
"""Create one folder per active company from the pipeline tracker.

Folders are per *company*, not per requisition. One relationship can have several
entries in the tracker, and a transcript belongs to the relationship rather than
to a req. Each folder gets a README seeded from the tracker so it opens with real
content instead of being an empty directory nobody fills.

Idempotent. Never overwrites a README that already exists — the seeded version is
a starting point that Anna and later sessions edit, and clobbering it on a re-run
would silently delete work.

    python3 scripts/job_scaffold.py [--stages interviewing,waiting,...] [--dry-run]

Everything it writes lives under job/, which is gitignored.
"""

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tracker_to_md import DEFAULT_IN, block, parse  # noqa: E402

REPO = Path(__file__).resolve().parent.parent
JOB = REPO / "job"
COMPANIES = JOB / "companies"
INBOX = JOB / "inbox"

# Stages worth a folder. The 29 lost and 10 never-heard-back entries stay as
# tracker rows; exploding those into directories buys nothing.
ACTIVE = ["interviewing", "waiting", "applied", "followup"]

PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")
NONWORD = re.compile(r"[^a-z0-9]+")


def slugify(company: str) -> str:
    base = PARENTHETICAL.sub("", company).strip().lower()
    return NONWORD.sub("-", base).strip("-")


def readme(company: str, entries: list[dict], labels: dict) -> str:
    lines = [
        f"# {company}",
        "",
        "Everything for this company. Transcripts, prep, and research live in the",
        "subfolders; this file is the standing picture.",
        "",
        "## Where it stands",
        "",
    ]
    for e in entries:
        stage = labels.get(e.get("stage", ""), e.get("stage", "?"))
        lines.append(f"- **{e.get('role', '?')}** — {stage}")
        if e.get("contacts"):
            lines.append(f"  - Contacts: {e['contacts']}")
    lines += [
        "",
        "## What I know",
        "",
        "_Seeded from the tracker. Edit freely — this file is the source of truth for this",
        "company from here on, and the tracker keeps only the stage._",
        "",
    ]
    for e in entries:
        if e.get("notes"):
            lines += [f"### {e.get('role', '?')}", "", e["notes"], ""]
    lines += [
        "## Open questions",
        "",
        "- ",
        "",
        "## Files",
        "",
        "- `jd/` — job descriptions and req text, `YYYY-MM-DD-role.md`. Keep every version;",
        "  JDs get edited quietly and the diff is evidence.",
        "- `transcripts/` — one file per call, `YYYY-MM-DD-who.md`, raw kept verbatim",
        "- `prep/` — prep docs, panel prompts, recruiter correspondence, anything they sent",
        "- `research/` — company research, so it stops dying in chat sessions",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stages", default=",".join(ACTIVE),
                    help=f"comma-separated stage keys (default: {','.join(ACTIVE)})")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    wanted = {s.strip() for s in args.stages.split(",") if s.strip()}

    if not DEFAULT_IN.exists():
        print(f"no tracker at {DEFAULT_IN}", file=sys.stderr)
        return 1

    html = DEFAULT_IN.read_text(encoding="utf-8")
    labels = {s["key"]: s["label"] for s in parse(block(html, "STAGES"))}
    entries = [e for e in parse(block(html, "SEED")) if e.get("stage") in wanted]

    grouped: dict[str, list[dict]] = {}
    names: dict[str, str] = {}
    for e in entries:
        company = e.get("company", "").strip()
        if not company:
            continue
        slug = slugify(company)
        grouped.setdefault(slug, []).append(e)
        names.setdefault(slug, company)

    created, skipped = [], []
    for slug, rows in sorted(grouped.items()):
        base = COMPANIES / slug
        target = base / "README.md"
        if args.dry_run:
            print(f"would create {base}/ ({len(rows)} entr{'y' if len(rows)==1 else 'ies'})")
            continue
        for sub in ("jd", "transcripts", "prep", "research"):
            (base / sub).mkdir(parents=True, exist_ok=True)
        if target.exists():
            skipped.append(slug)
        else:
            target.write_text(readme(names[slug], rows, labels), encoding="utf-8")
            created.append(slug)

    if args.dry_run:
        print(f"\n{len(grouped)} companies across stages: {', '.join(sorted(wanted))}")
        return 0

    INBOX.mkdir(parents=True, exist_ok=True)
    inbox_readme = INBOX / "README.md"
    if not inbox_readme.exists():
        inbox_readme.write_text(
            "# Inbox\n\n"
            "Drop transcripts and notes here when you are capturing fast and do not want to\n"
            "decide which company folder they belong to. That decision is what kills the\n"
            "habit; filing happens later, in a session.\n\n"
            "Name it `YYYY-MM-DD-what.md` and paste. No frontmatter, no summary — a session\n"
            "adds those when it files the file into `../companies/<slug>/transcripts/`.\n\n"
            "Paste both Granola panes, labeled `## Granola notes` and `## Raw`. Granola\n"
            "encrypts its local store, so there is no automated export; this is the path.\n\n"
            "An empty inbox is the goal.\n",
            encoding="utf-8",
        )

    print(f"created {len(created)}: {', '.join(created) or '—'}")
    if skipped:
        print(f"left alone (README exists) {len(skipped)}: {', '.join(skipped)}")
    print(f"inbox: {INBOX}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
