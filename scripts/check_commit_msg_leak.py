#!/usr/bin/env python3
"""commit-msg hook: block a commit whose MESSAGE — not just its diff —
contains real job-search data.

check_job_leak.py's pre-commit hook only ever checked staged file changes.
It never saw the commit message itself, and that gap is exactly how real
contact names ended up permanently public: written into commit messages as
"verification evidence" ("Real names surface cleanly (Name One, Name Two,
Name Three...)"), a channel no hook covered. Surfaced 2026-09-17 during a
public-exposure sweep that checked commit messages for the first time —
three separate commits had done this.

Reuses check_job_leak.py's load_sensitive_terms() so the two hooks track
the same data instead of drifting apart.

Git passes the message as a file path in argv[1] at the commit-msg stage —
unlike pre-commit, the message has already been written by then. Override
for a confirmed false positive:

    SKIP_JOB_LEAK_CHECK=1 git commit ...

    .githooks/commit-msg -> scripts/check_commit_msg_leak.py (this file)
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_job_leak import load_sensitive_terms  # noqa: E402


def main() -> int:
    if os.environ.get("SKIP_JOB_LEAK_CHECK"):
        return 0

    if len(sys.argv) < 2:
        return 0  # git always passes this at the commit-msg stage; nothing to check without it

    try:
        text = Path(sys.argv[1]).read_text(encoding="utf-8")
    except OSError:
        return 0

    terms = load_sensitive_terms()
    if not terms:
        return 0  # no pipeline data yet, or job/ isn't set up on this clone

    hits = sorted({term for term in terms if term in text})
    if not hits:
        return 0

    print("\n\U0001F6D1 check_commit_msg_leak: this commit message contains real job-search data:\n")
    for term in hits:
        print(f"  {term!r}")
    print(
        "\nThis matches data in job/pipeline.json (companies, named contacts, or a\n"
        "note-field phrase). A commit message is exactly as public as the diff it\n"
        "describes — don't cite real pipeline data as evidence of what a script found\n"
        "or verified, even in passing. Describe counts and categories instead\n"
        "(\"verified against 18 real entries by eye\"), never the actual values.\n\n"
        "If every match above is a genuine false positive (coincidental overlap, not\n"
        "real pipeline data), override once with:\n\n"
        "    SKIP_JOB_LEAK_CHECK=1 git commit ...\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
