#!/usr/bin/env python3
"""Lint job/pipeline.json for the data-entry mistakes that hid real contacts
this session: an annotation baked into the company field instead of its own
field (e.g. "Acme Inc (ex)", "Acme Inc (Jamie Rivera)"), and a contacts
string with no "Name (detail)" shape that graph_import.py's CONTACT_RE
silently parses into zero edges (e.g. a bare "Jamie Rivera" with no
parenthetical) - no error, just a contact that quietly never reaches the
graph. Also flags a leftover placeholder value like "TBD" in contacts.

Read-only: reports, never edits. Reuses graph_import.py's own CONTACT_RE so
this predicts exactly what a real import will do, rather than drifting from
it over time.

    .venv/bin/python3 scripts/pipeline_lint.py
"""

import json
import sys
from pathlib import Path

from graph_import import CONTACT_RE

REPO = Path(__file__).resolve().parent.parent
PIPELINE = REPO / "job" / "pipeline.json"

PLACEHOLDER_VALUES = {"tbd", "n/a", "none", "unknown", "?"}


def check_company_field(entry: dict) -> str | None:
    company = entry.get("company", "")
    if "(" in company:
        return f'company field contains "(" - likely an annotation that belongs in contacts or note instead: {company!r}'
    return None


def check_contacts_field(entry: dict) -> str | None:
    contacts = entry.get("contacts", "")
    if not contacts:
        return None
    if contacts.strip().lower() in PLACEHOLDER_VALUES:
        return f"contacts field is a placeholder, not a real contact: {contacts!r}"
    if not CONTACT_RE.findall(contacts):
        return (
            'contacts field has no "Name (detail)" match - graph_import.py will '
            f"silently load this as zero contact edges: {contacts!r}"
        )
    return None


CHECKS = (check_company_field, check_contacts_field)


def main() -> int:
    data = json.loads(PIPELINE.read_text(encoding="utf-8"))
    issues = []
    for e in data["entries"]:
        for check in CHECKS:
            msg = check(e)
            if msg:
                issues.append((e["id"], msg))

    if not issues:
        print(f"clean - {len(data['entries'])} entries, no issues")
        return 0

    print(f"{len(issues)} issue(s) across {len(data['entries'])} entries:\n")
    for entry_id, msg in issues:
        print(f"  {entry_id}: {msg}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
