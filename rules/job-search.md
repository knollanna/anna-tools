---
description: How to maintain the job-search context and pipeline tracker when Anna shares an interview, a transcript, a recruiter call, or a new application.
profiles: [tooling]
detect: ["job"]
---

# Job search

**Everything under `job/` is gitignored and stays that way.** It holds current employment
status, compensation targets, named contacts at companies Anna is interviewing with, and
candid assessments of both the companies and her own gaps. It must never be committed, pasted
into an artifact, published, or included in anything that leaves the machine. If a task seems
to need it in a shareable form, stop and ask.

**The specifics live in `job/`, not in this file.** This rule is tracked in git; the numbers,
names, and status are not. Don't copy them up here.

## The files

**One fact, one home.** Every piece of information has exactly one place it is written, and
everything else is either generated from it or points at it. When the same fact lived in four
files, a declined company sat at "interviewing" for a week and a misspelled name survived three
corrections. That is the failure this layout exists to prevent.

| File | What it is | Edited how |
| --- | --- | --- |
| `job/pipeline.json` | **Source of truth for stage** and the standing note on every company. | By hand or by a session |
| `job/companies/<slug>/` | One folder per active company. **Source of truth for everything else about that company.** | By hand and by session |
| `job/Anna_Job_Search_Context.md` | The orienting doc: background, criteria, talking points. | By hand, in place |
| `job/inbox/` | Drop point for unfiled captures. | Anna pastes; a session files them |
| `job/tracker.md` | Greppable pipeline. **Generated.** | `python3 scripts/board.py` |
| `job/board.html` | Visual kanban board. **Generated.** | `python3 scripts/board.py` |

**Never hand-edit `tracker.md` or `board.html`.** They are outputs; the next run overwrites
them. `python3 scripts/board.py --check` reports whether they are current, and the
`job_context_nudge` hook warns when `pipeline.json` is newer than its views.

`job/archive/` holds the original hand-maintained HTML tracker. It is not live and nothing
reads it.

### When a stage changes

1. Update `stage` in `pipeline.json` (and the `note`, so the board reads usefully).
2. Update the company's `README.md` if it has a folder — the *why* lives there, not in the
   board note.
3. Run `python3 scripts/board.py`.

That is the whole ritual. There is no separate tracker to maintain.

### Inside a company folder

```
companies/<slug>/
├── README.md                 the standing picture: where it stands, what I know, open questions
├── jd/YYYY-MM-DD-role.md     the posting or req text, every version
├── transcripts/YYYY-MM-DD-who.md
├── prep/YYYY-MM-DD-panel-prompt.md
└── research/funding-and-customers.md
```

**Save the JD the day it arrives, and keep every version.** A posting is the only written
statement of what the company says it wants, it is what an application gets measured against,
and it gets edited quietly — a JD that gains or loses a hard requirement between the screen and
the offer is evidence, and you only have it if you kept both. Postings also disappear once the
req closes.

Folders are per **company**, not per requisition. A company can have three separate entries in
the tracker and still be one relationship, and a transcript belongs to the relationship.
Create new ones with `python3 scripts/job_scaffold.py` (idempotent; never overwrites an
existing README).

Read the company's `README.md` before answering anything about that company, and the orienting
doc for anything about the search as a whole. Working from a partial view is how companies get
blended.

### Transcripts

- Filename `YYYY-MM-DD-who.md`, e.g. `2026-08-11-first-last.md`. Date first so it sorts.
  Lowercase, hyphens.
- **Summary at the top, raw verbatim at the bottom.** Anyone reading usually wants the three
  bullets; the raw is there for when the exact words matter. Never edit the raw.
- Granola encrypts its local store (`granola.db` has no SQLite header, the cache is `.enc`), so
  there is no automated export. Anna copies from the UI — either pasting into a session, or
  dropping a file in `job/inbox/`.
- Paste both Granola panes under `## Granola notes` and `## Raw`. The summary is Granola's
  interpretation; the raw is the ground truth and they are not interchangeable.
- **Anna does not write the summary.** She captures; the session summarizes against this rule.

### The inbox

Anything in `job/inbox/` is unfiled. The `job_context_nudge` hook reports the count on any
job-related prompt. Offer to file them: move into the right `companies/<slug>/transcripts/`,
add frontmatter and a summary, update the company README and the tracker. An empty inbox is
the goal.

## When to update

Any of these, without being asked:

- An interview, recruiter call, HM call, panel, or peer call happened
- A transcript or notes get shared
- A new application goes out, or a new company enters the picture
- A rejection, an offer, a stage change, or a role/title/comp clarification
- New research on a company already in the pipeline
- A contact name, title, or role gets corrected

## What to capture

Match the existing house style. It is dense on purpose and it works.

- **Date every event and say what kind it was.** `CALL HELD Aug 11, 2026 with Nir (COO) and
  Yuval (CTO)`. `RECRUITER CALL HELD Aug 5/6, 2026`. `Applied Aug 11, 2026`.
- **Get dates from `date`, never from memory or mental arithmetic.** Convert "last Tuesday"
  to an absolute date before writing it down.
- **Bold the flags.** `**FLAG — HARD REQUIREMENT:**`, `**ROLE-TYPE FLAG:**`,
  `**STRUCTURAL FLAG:**`, `**Comp/level unresolved:**`. These are what Anna scans for.
- **Name gaps honestly.** "Anna does not have hands-on SIEM/identity/cloud-security-architecture
  experience" is more useful than a hedge. The point of the file is to stop her walking into a
  room unprepared. Never soften a gap and never inflate a match.
- **Separate what was said from what was inferred.** "per Daniel", "founder framing on an
  unpriced structure, not a confirmed valuation", "name/title to be confirmed".
- **Always end an entry with next steps**, numbered, with who owns each.
- **Company research worth keeping:** funding and round, valuation, headcount and split,
  named customers, founders, the posted comp range measured against Anna's stated floor, and
  anything that changes the risk profile.
- **Update the `Last updated:` line** at the top of the context doc.

## Hard rules

- **Never blend companies.** Each company, its product, its people, and its process are
  distinct. A detail from one entry must never migrate into another. This is the single most
  common failure mode on a long pipeline and it is the one Anna notices.
- **Never invent a contact, date, title, comp figure, or funding number.** If it wasn't said
  or sourced, mark it TBD.
- **Don't drop history.** Entries accumulate. A stage change appends; it does not erase what
  came before. The record of how a process went is the value.
- **Keep the tracker and the context doc consistent.** If a stage changes in one, change it in
  the other. After the HTML tracker is regenerated, re-run `scripts/tracker_to_md.py`.
- **Never put job-search detail in a tracked file**, in `resume/`, on annaknoll.com, or in any
  artifact. The site rule "keep private job-search details off the page" applies everywhere.

## Standing context

- **Comp floor and target role shape are stated in `job/Anna_Job_Search_Context.md`** under
  "What Anna is looking for". Read them there. State the floor matter-of-factly when it comes
  up; never negotiate it down in a draft, and never write the figure into a tracked file.
- The `resume/` files are the canonical career background. Pull from `resume/full.md` and
  `resume/stories.md` when drafting applications; where they disagree with the job context
  doc on a career fact, the resume wins.
