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

**`transcripts/` is for calls with the company. A call with a third party *about* a company goes
in that company's `research/`** — a friend at a competitor briefing Anna on the market is
research, not a candidate conversation, and filing it as a transcript would imply contact that
never happened. When one conversation carries facts about two companies, split it: the record
goes where its subject is, and the other company's folder gets the part that belongs to it.

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

## Gmail rejection sweeps

When checking Gmail for a rejection (an objection-classification backfill, or just
"did I hear back from X"), never lock a search to an exact multi-word quoted phrase like
`"not moving forward"`. Real rejection emails vary the words *around* a phrase more than
the phrase itself — "we will **not be** moving forward" doesn't contain the substring "not
moving forward" and a phrase-locked query silently misses it, with no error, no empty-result
warning distinguishing "nothing to find" from "the query was too rigid." A real rejection
was missed exactly this way before this note existed.

Search on the shorter, more stable fragment instead (`"moving forward"`, not `"not moving
forward"`), or drop the phrase entirely for single strong words (`reject`, `rejected`,
`unfortunately`, `"other candidate"`, `"position has been filled"`, `"not selected"`) and
OR them together. Broad-and-cross-reference beats narrow-and-precise here: a mailbox-wide
sweep with loose terms, checked against company names already in the pipeline, catches more
than one exact-phrase query per company. Run this against `applied`-stage entries too, not
just closed ones — a rejection can land before anyone updates the stage.

## What to capture

Match the existing house style. It is dense on purpose and it works.

- **Date every event and say what kind it was.** `CALL HELD Aug 11, 2026 with Sam (COO) and
  Robin (CTO)`. `RECRUITER CALL HELD Aug 5/6, 2026`. `Applied Aug 11, 2026`.
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
  the other. `scripts/board.py` regenerates both `tracker.md` and `board.html` from
  `pipeline.json` in a single run — there is no separate step for the markdown tracker.
- **Never put job-search detail in a tracked file**, in `resume/`, on annaknoll.com, or in any
  artifact. The site rule "keep private job-search details off the page" applies everywhere.

## Objection classification

A closed entry (`lost`, `dropped`, `noresponse`) can carry an `objection` object —
`stated`, `inferred_class` (`domain-proof-gap` · `level-mismatch` · `location` ·
`comp` · `slate` · `culture-style` · `unknown`), `confidence`, and `note`. Classify
by hand or by a session from what the record actually says; never invent `stated`.
Three entries in the same `inferred_class` is a positioning problem, not luck.
`job_context_nudge.py` reports how many closed entries still need one on any
job-search-relevant prompt — `python3 scripts/objection_report.py` proposes a class
per entry from its note text (confirm or correct, it never writes).

## Warm-path check

A `considering` or `outreach` entry can carry a `human_path` object —
`checked` (date), `rungs_checked` (which of `pipeline`, `linkedin`, `alumni`,
`named-contact`, `mutual-connection` were actually attempted), `best_rung`
(the highest that succeeded, or `"none"`), `summary`, and an optional `note`.
Log one before the
entry moves to `applied`. `best_rung: "none"` is a legitimate, honest answer —
it's still correct to apply cold — but the field records that the question was
actually asked. An absent `human_path` means *unchecked*, not *checked, nothing
found*; don't leave it off once a check has run.

`best_rung` can also be `"mutual-connection"` — a 2nd-degree LinkedIn lead
surfaced via LinkedIn's own "mutual connections" widget on someone's profile,
where the mutual is a person Anna already knows well (a pipeline contact or
1st-degree connection), not something the graph query finds on its own.
Confirm with Anna which company the profile is actually at before logging it —
a title alone (e.g. "Product Manager, AI Platforms") is never enough.

`python3 scripts/warm_path.py "<Company>"` answers rungs 1-2 (pipeline contacts,
direct LinkedIn connections) from the Neo4j graph. Alumni overlap and naming a
hiring manager or recruiter (rungs 3-4) need a manual/WebSearch pass — the graph
has no data to answer those, and this is the one part of `human_path` a session
proposes from judgment rather than a query result. Never invent `summary` or
`best_rung`; mark `"none"` honestly rather than guessing at a path that wasn't
actually found.

### Outreach status

Once `best_rung` isn't `"none"`, `human_path` can also carry `outreach` —
tri-state, tracking whether the found lead actually got used:

- absent / `null` — pending, nobody's reached out yet.
- a date string (`"2026-09-16"`) — Anna reported contacting them.
- `"skipped"` — Anna deliberately decided not to use this lead (too weak,
  bad timing); the reason goes in `human_path.note`.

Set this from what Anna actually reports, same as everything else here —
never mark a lead contacted or skipped without her saying so. A found lead
is worth using at any live stage, not just before applying: `outreach`
applies through `considering`/`outreach`/`applied`/`warm`/`followup` alike,
wider than the `human_path` gate itself, since a warm contact found after
applying can still help get noticed or get a referral into the process.

`job_context_nudge.py` flags a named company that's at a gated stage with no
`human_path` yet, and separately reports how many `considering`/`outreach`
entries overall are still unchecked — `python3 scripts/human_path_report.py`
lists them and runs the graph query for each. It also flags a named company
with a found-but-`outreach`-pending lead ("reach out"), and one whose lead
was `"skipped"` (a different nudge — worth another pass for a stronger lead,
not a repeat push to contact someone already declined) — plus a matching
global count for pending outreach across every active-stage entry.

### Named contact and touch history

