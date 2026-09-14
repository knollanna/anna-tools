#!/usr/bin/env python3
"""Objection-pattern report for job/pipeline.json.

Two sections:

1. Pattern report - every entry with an `objection.inferred_class` already set,
   grouped by class. A class at 3+ occurrences is flagged as a pattern, not luck
   (rules/job-search.md; borrowed from JobFinderOS's playbook Sec9).
2. Needs review - every closed entry (lost/dropped/noresponse) with no `objection`
   field yet. A keyword/phrase matcher over the note text proposes an
   inferred_class + confidence, citing the phrase that triggered it. This is a
   proposal to confirm or correct by hand, never a write - `stated` is deliberately
   left for you to fill in from the note, since extracting a clean verbatim quote
   by regex risks laundering a guess as a fact.

Read-only: reports, never edits job/pipeline.json.

    .venv/bin/python3 scripts/objection_report.py
"""

import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PIPELINE = REPO / "job" / "pipeline.json"

CLOSED_STAGES = {"lost", "dropped", "noresponse"}

CLASSES = [
    "domain-proof-gap",
    "level-mismatch",
    "location",
    "comp",
    "slate",
    "culture-style",
    "unknown",
]

# Order matters: checked top to bottom, first match wins.
#
# Deliberately compound phrases, not bare words: "comp" and "level" and "fit" show
# up constantly as routine data (a role's disclosed comp, its title, why Anna liked
# it) with no connection to why it was actually lost. A bare-word first pass on this
# corpus flagged 44 of 58 entries as "comp" - including one entry whose actual
# stated reason (a screening call naming a practitioner-vs-presales gap) has
# nothing to do with comp; the note just also discloses a number. Requiring the
# word to appear paired with an explicit gap/mismatch phrase cuts that false-positive
# rate at the cost of surfacing fewer, lower-confidence "unknown"s instead - a wrong
# "unknown" costs nothing (you already read the note), a wrong "comp" costs trust
# in the whole suggestion.
KEYWORD_RULES = [
    ("comp", re.compile(r"comp\s+(gap|under)|under\s+the\s+floor|below\s+the\s+floor|OTE\s+ceiling", re.I)),
    ("level-mismatch", re.compile(r"level\s+(mismatch|jump)|over-?leveled|under-?leveled|leader\s+of\s+leaders|prior\s+\w+\s+title", re.I)),
    ("location", re.compile(r"relocation\s+required|no\s+relocation|not\s+remote|location\s+mismatch|onsite\s+required", re.I)),
    ("slate", re.compile(r"\bslate\b|other\s+candidate|someone\s+closer|closer\s+to\s+what", re.I)),
    ("culture-style", re.compile(r"not\s+a\s+fit|culture\s+fit|style\s+mismatch|wasn.t\s+a\s+fit", re.I)),
    ("domain-proof-gap", re.compile(r"domain\s+gap|not\s+hands-?on|practitioner|domain-proof", re.I)),
]


def load_entries() -> list[dict]:
    data = json.loads(PIPELINE.read_text(encoding="utf-8"))
    return data["entries"]


def draft_classification(note: str) -> tuple[str, str, str]:
    """-> (inferred_class, confidence, reason). Falls back to unknown/low."""
    for cls, pattern in KEYWORD_RULES:
        m = pattern.search(note or "")
        if m:
            return cls, "medium", f'matched "{m.group(0)}"'
    return "unknown", "low", "no matching phrase found"


def pattern_report(entries: list[dict]) -> None:
    by_class: dict[str, list[str]] = {c: [] for c in CLASSES}
    for e in entries:
        obj = e.get("objection")
        if not obj or not obj.get("inferred_class"):
            continue
        by_class.setdefault(obj["inferred_class"], []).append(e["id"])

    classified = sum(len(v) for v in by_class.values())
    print(f"Pattern report — {classified} entries classified\n")
    if not classified:
        print("  (none yet)")
    else:
        for cls, ids in by_class.items():
            if not ids:
                continue
            flag = "  <- pattern, a positioning problem, not luck" if len(ids) >= 3 else ""
            print(f"  {cls} ({len(ids)}){flag}")
            for entry_id in ids:
                print(f"    {entry_id}")
    print()


def needs_review(entries: list[dict]) -> None:
    pending = [
        e for e in entries
        if e.get("stage") in CLOSED_STAGES and not e.get("objection")
    ]
    print(f"Needs review — {len(pending)} closed entries with no objection classification\n")
    if not pending:
        print("  (none — every closed entry is classified)")
        return
    for e in pending:
        cls, confidence, reason = draft_classification(e.get("note", ""))
        print(f"  {e['id']} ({e['company']}, {e['stage']})")
        print(f"    suggested: {cls} — confidence {confidence} — {reason}")


def main() -> int:
    entries = load_entries()
    pattern_report(entries)
    needs_review(entries)
    return 0


if __name__ == "__main__":
    sys.exit(main())
