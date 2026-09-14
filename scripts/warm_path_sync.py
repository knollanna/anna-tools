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

from _neo4j import JOBWATCH_ENV, load_env


def fetch_counts(session) -> list[dict]:
    """One row per Company node with at least one CONTACT_AT or WORKS_AT edge.

    count(p1)/count(p2) on the named, optionally-matched Person - not
    count(*) - is what makes a real zero possible: OPTIONAL MATCH still
    produces one row with a null p1/p2 binding when nothing matches, and
    count(*) counts that row regardless, so contact_count/connection_count
    would otherwise never actually read 0 and the WHERE clause below would
    let almost every Company node in the graph through.
    """
    rows = session.run(
        """
        MATCH (c:Company)
        OPTIONAL MATCH (c)<-[:CONTACT_AT]-(p1:Person)
        WITH c, count(p1) AS contact_count
        OPTIONAL MATCH (c)<-[:WORKS_AT]-(p2:Person)
        WITH c, contact_count, count(p2) AS connection_count
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

    try:
        jobwatch_env = load_env(JOBWATCH_ENV)
    except FileNotFoundError as e:
        sys.exit(f"{e} - can't reach JobWatch's Supabase project")
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

    # A Company node with no name property is a malformed/partial import,
    # not a company to sync - skip and say so rather than crash on .lower().
    skipped = [r for r in counts if not r.get("company")]
    counts = [r for r in counts if r.get("company")]

    if not counts:
        print("No companies with a contact or connection in the graph - nothing to sync.")
        return 0

    # Two differently-cased Company nodes (e.g. "NiCE" / "NICE") collapse to
    # the same lowercase key here even though graph_import's MERGE never
    # unified them as one node - sum rather than let the second upsert in the
    # same batch collide with the first. Surfaced separately below so the
    # underlying duplicate node can be fixed at the source (an alias in
    # company_aliases.json + a re-import), not just papered over here.
    by_key: dict[str, list[dict]] = {}
    for row in counts:
        by_key.setdefault(row["company"].lower(), []).append(row)

    rows = []
    collisions = {}
    for key, group in by_key.items():
        rows.append({
            "company": key,
            "contact_count": sum(r["contact_count"] for r in group),
            "connection_count": sum(r["connection_count"] for r in group),
        })
        if len(group) > 1:
            # Sorted so the reported grouping is the same on every run,
            # independent of Neo4j's (unordered) result order.
            collisions[key] = sorted(r["company"] for r in group)

    client = create_client(supabase_url, supabase_key)
    client.table("warm_path").upsert(rows, on_conflict="company").execute()

    # upsert only ever adds/updates the keys in this run's payload - a company
    # whose last contact/connection dropped out of the graph since the prior
    # sync would otherwise sit in Supabase forever at its last (now stale)
    # positive count. Prune anything in the table that isn't in this run's
    # result so the table always reflects the graph's current state exactly.
    current_keys = {r["company"] for r in rows}
    existing = client.table("warm_path").select("company").execute()
    stale_keys = [r["company"] for r in existing.data if r["company"] not in current_keys]
    if stale_keys:
        client.table("warm_path").delete().in_("company", stale_keys).execute()

    print(f"{len(rows)} companies synced to JobWatch's warm_path table.")
    for row in sorted(rows, key=lambda r: r["company"]):
        print(f"  {row['company']!r}: {row['contact_count']} contact(s), {row['connection_count']} connection(s)")
    if skipped:
        print(f"\n{len(skipped)} Company node(s) with no name property skipped.")
    if stale_keys:
        print(f"{len(stale_keys)} stale row(s) no longer backed by a contact/connection removed: "
              f"{', '.join(sorted(stale_keys))}")
    if collisions:
        print(f"\n{len(collisions)} case-variant duplicate(s) merged on sync - fix at the "
              f"source (company_aliases.json + re-run graph_import.py) so they're one "
              f"node, not just summed here:")
        for key, names in collisions.items():
            print(f"  {' / '.join(names)} -> merged as {key!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