`human_path` can also carry `contact_name` (the primary/strongest contact for
this warm path) and `last_contacted` — `null` (never touched) or
`{"date": "YYYY-MM-DD", "type": "..."}` (`type` is free text: `email`,
`linkedin`, `call`, `interview`, `text`, `in-person`, whatever the actual
channel was). Both purely additive, sibling to `outreach` rather than
replacing it — `outreach` stays the coarse pending/contacted/skipped gate
`job_context_nudge.py`'s hook logic reads; `last_contacted` is the finer
"when, and how" detail a Slack digest needs to actually be actionable. Same
rules as everywhere else: get the date from `date`, never invent a name or a
date, update it as part of whatever turn actually made contact.

No backfill — an entry with no `contact_name`/`last_contacted` yet just shows
the rung category instead of a name in the digest, same soft-launch posture
as `last_touch` below. `scripts/job_digest.py`'s "Warm contacts to reach out
to" section reads these.

**This is a deliberate, scoped exception to "named contacts never leave this
machine."** `job_digest.py` posts to a Slack webhook/channel Anna created and
fully controls (no other installed app has access, confirmed 2026-09-15) —
the standing rule still holds for anything else: git, artifacts, any other
third-party service. Don't extend this exception to a different channel or
tool without asking first.

### Last-touch tracking

An entry can carry `last_touch` — a plain `"YYYY-MM-DD"` string, sibling to
`human_path`/`objection`. Same discipline as everything else here: get the
date from `date`, never invent one, and update it as part of whatever turn
actually touched the entry (a call, a note append, a stage change) — by hand
or by a session.

No entry starts with one, and there's no backfill — inventing 100 dates
nobody actually recorded would violate the same rule this field exists to
uphold. It fills in naturally as entries get touched going forward.
`scripts/job_digest.py` (see "Daily digest" below) uses it to flag an entry
that's gone quiet; an entry with no `last_touch` never gets flagged; that's
"never checked," not "confirmed fine."

### Posting link

An entry can carry `url` — the posting's live link, a plain string sibling to
`role`/`company`. Not previously tracked: JD files under `jd/` sometimes
capture a `source:` line, sometimes don't, and it's never been structured on
the entry itself. No backfill; `scripts/job_digest.py`'s "Worth applying to"
section links the entry's company/role text when `url` is present and falls
back to plain text when it isn't. A posting can go stale or the req can close
— that's still true of the link the way it was true of the saved JD text.

## Daily digest

`python3 scripts/job_digest.py` posts a once-a-day Slack summary: entries at
`considering` worth actually applying to, warm contacts found but not yet
reached out to — by name, with `human_path.contact_name`/`last_contacted` (see
"Named contact and touch history" above) — and entries with `last_touch` 7+
days old (`--threshold` to override). Company, role, stage, dates, and a
contact's name where one's on file — still never comp, never note text; the
contact-name exception is scoped specifically to this one webhook/channel
Anna controls, not a general loosening of "must never leave this machine"
(see the exception note above). `warm_path_sync.py`'s Supabase bridge is a
different destination with a different owner (JobWatch's Render deploy) and
stays count-only, no names — the exception here doesn't extend there.

Meant to run on a schedule, not interactively — `job/pipeline.json` can't
leave this machine, so unlike JobWatch this can't run on a cron host; it runs
locally via macOS `launchd`. Setup: copy
`scripts/launchd/com.annaknoll.job-digest.plist.example` to
`~/Library/LaunchAgents/`, fill in the machine-specific paths (comments in the
file walk through it), and `launchctl load` it. Needs its own Slack webhook —
a channel of its own, not JobWatch's — set as `JOB_DIGEST_SLACK_WEBHOOK_URL`
in `.env`. `--dry-run` prints the built message instead of posting it, for
checking the content (and that nothing sensitive snuck in) before it ever
reaches Slack.

## JobWatch integration

JobWatch (the nightly scraper, `../jobwatch/`) runs on Render with a
filesystem wiped between cron runs, so it can never reach this local,
`bolt://`-only Neo4j graph directly. Three one-way bridges instead, all
advisory except the sync — nothing here writes back into `pipeline.json` or
`jobwatch/config.py` on its own:

- **`python3 scripts/warm_path_sync.py`** — pushes a company name + contact/
  connection count (never a name) from the graph into a `warm_path` table in
  JobWatch's own Supabase project, the same local→cloud bridge
  `dedupe_store.py` already uses for dedupe. JobWatch's digest then flags a
  posting with `🤝 N contact(s)` and a small score bonus (`WARM_PATH_BONUS`
  in `jobwatch/config.py`), on every channel — console, email, and Slack.
  Run it after `graph_import.py` / `graph_import_linkedin.py`, same cadence.
  Stale between syncs; that's fine at a once-a-day digest cadence.
- **`python3 scripts/title_match_suggest.py`** — compares active-stage
  pipeline `role` titles against JobWatch's `ADZUNA_PHRASES` /
  `ATS_TITLE_KEYWORDS`, writes uncovered ones to
  `job/title_match_candidates.json` for review. Some `role` values are status
  notes ("WATCHING — no SE leadership role open"), not real titles — read the
  list, don't paste it wholesale into `jobwatch/config.py`.
- **`python3 scripts/ats_coverage_report.py`** — lists active-stage pipeline
  companies missing from JobWatch's `ATS_BOARDS`. No token lookup, no
  candidates file — just the gap, for a manual/WebSearch pass per company.

## Standing context

- **Comp floor and target role shape are stated in `job/Anna_Job_Search_Context.md`** under
  "What Anna is looking for". Read them there. State the floor matter-of-factly when it comes
  up; never negotiate it down in a draft, and never write the figure into a tracked file.
- The `resume/` files are the canonical career background. Pull from `resume/full.md` and
  `resume/stories.md` when drafting applications; where they disagree with the job context
  doc on a career fact, the resume wins.
