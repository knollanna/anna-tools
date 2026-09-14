#!/usr/bin/env python3
"""Sync a warm-path signal from the local Neo4j graph into JobWatch's Supabase
project, so its nightly digest can flag postings at companies where a
pipeline contact or LinkedIn connection already exists.

JobWatch runs on Render with a filesystem wiped between cron runs, so it can
never reach this graph directly (bolt://, local-only, not Aura). Supabase is
already the local->cloud bridge JobWatch uses for dedupe (dedupe_store.py's
seen_jobs table) - this reuses that same bridge rather than exposing Neo4j to
the internet.

Only a company name and two counts travel to Supabase - never a contact's
name. rules/job-search.md treats named contacts as data that must never leave
this machine; a count clears that bar, a name wouldn't. Run `warm_path.py
"<Company>"` locally for who, once a count says there's a "who" worth asking.

Run manually after graph_import.py / graph_import_linkedin.py, same cadence -
this isn't a cron job, it's a session action.

    .venv/bin/python3 scripts/warm_path_sync.py
"""

import sys

from neo4j import GraphDatabase
from supabase import create_client

from _neo4j import REPO, load_env

JOBWATCH_ENV = REPO.parent / "jobwatch" / ".env"


def load_jobwatch_env() -> dict:
    env = {}
    for line in JOBWATCH_ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            env[k.strip()] = v.strip()
    return env


def fetch_counts(session) -> list[dict]:
    """One row per Company node with at least one CONTACT_AT or WORKS_AT edge."""
    rows = session.run(
        """
        MATCH (c:Company)
        OPTIONAL MATCH (c)<-[:CONTACT_AT]-(:Person)
        WITH c, count(*) AS contact_count
        OPTIONAL MATCH (c)<-[:WORKS_AT]-(:Person)
        WITH c, contact_count, count(*) AS connection_count
        WHERE contact_count > 0 OR connection_count > 0
        RETURN c.name AS company, contact_count, connection_count
        """
    )
    return [dict(r) for r in rows]


def main() -> int:
    env = load_env()
    for key in ("NEO4J_URI", "NEO4J_USER", "NEO4J_PASSWORD"):
        if key not in env:
            sys.exit(f"missing {key} in .env")

    if not JOBWATCH_ENV.exists():
        sys.exit(f"no .env at {JOBWATCH_ENV} - can't reach JobWatch's Supabase project")
    jobwatch_env = load_jobwatch_env()
    supabase_url = jobwatch_env.get("SUPABASE_URL")
    supabase_key = jobwatch_env.get("SUPABASE_ANON_KEY")
    if not supabase_url or not supabase_key:
        sys.exit(f"SUPABASE_URL/SUPABASE_ANON_KEY not set in {JOBWATCH_ENV}")

    driver = GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"]))
    try:
        with driver.session() as session:
            counts = fetch_counts(session)
    finally:
        driver.close()

    if not counts:
        print("No companies with a contact or connection in the graph - nothing to sync.")
        return 0

    # Two differently-cased Company nodes (e.g. "Acme" / "ACME") collapse to
    # the same lowercase key here even though graph_import's MERGE never
    # unified them as one node - sum rather than let the second upsert in the
    # same batch collide with the first. Surfaced separately below so the
    # underlying duplicate node can be fixed at the source (an alias in
    # company_aliases.json + a re-import), not just papered over here.
    merged: dict[str, dict] = {}
    collisions: dict[str, list[str]] = {}
    for row in counts:
        key = row["company"].lower()
        if key in merged:
            collisions.setdefault(key, [merged[key]["_name"]]).append(row["company"])
            merged[key]["contact_count"] += row["contact_count"]
            merged[key]["connection_count"] += row["connection_count"]
        else:
            merged[key] = {
                "company": key,
                "contact_count": row["contact_count"],
                "connection_count": row["connection_count"],
                "_name": row["company"],
            }
    rows = [{k: v for k, v in r.items() if k != "_name"} for r in merged.values()]

    client = create_client(supabase_url, supabase_key)
    client.table("warm_path").upsert(rows, on_conflict="company").execute()

    print(f"{len(rows)} companies synced to JobWatch's warm_path table.")
    for row in sorted(rows, key=lambda r: r["company"]):
        print(f"  {row['company']!r}: {row['contact_count']} contact(s), {row['connection_count']} connection(s)")
    if collisions:
        print(f"\n{len(collisions)} case-variant duplicate(s) merged on sync - fix at the "
              f"source (company_aliases.json + re-run graph_import.py) so they're one "
              f"node, not just summed here:")
        for key, names in collisions.items():
            print(f"  {' / '.join(names)} -> merged as {key!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
