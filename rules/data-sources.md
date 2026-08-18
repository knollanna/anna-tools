---
description: Before adding or changing a third-party data source — check the terms, respect the barriers, and prefer the documented API.
profiles: [python-service]
detect: ["*_source.py", "*_sources.py"]
---

# Third-party data sources

Applies to FareWatch (Duffel, LiteAPI, SendGrid, Slack) and JobWatch (Adzuna, Greenhouse, Ashby,
Getro), and to any new source added to either.

## Check the terms before you write the fetch

**Read the provider's Terms of Service before building against them, not after.** Not after the
prototype works, not after the spec is written. Before.

This exists because of a specific failure on **2026-08-18**: a Consider.co endpoint powering the
a16z and Battery Ventures job boards was reverse-engineered, swept for results, and written up as
a JobWatch integration — and *then* the terms were read. They prohibited all of it. The work was
thrown away and `jobwatch/docs/consider-source-spec.md` now carries a do-not-build note.

Search the terms for: `robot`, `spider`, `scraper`, `automated`, `crawl`, `bot`, `API`,
`bypass`, `extract`. Two clauses matter most, and providers usually have both:

- **"automated means… for any purpose"** — there is no research-only or one-off carve-out. A
  single manual sweep counts.
- **"bypass any measures we may use to prevent or restrict access"** — this is the more serious
  one, and the easier one to violate without noticing.

## An access barrier is an answer, not an obstacle

**If you have to defeat something to get the data, that is the provider telling you no.**

CSRF tokens, undocumented private endpoints, signed requests, session cookies, rate limiters,
bot detection, and paywalls are all *measures to restrict access*. Extracting a CSRF token out
of page HTML so a POST will succeed is bypassing a measure, whatever the intent.

The 2026-08-18 failure was exactly this: the CSRF protection was read as an engineering puzzle
rather than as the answer it was. **When a barrier appears, stop and check the terms — do not
route around it and check later.**

## The preference order

1. **A documented public API**, used within its stated limits. Adzuna is the model — a real API,
   a real key, published terms.
2. **A documented feed or export** the provider offers on purpose.
3. **Server-rendered public HTML** that requires no authentication, no token, and no bypass —
   what the Getro source does. Still check the terms.
4. **Written permission**, if the source is worth asking for. This is the legitimate path when a
   provider prohibits automation but the data genuinely matters.
5. **Nothing.** A human opening a bookmark is not automated access and never needs a source.

**A script whose only function is to print or open a URL is not a source and does not belong in
this repo.** It adds nothing over a browser bookmark.

## When a source is rejected

Do not leave the working contract in the repo. A spec for a prohibited integration is how it
gets built a year later by someone who does not know the history. **Replace it with a note
saying what was rejected and why**, and leave the terms quote in place so nobody re-litigates it
from memory.

## Standing constraints

- **Never LinkedIn or Indeed.** Both prohibit it and both are the most likely to block or ban.
  This predates the rule and still holds.
- **Identify honestly.** Do not forge a User-Agent to look like a browser when the point is to
  avoid being recognized as a script.
- **Be gentle.** Timeouts, retries with backoff, and a real delay between requests. The existing
  sources already do this — match their shape rather than inventing a new one.
- **Cache and dedupe** so a rerun does not re-fetch what is already known.
