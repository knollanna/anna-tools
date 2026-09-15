#!/usr/bin/env python3
"""Pre-commit check: block a commit that introduces real job-search data
(company names, named contacts) outside job/.

Built after a public-exposure audit (2026-09-15) found real pipeline
data — a named contact and rejection reason, a real company, a real
interview date — had leaked into docstrings and comments as "worked
examples" across 8+ files and several commit messages, all while job/
itself was correctly gitignored the entire time. The failure mode was
never job/ leaking; it was someone (a session, a person) typing a real
name into a comment because it was the detail actually in front of them.
Doctrine alone didn't catch it happening twice in one session — this is
the guarantee-not-habit hook that does, same reasoning as
guard_mcp_readonly.py.

Checks only ADDED lines in the staged diff (not the whole file — an
already-committed false positive shouldn't re-block every future commit
to that file), excludes job/ itself (where this data belongs), and
extracts what counts as "real" directly from job/pipeline.json so the
check tracks the data instead of a hardcoded, staleness-prone list.

Deliberately noisy over silent: a false positive costs one look at a
diff; a missed real leak costs a public repo. Override for a confirmed
false positive:

    SKIP_JOB_LEAK_CHECK=1 git commit ...

    .githooks/pre-commit -> scripts/check_job_leak.py (this file)
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
PIPELINE = REPO / "job" / "pipeline.json"

# Matches graph_import.py's own CONTACT_RE so name extraction doesn't drift
# from what the graph importer already treats as "a name".
CONTACT_RE = re.compile(r"([A-Z][\w.'-]*(?:\s+[A-Z]?[\w.'-]+)*)\s*\(([^)]*)\)")

# Two-or-more-capitalized-word runs in free text (note fields) — the same
# pattern used to build the candidate list during the 2026-09-15 audit.
# Noisier than CONTACT_RE (catches role titles too), kept anyway: this is
# exactly the field the real leaks came from.
BIGRAM_RE = re.compile(r"\b[A-Z][a-z]{2,}(?:\.)? [A-Z][a-zA-Z\-]{2,}\b")

# Below this length a term is too likely to collide with ordinary prose
# ("In UI", "Data Cloud") to be worth blocking a commit over.
MIN_TERM_LEN = 5


def load_sensitive_terms() -> set[str]:
    if not PIPELINE.exists():
        return set()
    try:
        data = json.loads(PIPELINE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return set()

    terms = set()
    for e in data.get("entries", []):
        company = (e.get("company") or "").strip()
        if company:
            terms.add(company)
        contacts = e.get("contacts") or ""
        for name, _detail in CONTACT_RE.findall(contacts):
            name = name.strip().rstrip(",")
            if name:
                terms.add(name)
        for field in ("note", "notes"):
            text = e.get(field) or ""
            terms.update(BIGRAM_RE.findall(text))

    return {t for t in terms if len(t) >= MIN_TERM_LEN}


def staged_added_lines() -> dict[str, list[tuple[int, str]]]:
    """{path: [(line_no, text), ...]} for every ADDED line in the staged
    diff, excluding job/ (where this data is supposed to live) and binary
    files. Line numbers are in the new file, 1-indexed."""
    out = subprocess.run(
        ["git", "diff", "--cached", "-U0", "--no-color", "--", ".", ":!job/"],
        cwd=REPO, capture_output=True, text=True, check=False,
    ).stdout

    result: dict[str, list[tuple[int, str]]] = {}
    current_file = None
    current_line = None
    for line in out.splitlines():
        if line.startswith("+++ "):
            path = line[4:]
            current_file = None if path == "/dev/null" else path[2:]  # strip "b/"
            continue
        if line.startswith("@@"):
            m = re.search(r"\+(\d+)", line)
            current_line = int(m.group(1)) if m else None
            continue
        if current_file and current_line is not None and line.startswith("+") and not line.startswith("+++"):
            result.setdefault(current_file, []).append((current_line, line[1:]))
            current_line += 1
        elif current_file and current_line is not None and not line.startswith("-"):
            current_line += 1
    return result


def main() -> int:
    import os
    if os.environ.get("SKIP_JOB_LEAK_CHECK"):
        return 0

    terms = load_sensitive_terms()
    if not terms:
        return 0  # no pipeline data yet, or job/ isn't set up on this clone

    added = staged_added_lines()
    if not added:
        return 0

    hits = []
    for path, lines in added.items():
        for line_no, text in lines:
            for term in terms:
                if term in text:
                    hits.append((path, line_no, term, text.strip()))

    if not hits:
        return 0

    print("\n\U0001F6D1 check_job_leak: staged changes contain real job-search data:\n")
    for path, line_no, term, text in hits:
        print(f"  {path}:{line_no}  matched {term!r}")
        print(f"    {text[:120]}")
    print(
        "\nThis matches data in job/pipeline.json (companies, named contacts, or a\n"
        "note-field phrase). job/ is gitignored on purpose — nothing from it belongs\n"
        "in a tracked file, even as a \"worked example\" in a comment.\n\n"
        "If every match above is a genuine false positive (coincidental overlap, not\n"
        "real pipeline data), override once with:\n\n"
        "    SKIP_JOB_LEAK_CHECK=1 git commit ...\n"
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
