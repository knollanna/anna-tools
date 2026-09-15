#!/usr/bin/env python3
"""Suggest contact_name candidates for pipeline entries with a found warm
path but no contact_name recorded yet.

human_path.summary already names a contact when one was found - "Ed
Sandoval, Senior Product Manager AI - LinkedIn connection" - but as free
prose, not the structured contact_name field job_digest.py actually reads.
This doesn't guess *which* name is the primary contact when a summary lists
several (a later warm_path.py pass can turn up more than one lead) - it
surfaces every capitalized-name-shaped candidate per entry and leaves
picking (and copying into pipeline.json) to a human review pass, same
"suggest, never invent" rule as company_aliases_suggest.py.

Writes candidates to job/contact_name_candidates.json for review. Never
writes to pipeline.json - approving one means copying the name into that
entry's human_path.contact_name by hand or in a session.

    .venv/bin/python3 scripts/warm_contact_suggest.py
"""

import json
import re

from _neo4j import REPO

PIPELINE = REPO / "job" / "pipeline.json"
CANDIDATES_OUT = REPO / "job" / "contact_name_candidates.json"

# Same shape as check_job_leak.py's BIGRAM_RE: two-or-more capitalized-word
# runs. Noisier than a strict name pattern (catches role-title language too)
# - deliberately over-inclusive since a human reviews the output, and a
# missed real name is worse than an extra candidate to discard by eye.
NAME_RE = re.compile(r"\b[A-Z][a-z]{1,}(?:\.)? [A-Z][a-zA-Z\-']{1,}\b")

# Role-title / rung-language bigrams that would otherwise show up as
# false-positive "names" - extend this list as real summaries surface more.
_STOPWORDS = {
    "Senior Director", "Sr Director", "Sr. Director", "Vice President",
    "Product Manager", "Solutions Engineer", "Solutions Architect",
    "Solution Architect", "Team Lead", "Partner Architecture",
    "Partner Architect", "Sr. Partner", "Direct LinkedIn",
    "LinkedIn Connection", "Mutual Connection", "Found While",
    "Strongest Lead", "Still Warm", "Not Yet", "Global Specialist",
    "Sales Strategist", "Account Mgmt", "Talent Acquisition",
    "Enterprise GTM", "Enterprise AI", "Platform Sales", "Director SE",
    "Director CX", "Director Responsible", "Revenue Operations",
    "Lead Developer", "Lead Agentforce", "Service Solution",
    "Senior Talent", "Senior AI",
}


def load_pending_entries() -> list[dict]:
    data = json.loads(PIPELINE.read_text(encoding="utf-8"))
    out = []
    for e in data["entries"]:
        hp = e.get("human_path")
        if not hp or hp.get("best_rung") in (None, "none"):
            continue
        if hp.get("contact_name"):
            continue  # already filled in
        if not hp.get("summary"):
            continue
        out.append(e)
    return out


def candidate_names(summary: str, company: str) -> list[str]:
    found = []
    for match in NAME_RE.findall(summary):
        if match in _STOPWORDS or match in found or match == company:
            continue
        found.append(match)
    return found


def main():
    entries = load_pending_entries()
    candidates = []
    for e in entries:
        hp = e["human_path"]
        candidates.append({
            "id": e["id"],
            "company": e["company"],
            "best_rung": hp.get("best_rung"),
            "summary": hp["summary"],
            "name_candidates": candidate_names(hp["summary"], e["company"]),
        })

    CANDIDATES_OUT.write_text(json.dumps(candidates, indent=2) + "\n")

    print(f"{len(entries)} entries with a found warm path and no contact_name yet, "
          f"written to {CANDIDATES_OUT.relative_to(REPO)} for review.\n")
    for c in candidates:
        names = ", ".join(c["name_candidates"]) or "(no candidate found - check by hand)"
        print(f"  {c['company']}: {names}")
    print("\nApprove by copying the right name into that entry's "
          "human_path.contact_name in job/pipeline.json - this script never writes there.")


if __name__ == "__main__":
    main()
