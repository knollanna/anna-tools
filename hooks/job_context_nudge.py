#!/usr/bin/env python3
"""UserPromptSubmit hook — surface the job-search rule when the prompt is about the search.

Rules and skills are prose the model can drift from. This is the layer that
doesn't drift: whenever a prompt carries a job-search signal, the procedure and
the current file state get injected into context before the model answers.

It is deliberately dumb. It matches keywords and the company names already in the
tracker; it never reads or echoes the contents of `job/`, because that content is
private and injecting it wholesale would be both wasteful and a leak into every
transcript. It emits a pointer and nothing else.

Silent (exit 0, no output) when: `job/` is absent, the prompt has no signal, or
anything at all goes wrong. A hook that breaks a session is worse than a hook
that misses one nudge.

Wired on UserPromptSubmit. Reads the hook payload as JSON on stdin.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

# job/ follows Anna's content, not the plugin. If this resolved to the plugin root
# and the plugin were installed from a marketplace cache, the hook would go
# permanently and silently quiet.
JOB = _lib.data_home() / "job"
CONTEXT = JOB / "Anna_Job_Search_Context.md"
TRACKER_MD = JOB / "tracker.md"
TRACKER_HTML = JOB / "job_search_tracker.html"
RULE = _lib.plugin_root() / "rules" / "job-search.md"

# Phrases that mean "this is about the search" on their own.
SIGNALS = re.compile(
    r"""\b(
        interview(s|ed|ing)? | recruiter | hiring\s+manager | phone\s+screen
      | panel | take[-\s]?home | job\s+description | \bJD\b | job\s+post(ing)?
      | applied\s+(to|for) | application | referral | reject(ed|ion)
      | offer\s+letter | counter[-\s]?offer | comp\s+(range|band|conversation)
      | \bOTE\b | pipeline | candidacy | headhunter | onsite
      | job\s+search | new\s+role | reached\s+out\s+to
      | got\s+back\s+to\s+me | heard\s+back | next\s+steps
      | hiring\s+process | \bHM\b | screening\s+call | follow[-\s]?up\s+call
      | transcript | debrief | call\s+notes | spoke\s+with | met\s+with
    )\b""",
    re.I | re.X,
)

# "Notch (notch.cx)" -> "Notch"; "Cursor (Anysphere)" -> "Cursor".
PARENTHETICAL = re.compile(r"\s*\([^)]*\)\s*$")
NONWORD = re.compile(r"[^a-z0-9]+")


def slugify(company: str) -> str:
    """Must match scripts/job_scaffold.py, or the hook points at folders that
    do not exist."""
    return NONWORD.sub("-", PARENTHETICAL.sub("", company).strip().lower()).strip("-")

MAX_COMPANIES = 200


def companies() -> set[str]:
    """Company names already in the pipeline, from the generated tracker markdown."""
    if not TRACKER_MD.exists():
        return set()
    found = set()
    for line in TRACKER_MD.read_text(encoding="utf-8", errors="replace").splitlines():
        if line.startswith("### "):
            name = PARENTHETICAL.sub("", line[4:].split(" — ")[0]).strip()
            if len(name) > 3:
                found.add(name)
        if len(found) >= MAX_COMPANIES:
            break
    return found


def matched_companies(prompt: str) -> list[str]:
    """Single-word names match case-sensitively — "Notch" should not fire on "top-notch"."""
    hits = []
    for name in companies():
        flags = 0 if " " not in name else re.I
        if re.search(rf"\b{re.escape(name)}\b", prompt, flags):
            hits.append(name)
    return sorted(hits)


def last_updated() -> str:
    if not CONTEXT.exists():
        return "not found"
    for line in CONTEXT.read_text(encoding="utf-8", errors="replace").splitlines()[:10]:
        if "Last updated" in line:
            return "last updated " + line.split("Last updated")[1].strip(" :*_.")
    return "unknown"


def main() -> int:
    prompt = str(_lib.payload().get("prompt", ""))
    if not prompt or not JOB.is_dir():
        return 0

    hits = matched_companies(prompt)
    if not (SIGNALS.search(prompt) or hits):
        return 0

    stale = ""
    if TRACKER_HTML.exists() and TRACKER_MD.exists():
        if TRACKER_HTML.stat().st_mtime > TRACKER_MD.stat().st_mtime:
            stale = (
                f"- ⚠️ `{TRACKER_HTML}` is newer than the markdown. Run "
                f"`python3 {_lib.plugin_root() / 'scripts' / 'tracker_to_md.py'}` "
                "before relying on it."
            )

    # Absolute paths throughout: this fires in any repo, where a relative path
    # resolves against the wrong working directory.
    lines = [
        "This prompt looks like it concerns Anna's job search.",
        "",
        f"- **Read `{RULE}` before responding.** It defines what to capture and the hard rules.",
        f"- Pipeline context: `{CONTEXT}` ({last_updated()}).",
        f"- Greppable pipeline: `{TRACKER_MD}`.",
        "- If this shares an interview, transcript, call, application, rejection, or new "
        "company, **update the context doc and the tracker as part of this turn** — do not "
        "wait to be asked.",
        "- That directory is gitignored and private. Never commit it, publish it, or put it "
        "in an artifact.",
    ]
    if hits:
        lines.append(f"- Already in the pipeline: {', '.join(hits)}. Read the existing entry "
                     "before writing a new one, and never merge details across companies.")
        for name in hits:
            folder = JOB / "companies" / slugify(name)
            if folder.is_dir():
                lines.append(
                    f"  - **{name} has a folder: `{folder}`.** Read its `README.md` first; "
                    "it is the source of truth for this company. New transcripts go in "
                    "`transcripts/` as `YYYY-MM-DD-who.md`, research in `research/` so it "
                    "stops dying in chat sessions."
                )

    pending = sorted(p for p in (JOB / "inbox").glob("*.md") if p.name != "README.md")
    if pending:
        names = ", ".join(p.name for p in pending[:5])
        lines.append(
            f"- 📥 {len(pending)} unfiled item(s) in `{JOB / 'inbox'}`: {names}. "
            "Offer to file them into the right company folder."
        )

    if stale:
        lines.append(stale)

    _lib.emit("UserPromptSubmit", "\n".join(lines))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
