#!/usr/bin/env python3
"""Warm-path pending report for job/pipeline.json.

Every `considering`/`outreach` entry with no `human_path` logged yet — the
same set `hooks/job_context_nudge.py`'s pending count is computed from, listed
in full instead of just counted.

Unlike `objection_report.py`, there's no note text to mine for a forward-looking
check, so this automates the one part that *can* be automated instead of just
naming entries: for each pending company it runs the same graph queries
`warm_path.py` uses (imported, not reimplemented) and prints rungs 1-2 inline.
Alumni overlap and a named hiring manager/recruiter (rungs 3-4) still need a
manual/WebSearch pass - this proposes nothing for those, same "propose, never
invent" rule as objection classification.

Read-only: queries the graph, never writes job/pipeline.json.

    .venv/bin/python3 scripts/human_path_report.py
"""

import json
import sys
from pathlib import Path

from neo4j import GraphDatabase

from _neo4j import find_company, is_exact_match, load_env
from warm_path import linkedin_connections, pipeline_contacts, render

REPO = Path(__file__).resolve().parent.parent
PIPELINE = REPO / "job" / "pipeline.json"

GATED_STAGES = {"considering", "outreach"}


def pending_entries() -> list[dict]:
    data = json.loads(PIPELINE.read_text(encoding="utf-8"))
    return [
        e for e in data["entries"]
        if e.get("stage") in GATED_STAGES and not e.get("human_path")
    ]


def main() -> int:
    pending = pending_entries()
    print(f"Warm-path pending — {len(pending)} considering/outreach entries with no human_path\n")
    if not pending:
        print("  (none — every considering/outreach entry has a check logged)")
        return 0

    env = load_env()
    driver = GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"]))
    try:
        with driver.session() as session:
            for e in pending:
                print(f"=== {e['id']} ({e['company']}, {e['stage']}) ===")
                matches = find_company(session, e["company"])
                if not is_exact_match(matches):
                    print(f'  No exact graph match for "{e["company"]}" — check the name by hand.')
                    print()
                    continue
                company = matches[0]["name"]
                contacts = pipeline_contacts(session, company)
                connections = linkedin_connections(session, company)
                for line in render(company, contacts, connections).splitlines():
                    print(f"  {line}")
                print()
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
