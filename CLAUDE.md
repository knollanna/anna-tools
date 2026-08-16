# anna-tools

Anna Knoll's personal AI tooling. Standing conventions for her own projects, kept in one
place so every session starts knowing them instead of being told again.

Ships as a Claude Code plugin, so the rules and hooks travel to every repo instead of only
working inside this directory. No agents and no skills yet — those get added when something
annoys her twice, not before.

## Non-negotiables

- **No employer or customer working material lives here.** No internal architecture, no
  engagement notes, no deal detail, no credentials, nothing covered by an NDA. This repo is
  personal work only. The boundary is the point: a toolkit that has never held someone else's
  material can be shown to anyone without a review.
  **Her own career history is hers**, so `resume/` carries employers, titles, dates, and the
  account names that appear on her own resume. That is the line: a fact she publishes about
  herself is in scope; anything she learned by working somewhere is not.
- **No secrets, no `.env` contents, no API keys** — not in rules, not in examples, not in a
  comment "just for now". FareWatch and JobWatch both keep live `.env` files; never copy a
  value out of one into this repo.
- **A new primitive needs a second occurrence.** Don't add a skill, hook, agent, or script
  because it might be useful. Add it when the same friction has happened twice and you can
  name both times. One annoyance gets fixed in place and forgotten.
- **American English.**
- **The rules in `rules/` are not auto-loaded.** They are plain files, pointed at from here
  and from individual projects. Adding a rule means adding it to the table below, or nothing
  will ever read it.

## Layout

```
anna-tools/
├── .claude-plugin/
│   ├── plugin.json        the packaging contract
│   └── marketplace.json   local marketplace so it installs at user scope
├── CLAUDE.md          this file
├── projects.json      the catalog: what exists, where, what state it's in
├── rules/
│   ├── design-system.md   the quality bar for anything with a UI
│   ├── writing.md         voice, and the LLM tells to cut
│   ├── github.md          branches, commits, what gets reviewed
│   └── job-search.md      how to maintain the pipeline files
├── resume/
│   ├── summary.md         short, always loaded
│   ├── full.md            every role and date, on demand
│   └── stories.md         STAR anecdotes, on demand
├── hooks/
│   ├── hooks.json             event wiring
│   ├── _lib.py                payload parsing + root resolution
│   ├── session_init.py        SessionStart: where am I, which rules apply
│   └── job_context_nudge.py   UserPromptSubmit: surfaces the job rule on a match
├── scripts/
│   └── tracker_to_md.py       tracker HTML -> greppable markdown
└── job/               🔒 GITIGNORED. Never commit, publish, or put in an artifact.
```

## How it loads

Registered at user scope in `~/.claude/settings.json` as `anna-tools@anna-local`, sourced
from this directory. Every session on this machine gets it, in any repo.

`session_init.py` is what makes that worth anything. A session opened in `farewatch/` never
reads this file, so on `SessionStart` the hook names the project from `projects.json` and
lists the rules that apply. It emits **pointers, not content** — loading four rule files into
every session would tax every conversation that doesn't need them.

## How rules get selected

Rules are chosen two ways, and each rule declares its own applicability in its frontmatter.
Adding a rule needs no change to any hook.

```yaml
---
description: ...          # shown in the session index
profiles: [static-site]   # declared: project archetypes this serves. "*" means everywhere.
detect: ["*.css", ".git"] # observed: pull it in if these exist in the working tree
---
```

- **By profile.** Each project in `projects.json` claims one, and the valid names live in
  `profiles.json`. Declared, stable, and the thing you'd reason about when adding a project.
- **By detection.** A bounded walk of the working tree, depth 3, skipping `node_modules` and
  friends. This catches what a profile misses: FareWatch is a `python-service`, but it has
  `templates/` and a stylesheet, so the design bar applies there and the hook works that out
  on its own.

The index says **why** each rule was selected (`profile: static-site`, `found .git`, `always`)
and names the ones it deliberately skipped. A wrong selection should be debuggable in one
glance rather than mysterious.

`profiles.json` exists to catch drift. A profile no rule claims is fine — it means the
universal and detected rules already cover it. A profile name that isn't in the registry is a
typo, and a typo means a rule silently never loads, which is the failure mode worth spending a
file to prevent.

Current selection:

