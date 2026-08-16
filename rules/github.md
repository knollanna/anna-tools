---
description: Branch naming, commit format, and what gets reviewed before it lands. Modeled on FareWatch.
---

# GitHub

All repos are under `github.com/knollanna`. Default branch is `main` everywhere.

FareWatch already works this way. annaknoll-site and JobWatch mostly commit straight to
`main`; they move to this model from now on. Don't rewrite their history.

## Branches

Never commit directly to `main`. Branch, then merge.

```
<type>/<short-kebab-description>
```

`feat/` · `fix/` · `docs/` · `refactor/` · `chore/`

Real examples from FareWatch: `feat/hotels-phase2-alerts`, `docs/edit-405-cache-gotcha`,
`feat/graceful-405-redirect`.

Keep the description specific enough to recognize in `git branch` three weeks later.
`review-fixes` and `farewatch-built-section` are both too vague to have been useful.

## Commits

**Subject line: lowercase `type:` prefix, then sentence case, imperative, no trailing period.**

```
feat: scope watch history and alerts to a trip epoch
fix: key cross-run dedupe on company+title+location-type, not raw listing id
docs: note 405-on-edit is a stale browser cache, not a server bug
```

The prefix is what a hook or a script can parse later. The sentence case is what makes the log
readable. Both matter.

Say what changed and why it changed. `docs: note 405-on-edit is a stale browser cache, not a
server bug` is a good commit message because six months later it answers a question. `fix
committed files` answers nothing.

Body only when the subject can't carry it. Wrap it in prose, not bullets, unless there are
genuinely several independent changes — and if there are, that's usually two commits.

`rules/writing.md` applies to commit messages.

## Merging

Merge commits, not squash and not rebase. The branch name survives in the merge commit, which
is how `Merge feat/hotels-phase2-alerts: hotel alerts (swallow-safe)` still reads usefully.

Delete the branch after merging.

## Before pushing

- **Read the diff.** Every hunk. Not `git add -A` on faith.
- **Check for secrets.** FareWatch and JobWatch both keep live `.env` files next to committed
  code. Confirm `.gitignore` covers them before every push, not once.
- **Confirm nothing crossed a publish boundary.** On annaknoll-site, anything added under
  `public/` becomes a world-readable URL at `annaknoll.com/<path>` on the next deploy. Adding
  files outside `public/` is always safe. Adding files inside it is a publishing decision.
- **Know what the push deploys.** A push to `main` is a deploy on all three:

| Repo | Push to `main` triggers |
| --- | --- |
| annaknoll-site | Netlify deploy, publish dir `public/`, no build command |
| FareWatch | Render redeploy — web app and the 2-hourly cron |
| JobWatch | Render redeploy — nightly cron |

There is no staging environment on any of them. `main` is production.

## Reviews

Solo repos, so review means: open a PR, read your own diff as a diff rather than as the code
you just wrote, then merge. Both jobwatch's "Fix four correctness bugs found in code review"
and annaknoll-site's "Code-review fixes: spacing, a11y, headings, OG images, dead CSS" came
out of doing exactly that.

Ask for a review pass on anything that touches money, credentials, a cron schedule, or a
publish boundary.

## Never

- Force-push `main`.
- Commit a `.env`, an API key, a webhook URL, or a Supabase key.
- Commit generated artifacts without the source that generates them.
- Push a copy change to annaknoll-site without regenerating the social cards. See
  `rules/design-system.md`.
