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

Only open-stage entries (job/pipeline.json's stages minus lost/dropped/
noresponse — see _neo4j.OPEN_STAGES) are checked; a title from a dead lead
isn't worth chasing.

Writes candidates to job/title_match_candidates.json for review.

    .venv/bin/python3 scripts/title_match_suggest.py [--threshold 80]
"""

import argparse
import json

from rapidfuzz import fuzz

from _neo4j import OPEN_STAGES, REPO, load_jobwatch_config_names

PIPELINE = REPO / "job" / "pipeline.json"
CANDIDATES_OUT = REPO / "job" / "title_match_candidates.json"

# Below this length, a substring hit is as likely to be a coincidence (a
# short acronym like "AI" or "SE" appearing inside an unrelated title) as a
# real match - fall through to the fuzzy pass instead of trusting it outright.
MIN_SUBSTRING_LEN = 6


def load_jobwatch_phrases() -> list[str]:
    config = load_jobwatch_config_names("ADZUNA_PHRASES", "ATS_TITLE_KEYWORDS")
    return [*config["ADZUNA_PHRASES"], *config["ATS_TITLE_KEYWORDS"]]


def load_pipeline_titles() -> list[str]:
    entries = json.loads(PIPELINE.read_text(encoding="utf-8"))["entries"]
    titles = {
        e["role"].strip()
        for e in entries
        if e.get("stage") in OPEN_STAGES and e.get("role", "").strip()
    }
    return sorted(titles)


def is_covered(title: str, phrases: list[str], threshold: int) -> tuple[bool, str | None]:
    t = title.lower()
    for phrase in phrases:
        p = phrase.lower()
        shorter, longer = (p, t) if len(p) <= len(t) else (t, p)
        if len(shorter) >= MIN_SUBSTRING_LEN and shorter in longer:
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

    print(f"{len(titles)} open-stage pipeline titles checked against "
          f"{len(phrases)} JobWatch phrases/keywords.")
    print(f"{len(candidates)} uncovered, written to {CANDIDATES_OUT.relative_to(REPO)}\n")
    for c in candidates:
        print(f"  {c['title']!r}")


if __name__ == "__main__":
    main()
