---
description: How to maintain the job-search context and pipeline tracker when Anna shares an interview, a transcript, a recruiter call, or a new application.
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

| File | What it is | Edited how |
| --- | --- | --- |
| `job/Anna_Job_Search_Context.md` | The orienting doc. Background, criteria, full pipeline, talking points, company quick reference. | By hand, in place |
| `job/job_search_tracker.html` | The interactive pipeline artifact. Source of truth for stage and status. | Regenerated as an artifact |
| `job/tracker.md` | Greppable markdown of the tracker. | `python3 scripts/tracker_to_md.py` — never by hand |

Read `job/Anna_Job_Search_Context.md` before answering anything about the search. It is long;
read it anyway. Working from a partial view is how companies get blended.

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
