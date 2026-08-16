# anna-tools

Anna Knoll's personal AI tooling. Standing conventions for her own projects, kept in one
place so every session starts knowing them instead of being told again.

This is Phase 1: four rule files and a project catalog. No agents, no hooks, no skills, no
plugin manifest. Those get added when something annoys her twice, not before.

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
├── CLAUDE.md          this file
├── projects.json      the catalog: what exists, where, what state it's in
├── rules/
│   ├── design-system.md   the quality bar for anything with a UI
│   ├── writing.md         voice, and the LLM tells to cut
│   └── github.md          branches, commits, what gets reviewed
└── resume/
    ├── summary.md         short, always loaded
    ├── full.md            every role and date, on demand
    └── stories.md         STAR anecdotes, on demand
```

## Rules (read on demand)

| File | When to read |
| --- | --- |
| `rules/writing.md` | Before writing anything Anna will publish, commit, or read. Effectively always. |
| `rules/design-system.md` | Before touching CSS, color, type, or markup in any project with a UI |
| `rules/github.md` | Before branching, committing, opening a PR, or pushing |

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

## What is not here yet, and why

| Piece | Add it when |
| --- | --- |
| Skills (`/tailor-resume`, `/new-post`) | You have explained the same process twice |
| Hooks | Prose stopped being enough and you need a guarantee |
| Agents | A task reliably burns your context reading files |
| Scripts | You catch yourself asking a model to check 50 things |
| A plugin manifest / installer | More than one machine or more than one person needs this |
