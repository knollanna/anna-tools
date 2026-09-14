#!/usr/bin/env python3
"""Merge LinkedIn's Invitations.csv (outstanding sent/received invites) into
the graph as (from:Person)-[:INVITED]->(to:Person).

Invitations.csv only lists invites still pending — an accepted one moves to
Connections.csv and drops off this file — so the edge existing at all means
"pending", no separate status field needed.

    .venv/bin/python3 scripts/graph_import_invitations.py [path/to/Invitations.csv]

Defaults to job/invitations.csv (gitignored, same as the other exports).
"""

import csv
import sys
from pathlib import Path

from neo4j import GraphDatabase

from _neo4j import REPO, load_env, load_person_aliases

DEFAULT_CSV = REPO / "job" / "invitations.csv"


def import_rows(driver, rows: list[dict]) -> int:
    person_aliases = load_person_aliases()
    n = 0
    with driver.session() as session:
        for row in rows:
            from_name = (row.get("From") or "").strip()
            to_name = (row.get("To") or "").strip()
            if not from_name or not to_name:
                continue
            from_name = person_aliases.get(from_name, from_name)
            to_name = person_aliases.get(to_name, to_name)
            session.run(
                """
                MERGE (a:Person {name: $from_name})
                MERGE (b:Person {name: $to_name})
                MERGE (a)-[r:INVITED]->(b)
                SET r.sent_at = $sent_at, r.message = $message
                """,
                from_name=from_name,
                to_name=to_name,
                sent_at=(row.get("Sent At") or "").strip(),
                message=(row.get("Message") or "").strip(),
            )
            n += 1
    return n


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        sys.exit(f"no file at {csv_path}")

    env = load_env()
    driver = GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"]))
    try:
        with open(csv_path, encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        n = import_rows(driver, rows)
        print(f"{n} INVITED edges set.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
