#!/usr/bin/env python3
"""Suggest company-name aliases so a LinkedIn connection's employer string
resolves to the same graph node as the matching job/pipeline.json company.

Scope is deliberately narrow: match every OTHER distinct Company name in the
graph against the ~76 pipeline companies (the canonical list), not against
each other. Two unrelated companies among your LinkedIn connections having
similar names isn't a problem worth solving here.

Two passes:
  1. Deterministic normalize (case, punctuation, legal suffixes) — catches
     "Google Cloud" style noise outright, no scoring needed.
  2. Fuzzy match the remainder against pipeline names via rapidfuzz —
     catches typos like Acmee/Acme. Suggestions only; nothing is
     auto-merged.

Writes candidates to job/company_alias_candidates.json for review. Approving
a mapping means adding it to job/company_aliases.json (alias -> canonical),
which graph_import.py and graph_import_linkedin.py apply on the next run.

    .venv/bin/python3 scripts/company_aliases_suggest.py [--threshold 85]
"""

import argparse
import json

from neo4j import GraphDatabase
from rapidfuzz import fuzz

from _neo4j import REPO, load_env, normalize

PIPELINE = REPO / "job" / "pipeline.json"
CANDIDATES_OUT = REPO / "job" / "company_alias_candidates.json"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=85)
    args = parser.parse_args()

    pipeline_companies = sorted({e["company"] for e in json.loads(PIPELINE.read_text())["entries"]})

    env = load_env()
    driver = GraphDatabase.driver(env["NEO4J_URI"], auth=(env["NEO4J_USER"], env["NEO4J_PASSWORD"]))
    with driver.session() as s:
        other_companies = sorted(
            {r["name"] for r in s.run("MATCH (c:Company) RETURN DISTINCT c.name AS name")}
            - set(pipeline_companies)
        )
    driver.close()

    norm_pipeline = {normalize(p): p for p in pipeline_companies}

    candidates = []
    seen_others = set()

    for other in other_companies:
        norm_other = normalize(other)
        if norm_other in norm_pipeline:
            candidates.append({
                "alias": other,
                "canonical": norm_pipeline[norm_other],
                "score": 100,
                "method": "normalized",
            })
            seen_others.add(other)

    remaining_pipeline_norms = list(norm_pipeline.keys())
    for other in other_companies:
        if other in seen_others:
            continue
        norm_other = normalize(other)
        best_norm, score, _ = max(
            ((p, fuzz.ratio(norm_other, p), None) for p in remaining_pipeline_norms),
            key=lambda t: t[1],
            default=(None, 0, None),
        )
        if score >= args.threshold:
            candidates.append({
                "alias": other,
                "canonical": norm_pipeline[best_norm],
                "score": round(score, 1),
                "method": "fuzzy",
            })

    candidates.sort(key=lambda c: (-c["score"], c["canonical"]))
    CANDIDATES_OUT.write_text(json.dumps(candidates, indent=2) + "\n")

    print(f"{len(candidates)} candidates written to {CANDIDATES_OUT.relative_to(REPO)}\n")
    for c in candidates:
        print(f"  [{c['score']:>5}] {c['alias']!r:40} -> {c['canonical']!r}  ({c['method']})")


if __name__ == "__main__":
    main()
