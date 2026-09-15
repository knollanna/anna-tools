#!/usr/bin/env python3
"""Check arbitrary text (a PR title, a PR body, anything not going through
`git commit`) for real job-search data, using the same term list as
check_job_leak.py.

Built because `.githooks/pre-commit` structurally can't cover this: a PR
title/body is a `gh pr create` / `gh pr edit` API call, not a git commit, so
no git hook ever sees it. Surfaced 2026-09-15 checking whether the same
session's own PR descriptions (drafted while fixing an unrelated real-name
leak) had restated any of the real names as part of explaining the fix —
they hadn't, checked and confirmed clean, but nothing had actually stopped
that from happening; the git hook covers commits, not this. This is the
gap that leaves.

Server-side (a GitHub Action) isn't a clean fix either: job/pipeline.json
is gitignored on purpose and never leaves this machine, so a cloud check
would need its own copy of the sensitive-terms list to check against,
which defeats the point. This has to run locally, before the `gh` call
goes out — which also means it's a discipline step, not a guarantee the
way the git hook is. Run it on every PR title/body before submitting one:

    echo "$TITLE"$'\n'"$BODY" | python3 scripts/check_text_leak.py
    python3 scripts/check_text_leak.py < body.txt
    python3 scripts/check_text_leak.py "some string directly"

Exit 0 and silent if clean. Exit 1 and prints every match if not — no
override flag, unlike the git hooks: this never blocks anything on its
own (it isn't wired to a git operation), it's a check you choose to run,
so there's nothing to override.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_job_leak import load_sensitive_terms  # noqa: E402

# The standard attribution footer this session adds to every PR body — a
# guaranteed hit otherwise, since "Claude Code" gets pulled in as a bigram
# from job/pipeline.json's own notes (it's a real tool mentioned there, just
# never the identifying part of anything). Stripped before checking rather
# than allowlisted as a term, since it's fixed, known boilerplate text, not
# a term that might legitimately need to fire in some other sentence.
FOOTER_RE = re.compile(r"\n?.*Generated with \[Claude Code\].*", re.IGNORECASE)

# Well-known generic product/technology names, or Anna's own public resume
# content, that also happen to coincide with a real term in job/pipeline.json
# (Neo4j is anna-tools'/FareWatch's own database; Stripe is a generic
# secret-format reference in check_secrets.py; Google is Drive/Calendar/Cloud/
# Fonts referenced constantly in this codebase's own docs; Employee Experience
# is a Salesforce product name from resume/full.md's own career history,
# in-scope per that file's own rule). Excluded because in THIS checker's
# actual use — reviewing a PR description before submitting — they fire on
# ordinary narration far more often than on an actual leak, and a check
# ignored out of habit protects nothing. Add to sparingly: each entry trades
# away real coverage of that one term everywhere in the pipeline, not just in
# the generic/resume sense a given PR happened to use it in.
ALLOWLIST = {"Neo4j", "Stripe", "Google", "Employee Experience"}


def find_hits(text: str, terms: set[str]) -> list[str]:
    text = FOOTER_RE.sub("", text)
    return sorted({term for term in terms if term in text and term not in ALLOWLIST})


def main() -> int:
    if len(sys.argv) > 1:
        text = " ".join(sys.argv[1:])
    else:
        text = sys.stdin.read()

    terms = load_sensitive_terms()
    if not terms:
        return 0  # no pipeline data on this clone

    hits = find_hits(text, terms)
    if not hits:
        return 0

    print("\U0001F6D1 check_text_leak: this text contains real job-search data:\n")
    for term in hits:
        print(f"  {term!r}")
    print(
        "\nThis matches job/pipeline.json (a company or named contact). A PR "
        "title/body is public the moment it's submitted — job/ never leaves "
        "this machine, so nothing from it belongs here either, same as any "
        "tracked file."
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
