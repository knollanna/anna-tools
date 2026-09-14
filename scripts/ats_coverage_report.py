#!/usr/bin/env python3
"""Report active-stage pipeline companies JobWatch isn't polling directly.

JobWatch's ATS_BOARDS (jobwatch/config.py) is a hand-maintained list of
Greenhouse/Ashby tokens for companies in Anna's pipeline. It only grows when
someone notices a gap and adds one — this makes the gap visible instead of
relying on noticing. Read-only report, no candidates file: unlike a title or
company-name match, there's nothing to fuzzy-score here, and finding the
actual ATS token still needs a manual/WebSearch pass (JobWatch's own
ats_sources.py does the fetching once a token is known).

    .venv/bin/python3 scripts/ats_coverage_report.py
"""

import ast
import json

from _neo4j import REPO

PIPELINE = REPO / "job" / "pipeline.json"
JOBWATCH_CONFIG = REPO.parent / "jobwatch" / "config.py"

ACTIVE_STAGES = {"applied", "considering", "outreach", "warm", "followup"}


def load_ats_companies() -> set[str]:
    tree = ast.parse(JOBWATCH_CONFIG.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id == "ATS_BOARDS":
                boards = ast.literal_eval(node.value)
                return {b["company"].lower() for b in boards}
    return set()


def load_pipeline_companies() -> list[str]:
    entries = json.loads(PIPELINE.read_text(encoding="utf-8"))["entries"]
    companies = {e["company"].strip() for e in entries if e.get("stage") in ACTIVE_STAGES}
    return sorted(companies)


def main():
    ats_companies = load_ats_companies()
    pipeline_companies = load_pipeline_companies()

    missing = [c for c in pipeline_companies if c.lower() not in ats_companies]

    print(f"{len(pipeline_companies)} active-stage pipeline companies checked "
          f"against {len(ats_companies)} in JobWatch's ATS_BOARDS.")
    print(f"{len(missing)} not directly polled:\n")
    for c in missing:
        print(f"  {c}")
    print("\nCheck each for a Greenhouse/Ashby board and add its token to "
          "jobwatch/config.py's ATS_BOARDS if found.")


if __name__ == "__main__":
    main()
