#!/usr/bin/env python3
"""Suggest JobWatch search-phrase/keyword additions from titles already in
job/pipeline.json that JobWatch's config.py doesn't cover.

The pipeline records the actual titles companies use ("Head of Solutions
Consulting", not the shape of a search phrase); JobWatch only ever finds a
posting whose title lands within ADZUNA_PHRASES (exact-phrase Adzuna search)
or ATS_TITLE_KEYWORDS (substring filter on ATS-board postings). A pipeline
entry proves that title shape exists in the wild — every one JobWatch's
config doesn't already cover is a title JobWatch is silently blind to.

Two passes, same as company_aliases_suggest.py: substring match first (catches
"applied ai lead" containing "applied ai" outright), then a rapidfuzz fallback
for near-misses ("Head of Solutions Consulting" vs "Head of Solutions
Engineering"). Suggestions only — nothing is auto-applied. Approving one means
adding it to jobwatch/config.py by hand.

Only active-stage entries (applied/considering/outreach/warm/followup) are
checked; a title from a dead lead isn't worth chasing.

Writes candidates to job/title_match_candidates.json for review.

    .venv/bin/python3 scripts/title_match_suggest.py [--threshold 80]
"""

import argparse
import ast
import json
from pathlib import Path

from rapidfuzz import fuzz

from _neo4j import REPO

PIPELINE = REPO / "job" / "pipeline.json"
JOBWATCH_CONFIG = REPO.parent / "jobwatch" / "config.py"
CANDIDATES_OUT = REPO / "job" / "title_match_candidates.json"

ACTIVE_STAGES = {"applied", "considering", "outreach", "warm", "followup"}


def load_jobwatch_phrases() -> list[str]:
    """Pull ADZUNA_PHRASES + ATS_TITLE_KEYWORDS out of jobwatch/config.py
    without importing it (keeps this script out of JobWatch's own venv/deps)."""
    tree = ast.parse(JOBWATCH_CONFIG.read_text(encoding="utf-8"))
    phrases = []
    wanted = {"ADZUNA_PHRASES", "ATS_TITLE_KEYWORDS"}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            if isinstance(target, ast.Name) and target.id in wanted:
                phrases.extend(ast.literal_eval(node.value))
    return phrases


def load_pipeline_titles() -> list[str]:
    entries = json.loads(PIPELINE.read_text(encoding="utf-8"))["entries"]
    titles = {
        e["role"].strip()
        for e in entries
        if e.get("stage") in ACTIVE_STAGES and e.get("role", "").strip()
    }
    return sorted(titles)


def is_covered(title: str, phrases: list[str], threshold: int) -> tuple[bool, str | None]:
    t = title.lower()
    for phrase in phrases:
        if phrase.lower() in t or t in phrase.lower():
            return True, phrase
    best_phrase, best_score = None, 0
    for phrase in phrases:
        score = fuzz.ratio(t, phrase.lower())
        if score > best_score:
            best_phrase, best_score = phrase, score
    if best_score >= threshold:
        return True, best_phrase
    return False, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--threshold", type=int, default=80)
    args = parser.parse_args()

    phrases = load_jobwatch_phrases()
    titles = load_pipeline_titles()

    candidates = []
    for title in titles:
        covered, match = is_covered(title, phrases, args.threshold)
        if not covered:
            candidates.append({"title": title})

    CANDIDATES_OUT.write_text(json.dumps(candidates, indent=2) + "\n")

    print(f"{len(titles)} active-stage pipeline titles checked against "
          f"{len(phrases)} JobWatch phrases/keywords.")
    print(f"{len(candidates)} uncovered, written to {CANDIDATES_OUT.relative_to(REPO)}\n")
    for c in candidates:
        print(f"  {c['title']!r}")


if __name__ == "__main__":
    main()
