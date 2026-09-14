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

import json
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
PIPELINE = JOB / "pipeline.json"
RULE = _lib.plugin_root() / "rules" / "job-search.md"
BOARD = _lib.plugin_root() / "scripts" / "board.py"
OBJECTION_REPORT = _lib.plugin_root() / "scripts" / "objection_report.py"
WARM_PATH = _lib.plugin_root() / "scripts" / "warm_path.py"
HUMAN_PATH_REPORT = _lib.plugin_root() / "scripts" / "human_path_report.py"

CLOSED_STAGES = {"lost", "dropped", "noresponse"}
GATED_STAGES = {"considering", "outreach"}

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

# Strip a trailing parenthetical so a heading like "Name (domain.com)" still
# matches a bare mention of "Name" in a prompt.
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
    """Single-word names match case-sensitively, so a short company name that is also a
    common English word does not fire on every casual use of that word."""
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


def pipeline_entries() -> list[dict]:
    if not PIPELINE.exists():
        return []
    try:
        data = json.loads(PIPELINE.read_text(encoding="utf-8"))
    except Exception:
        return []
    return data.get("entries", [])


def unclassified_closed_count(entries: list[dict]) -> int:
    """Closed entries (lost/dropped/noresponse) with no `objection` field yet.
    Mirrors the inbox count below: a count computed here fires on every relevant
    prompt, so it can't be forgotten the way a prose reminder can."""
    return sum(
        1 for e in entries
        if e.get("stage") in CLOSED_STAGES and not e.get("objection")
    )


def pending_human_path_count(entries: list[dict]) -> int:
    """considering/outreach entries with no `human_path` logged yet. Same shape
    as unclassified_closed_count: a count that fires on every relevant prompt
    so the warm-path check isn't something a session has to remember to run."""
    return sum(
        1 for e in entries
        if e.get("stage") in GATED_STAGES and not e.get("human_path")
    )


def gated_hits_missing_human_path(entries: list[dict], hits: list[str]) -> list[tuple[str, list[str]]]:
    """(company, stages) for each hit with at least one gated-stage entry
    missing human_path — the targeted warning, fired exactly when a company is
    named and about to be acted on rather than buried in the global count
    above. Grouped by company: a company with two open reqs (e.g. two
    `outreach` entries) reports once with both stages, not one identical
    warning line per entry.

    hits come from matched_companies(), which strips a trailing parenthetical
    (companies() does the same PARENTHETICAL.sub before adding a name to the
    set) so a heading like "Cursor (Anysphere)" still matches a bare mention
    of "Cursor". A pipeline entry's raw `company` field keeps the parenthetical,
    so it must be stripped the same way before comparing against hits — an
    exact-string compare here would silently never match any such company."""
    by_company: dict[str, list[str]] = {}
    for e in entries:
        company = e.get("company", "")
        stripped = PARENTHETICAL.sub("", company).strip()
        if (
            stripped in hits
            and e.get("stage") in GATED_STAGES
            and not e.get("human_path")
        ):
            by_company.setdefault(company, []).append(e["stage"])
    return sorted(by_company.items())


def main() -> int:
    prompt = str(_lib.payload().get("prompt", ""))
    if not prompt or not JOB.is_dir():
        return 0

    hits = matched_companies(prompt)
    if not (SIGNALS.search(prompt) or hits):
        return 0

    # Read once and reuse — pipeline.json is real-sized (hundreds of entries),
    # and this hook runs on every job-search-flavored prompt, so re-reading and
    # re-parsing it per counter below adds up.
    entries = pipeline_entries()

    # pipeline.json is the only place a stage is written; the two views are
    # generated. If the data is newer than a view, the view is lying.
    stale = ""
    if PIPELINE.exists() and TRACKER_MD.exists():
        if PIPELINE.stat().st_mtime > TRACKER_MD.stat().st_mtime:
            stale = (
                f"- ⚠️ `pipeline.json` is newer than the generated views. Run "
                f"`python3 {BOARD}` before relying on `tracker.md` or `board.html`."
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
        for company, stages in gated_hits_missing_human_path(entries, hits):
            stage_label = "/".join(f"`{s}`" for s in sorted(set(stages)))
            lines.append(
                f"  - ⚠️ {company} is at {stage_label} with no warm-path check logged. Run "
                f"`python3 {WARM_PATH} \"{company}\"` (and check for alumni overlap or a named "
                "hiring manager/recruiter by hand) before applying."
            )

    pending = sorted(p for p in (JOB / "inbox").glob("*.md") if p.name != "README.md")
    if pending:
        names = ", ".join(p.name for p in pending[:5])
        lines.append(
            f"- 📥 {len(pending)} unfiled item(s) in `{JOB / 'inbox'}`: {names}. "
            "Offer to file them into the right company folder."
        )

    unclassified = unclassified_closed_count(entries)
    if unclassified:
        lines.append(
            f"- 🏷️ {unclassified} closed entr{'y has' if unclassified == 1 else 'ies have'} no "
            f"objection classification yet. Run `python3 {OBJECTION_REPORT}` to see suggestions."
        )

    pending_warm = pending_human_path_count(entries)
    if pending_warm:
        lines.append(
            f"- 🤝 {pending_warm} `considering`/`outreach` entr{'y has' if pending_warm == 1 else 'ies have'} "
            f"no warm-path check logged. Run `python3 {HUMAN_PATH_REPORT}` to see who's still "
            "unchecked before any of them move to `applied`."
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
