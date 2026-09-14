#!/usr/bin/env python3
"""Answer "who do I know at <Company>?" from the graph already built by
graph_import.py / graph_import_linkedin.py, instead of re-searching LinkedIn
by hand each time.

Read-only: this only queries. It never writes to job/pipeline.json, the
vault, or the graph itself.

Company-name resolution: exact case-insensitive match against Company nodes
first. On a miss, find_company() (scripts/_neo4j.py) fuzzy-matches the query
against every company name already in the graph, not just the pipeline's
~76 - so "Deloitte" can still surface "Deloitte Consulting LLP" as a
distinct, un-merged node even with no approved alias.

This only answers what the graph can answer: existing pipeline contacts and
direct LinkedIn connections at the company (the warm-path ladder's first two
rungs). Alumni who moved there from a former employer, or a named hiring
manager or recruiter you don't already know (the next two rungs), still need
a manual/WebSearch pass - the report says so rather than implying it checked.

Run graph_import.py / graph_import_linkedin.py again first if pipeline.json
or your LinkedIn export changed since the last import; this reads whatever
is already in the graph, not the source files.

    .venv/bin/python3 scripts/warm_path.py "<Company>"
"""

import argparse
import sys

from neo4j import GraphDatabase

from _neo4j import find_company, load_env


def pipeline_contacts(session, company: str) -> list[dict]:
    rows = session.run(
        """
        MATCH (p:Person)-[r:CONTACT_AT]->(c:Company {name: $company})
        RETURN p.name AS name, r.role AS role, r.detail AS detail
        ORDER BY p.name
        """,
        company=company,
    )
    return [dict(r) for r in rows]


def linkedin_connections(session, company: str) -> list[dict]:
    rows = session.run(
        """
        MATCH (p:Person)-[r:WORKS_AT]->(c:Company {name: $company})
        RETURN p.name AS name, r.position AS position,
               r.connected_on AS connected_on, p.linkedin_url AS url
        ORDER BY r.connected_on DESC
        """,
        company=company,
    )
    return [dict(r) for r in rows]


def render(company: str, contacts: list[dict], connections: list[dict]) -> str:
    lines = [f"Warm path — {company}", ""]

    lines.append(f"Pipeline contacts ({len(contacts)})")
    if contacts:
        for c in contacts:
            # detail carries the full parenthetical from pipeline.json; role
            # is only its first comma-delimited segment (graph_import.py) and
            # would silently truncate anything past the first comma.
            info = c.get("detail") or c.get("role")
            tail = f" — {info}" if info else ""
            lines.append(f"  {c['name']}{tail}")
    else:
        lines.append("  (none)")
    lines.append("")

    lines.append(f"LinkedIn connections at this company ({len(connections)})")
    if connections:
        for c in connections:
            bits = [b for b in (c.get("position"), c.get("connected_on")) if b]
            tail = f" ({', '.join(bits)})" if bits else ""
            url = f" — {c['url']}" if c.get("url") else ""
            lines.append(f"  {c['name']}{tail}{url}")
    else:
        lines.append("  (none)")
    lines.append("")

    if contacts or connections:
        lines.append(
            "Not covered by this graph: alumni who moved here from a former "
            "employer, or anyone not already a pipeline contact or a direct "
            "connection. Those still need a manual/WebSearch pass."
        )
    else:
        lines.append(
            "No known contacts in the graph at this company. This only checks "
            "the first two rungs of the ladder (pipeline contacts, direct "
            "LinkedIn connections). Alumni overlap and a named hiring manager "
            "or recruiter still need a manual/WebSearch pass — the graph has "
            "no data to answer those."
        )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("company", help="Company name to look up")
    args = parser.parse_args()

    env = load_env()
    driver = GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"]))
    try:
        with driver.session() as session:
            matches = find_company(session, args.company)
            if not matches:
                print(f'No company matching "{args.company}" found in the graph.')
                return 1
            if len(matches) > 1 or matches[0]["score"] < 100:
                print(f'No exact match for "{args.company}". Close matches in the graph:')
                for m in matches[:10]:
                    print(f"  [{m['score']:>5}] {m['name']}")
                print("\nRe-run with the exact name, e.g.:")
                print(f'  .venv/bin/python3 scripts/warm_path.py "{matches[0]["name"]}"')
                return 1

            company = matches[0]["name"]
            contacts = pipeline_contacts(session, company)
            connections = linkedin_connections(session, company)
            print(render(company, contacts, connections))
    finally:
        driver.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
