#!/usr/bin/env python3
"""Report open-stage pipeline companies JobWatch isn't polling directly.

JobWatch's ATS_BOARDS (jobwatch/config.py) is a hand-maintained list of
Greenhouse/Ashby tokens for companies in Anna's pipeline. It only grows when
someone notices a gap and adds one — this makes the gap visible instead of
relying on noticing. Read-only report, no candidates file: unlike a title or
company-name match, there's nothing to fuzzy-score here, and finding the
actual ATS token still needs a manual/WebSearch pass (JobWatch's own
ats_sources.py does the fetching once a token is known).

Comparison is normalized (case/punctuation/legal-suffix-insensitive, the same
normalize() used to resolve a graph company name), not just lower()'d - so
"Salesforce, Inc." in the pipeline still matches "Salesforce" in ATS_BOARDS.
It still won't catch every real match: an alias like "Meta (Facebook)"
needs an actual entry in job/company_aliases.json to resolve, the same limit
company_aliases_suggest.py's own candidates have until approved.

    .venv/bin/python3 scripts/ats_coverage_report.py
"""

import json

from _neo4j import OPEN_STAGES, REPO, load_aliases, load_jobwatch_config_names, normalize

PIPELINE = REPO / "job" / "pipeline.json"


def load_ats_companies() -> set[str]:
    boards = load_jobwatch_config_names("ATS_BOARDS")["ATS_BOARDS"]
    return {normalize(b["company"]) for b in boards if b.get("company")}


def load_pipeline_companies() -> list[str]:
    entries = json.loads(PIPELINE.read_text(encoding="utf-8"))["entries"]
    companies = {e["company"].strip() for e in entries if e.get("stage") in OPEN_STAGES}
    return sorted(companies)


def main():
    ats_companies = load_ats_companies()
    pipeline_companies = load_pipeline_companies()
    aliases = load_aliases()

    missing = [
        c for c in pipeline_companies
        if normalize(aliases.get(c, c)) not in ats_companies
    ]

    print(f"{len(pipeline_companies)} open-stage pipeline companies checked "
          f"against {len(ats_companies)} in JobWatch's ATS_BOARDS.")
    print(f"{len(missing)} not directly polled:\n")
    for c in missing:
        print(f"  {c}")
    print("\nCheck each for a Greenhouse/Ashby board and add its token to "
          "jobwatch/config.py's ATS_BOARDS if found.")


if __name__ == "__main__":
    main()
