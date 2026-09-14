#!/usr/bin/env python3
"""Merge a LinkedIn "Connections.csv" export into the same Neo4j graph as
graph_import.py.

Get the export from LinkedIn: Settings & Privacy -> Data privacy -> Get a
copy of your data -> Connections. It emails you a zip; the file inside is
Connections.csv. This is LinkedIn's own self-service export of your own
data, not scraping.

Person nodes are merged by name, so a pipeline contact (graph_import.py)
who is also a LinkedIn connection collapses into one node. Company nodes
are merged by name for the same reason: if the company on record in your
LinkedIn export differs from the company in job/pipeline.json for someone
you already know, that mismatch is the "did they move" signal.

    .venv/bin/python3 scripts/graph_import_linkedin.py [path/to/Connections.csv]

Defaults to job/linkedin_connections.csv (job/ is gitignored — this file,
like pipeline.json, never gets committed). Safe to re-run after a fresh
export; existing WORKS_AT edges for a person are overwritten, not
duplicated.
"""

import csv
import sys
from pathlib import Path

from neo4j import GraphDatabase

from _neo4j import REPO, load_aliases, load_env, load_person_aliases

DEFAULT_CSV = REPO / "job" / "linkedin_connections.csv"


def read_rows(path: Path) -> list[dict]:
    """Skip LinkedIn's export preamble and return rows keyed by its header."""
    lines = path.read_text(encoding="utf-8-sig").splitlines()
    for i, line in enumerate(lines):
        if line.startswith("First Name,Last Name"):
            header_idx = i
            break
    else:
        sys.exit(f"couldn't find the 'First Name,Last Name,...' header row in {path}")
    return list(csv.DictReader(lines[header_idx:]))


def import_rows(driver, rows: list[dict]) -> tuple[int, int]:
    aliases = load_aliases()
    person_aliases = load_person_aliases()
    n_people = n_edges = 0
    with driver.session() as session:
        for row in rows:
            first = (row.get("First Name") or "").strip()
            last = (row.get("Last Name") or "").strip()
            name = f"{first} {last}".strip()
            if not name:
                continue
            name = person_aliases.get(name, name)
            company = (row.get("Company") or "").strip()
            company = aliases.get(company, company)
            position = (row.get("Position") or "").strip()
            connected_on = (row.get("Connected On") or "").strip()
            url = (row.get("URL") or "").strip()
            email = (row.get("Email Address") or "").strip()

            session.run(
                """
                MERGE (p:Person {name: $name})
                SET p.linkedin_url = $url, p.email = coalesce(NULLIF($email, ''), p.email)
                """,
                name=name,
                url=url,
                email=email,
            )
            n_people += 1

            if company:
                session.run(
                    """
                    MERGE (c:Company {name: $company})
                    WITH c
                    MATCH (p:Person {name: $name})
                    MERGE (p)-[r:WORKS_AT]->(c)
                    SET r.position = $position, r.connected_on = $connected_on
                    """,
                    company=company,
                    name=name,
                    position=position,
                    connected_on=connected_on,
                )
                n_edges += 1

    return n_people, n_edges


def main():
    csv_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_CSV
    if not csv_path.exists():
        sys.exit(f"no file at {csv_path} — export from LinkedIn first (see docstring)")

    env = load_env()
    for key in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"):
        if key not in env:
            sys.exit(f"missing {key} in .env")

    rows = read_rows(csv_path)
    driver = GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"]))
    try:
        people, edges = import_rows(driver, rows)
        print(f"{people} LinkedIn connections merged, {edges} WORKS_AT edges set.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
