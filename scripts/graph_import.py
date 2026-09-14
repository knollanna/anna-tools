#!/usr/bin/env python3
"""Load job/pipeline.json into a local Neo4j graph.

pipeline.json already carries graph-shaped data that tracker.md and board.py
flatten into lists: which contacts sit at which company, at what stage. This
mirrors that same source of truth into (Company)-[:CONTACT_AT]-(Person) and
(Company)-[:AT_STAGE]->(Stage) so it can be queried instead of read.

Credentials come from .env (gitignored) via NEO4J_URI / NEO4J_USER /
NEO4J_PASSWORD. Nothing from job/ is written back to disk; it goes straight
over bolt into the local database, which itself lives outside this repo
(Homebrew's neo4j data dir), so no pipeline content ever touches git.

    .venv/bin/python3 scripts/graph_import.py [--wipe]

`--wipe` clears prior Company/Person/Stage nodes before reloading, for
re-running after pipeline.json changes.
"""

import argparse
import json
import re
import sys

from neo4j import GraphDatabase

from _neo4j import REPO, load_aliases, load_env, load_person_aliases

DATA = REPO / "job" / "pipeline.json"

CONTACT_RE = re.compile(r"([A-Z][\w.'-]*(?:\s+[A-Z]?[\w.'-]+)*)\s*\(([^)]*)\)")


def parse_contacts(text: str) -> list[tuple[str, str]]:
    """'Name (role, detail), Name (role, detail)' -> [(name, detail), ...]"""
    out = []
    for name, detail in CONTACT_RE.findall(text or ""):
        name = name.strip().rstrip(",")
        if name:
            out.append((name, detail.strip()))
    return out


def load() -> dict:
    return json.loads(DATA.read_text(encoding="utf-8"))


def import_data(driver, data: dict, wipe: bool) -> tuple[int, int, int]:
    stages = {s["key"]: s["label"] for s in data["stages"]}
    aliases = load_aliases()
    person_aliases = load_person_aliases()
    n_companies = n_people = n_edges = 0

    with driver.session() as session:
        if wipe:
            session.run(
                "MATCH (n) WHERE n:Company OR n:Person OR n:Stage DETACH DELETE n"
            )

        for key, label in stages.items():
            session.run(
                "MERGE (s:Stage {key: $key}) SET s.label = $label", key=key, label=label
            )

        for e in data["entries"]:
            company_name = aliases.get(e["company"], e["company"])
            session.run(
                """
                MERGE (c:Company {name: $name})
                SET c.pipeline_id = $id, c.role = $role
                WITH c
                MATCH (s:Stage {key: $stage})
                MERGE (c)-[:AT_STAGE]->(s)
                """,
                id=e["id"],
                name=company_name,
                role=e.get("role") or "",
                stage=e.get("stage", "unknown"),
            )
            n_companies += 1

            for raw_name, detail in parse_contacts(e.get("contacts", "")):
                name = person_aliases.get(raw_name, raw_name)
                role = detail.split(",")[0].strip() if detail else ""
                session.run(
                    """
                    MERGE (p:Person {name: $name})
                    WITH p
                    MATCH (c:Company {name: $company_name})
                    MERGE (p)-[r:CONTACT_AT]->(c)
                    SET r.role = $role, r.detail = $detail
                    """,
                    name=name,
                    company_name=company_name,
                    role=role,
                    detail=detail,
                )
                n_people += 1
                n_edges += 1

    return n_companies, n_people, n_edges


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--wipe", action="store_true", help="clear prior graph data first")
    args = parser.parse_args()

    env = load_env()
    for key in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"):
        if key not in env:
            sys.exit(f"missing {key} in .env")

    driver = GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"]))
    try:
        data = load()
        companies, contact_edges, edges = import_data(driver, data, args.wipe)
        print(f"{companies} companies, {contact_edges} contact edges loaded into Neo4j.")
    finally:
        driver.close()


if __name__ == "__main__":
    main()