| Project | Profile | Rules |
| --- | --- | --- |
| annaknoll-site | `static-site` | design-system (profile), github (found `.git`), writing (always) |
| farewatch | `python-service` | design-system (found `*.html`), github, writing |
| jobwatch | `python-service` | github, writing |
| anna-tools | `tooling` | job-search (profile), design-system, github, writing |

To work on the plugin itself without the installed copy interfering:

```bash
claude --plugin-dir /Users/anna/Documents/Claude/Projects/anna-tools
```

**Two roots, and they are not the same thing.** `CLAUDE_PLUGIN_ROOT` is where `rules/` live
and may be a marketplace cache copy. `ANNA_TOOLS_HOME` is where Anna's own content lives
(`projects.json`, `resume/`, `job/`) and never moves. `hooks/_lib.py` resolves both. Collapsing
them means a cached plugin silently stops finding the job pipeline, and the failure is
invisible because the hook just goes quiet.

## Rules (read on demand)

| File | When to read |
| --- | --- |
| `rules/writing.md` | Before writing anything Anna will publish, commit, or read. Effectively always. |
| `rules/design-system.md` | Before touching CSS, color, type, or markup in any project with a UI |
| `rules/github.md` | Before branching, committing, opening a PR, or pushing |
| `rules/job-search.md` | Any interview, transcript, recruiter call, application, or pipeline change. The `job_context_nudge` hook points here automatically. |

## Resume (read on demand)

| File | When to read |
| --- | --- |
| `resume/summary.md` | Any time Anna's background is relevant. Short enough to always load. |
| `resume/full.md` | Writing a resume, a bio, a profile, or anything needing dates and specifics |
| `resume/stories.md` | Cover letters, interview prep, anything needing a concrete anecdote |

**Never invent a role, date, employer, metric, or credential.** If `full.md` doesn't have it,
say so and ask. A plausible-sounding fabrication in a job application is the worst possible
failure mode for this repo.

## Projects

`projects.json` is the catalog — name, repo, path, stack, deploy target, current state. It
says what exists and where to look. It does not duplicate the details.

Architecture lives in each project's own repo, not here. Read the project's `README.md` for
how it works before changing anything in it; FareWatch and annaknoll.com both have thorough
ones and neither is decorative.

## Job search

`job/` holds the pipeline context and tracker. **It is gitignored and stays that way** — it
carries sensitive employment and compensation detail, named contacts at companies Anna is
interviewing with, and candid assessments. `rules/job-search.md`
is the procedure. `hooks/job_context_nudge.py` fires on `UserPromptSubmit` and surfaces that
rule whenever a prompt carries a job-search signal, so the update doesn't depend on anyone
remembering. Wired in `~/.claude/settings.json`.

## The seam: what would and wouldn't ship to someone else

This plugin is Anna's. If a second person installed it today they would get her resume, her
project catalog, and her job pipeline, which is useless to them and private to her.

The line runs through the middle of this repo, and naming it is more useful than pretending
it isn't there:

| Layer | Contents | Portable? |
| --- | --- | --- |
| **Structure** | `.claude-plugin/`, `hooks/hooks.json`, `_lib.py`, `session_init.py`, the rules-as-plain-files pattern, the two-roots split | Yes. This is the transferable part. |
| **Standards** | `rules/github.md`, the accessibility contract and deterministic-first parts of `rules/design-system.md` | Mostly. A team would seed its own equivalents. |
| **Personal** | `resume/`, `projects.json`, `job/`, `rules/writing.md`, the annaknoll palette | No. Never. |

A shared version would ship the first row, seed the second, and leave the third to each
person. That is the two-layer model in `mg-tools-reference/docs/architecture.md`: a standards
layer plus a per-consumer layer. **Do not build the shared version until someone other than
Anna actually needs it.**

## What is here, and what earned it

| Piece | Status |
| --- | --- |
| Hook (`job_context_nudge.py`) | **Built.** Anna asked for a guarantee, not a habit — a prose rule that only works when someone remembers to read it is the case a hook exists for. |
| Script (`tracker_to_md.py`) | **Built.** Converting 60 JS objects to markdown by hand is the definition of work a model should not be doing. |
| Skills (`/tailor-resume`, `/new-post`) | Not yet. Write one the second time you explain the same process. `/tailor-resume` is the obvious first candidate. |
| Agents | Not yet. Add when a task reliably burns your context reading files. |
| A plugin manifest / installer | Not yet. Add when more than one machine or more than one person needs this. |
