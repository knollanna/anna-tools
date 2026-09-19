#!/usr/bin/env python3
"""Daily Slack digest of job-search follow-ups: `considering`-stage entries
worth actually applying to, warm contacts found but not yet reached out to
(by name, with when/how they were last touched), and entries that have gone
quiet past a threshold.

`hooks/job_context_nudge.py` already computes most of this, but only
reactively - injected into a session when a prompt happens to look
job-search-related. This pushes the same category of nudge proactively, once
a day, to Slack.

job/pipeline.json is exactly the data rules/job-search.md says must never
leave this machine unnamed-contact-free, so this can't run on a cron host the
way JobWatch does - meant to run locally on a schedule (see
scripts/launchd/com.annaknoll.job-digest.plist.example).

Sends a contact's name (human_path.contact_name) and their last-touch date +
type (human_path.last_contacted) when those are on file - never comp, never
note prose. This is a DELIBERATE, SCOPED exception to "named contacts never
leave this machine": the destination is a Slack webhook/channel Anna created
and fully controls, confirmed no other app has access. See "Named contact and
touch history" in rules/job-search.md before reusing this pattern anywhere
else - it does not generalize to other channels, tools, or destinations
(warm_path_sync.py's Supabase bridge stays count-only, no names, on purpose).

Stage-set logic (outreach_state, the open-stage filter) is written fresh here
rather than imported from hooks/job_context_nudge.py: hooks/ and scripts/ are
a deliberate dependency boundary in this repo already (the hook stays
dependency-light and never imports from scripts/). OPEN_STAGES itself is
imported from _neo4j.py, a normal same-directory scripts/ import, same as
every other script here.

Failures here are loud, not soft: a missing webhook is a hard exit, since the
script's entire job is sending the Slack message - a silent skip just means
today's digest never happened, with nothing to notice.

    .venv/bin/python3 scripts/job_digest.py [--threshold 7] [--dry-run]
"""

import argparse
import json
import re
import sys
from datetime import date

import requests

from _neo4j import OPEN_STAGES, REPO, load_env

PIPELINE = REPO / "job" / "pipeline.json"
FOLLOWUP_THRESHOLD_DAYS = 7

OUTREACH_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _esc_slack(value):
    """Slack mrkdwn wants these three characters escaped, ampersand first."""
    return (str(value or "")
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;"))


def _esc_slack_url(url):
    """Same, plus a percent-encoded pipe: a literal '|' in the URL would end
    the <url|label> link target early and swallow the rest as label text."""
    return _esc_slack(url).replace("|", "%7C")


def load_entries() -> list[dict]:
    data = json.loads(PIPELINE.read_text(encoding="utf-8"))
    return data["entries"]


def outreach_state(hp: dict) -> str:
    """"contacted" | "skipped" | "pending". Mirrors job_context_nudge.py's
    function of the same name - see that file if this needs to change,
    they should stay in sync by hand since they're not shared code."""
    outreach = hp.get("outreach")
    if outreach == "skipped":
        return "skipped"
    if outreach and OUTREACH_DATE.match(outreach):
        return "contacted"
    return "pending"


def worth_applying(entries: list[dict]) -> list[dict]:
    """`considering` entries - not yet applied, an action Anna can actually
    take today. `applied` entries are the opposite: already submitted,
    waiting on the company - nothing for Anna to do but wait, so they don't
    belong in an actionable digest."""
    return [e for e in entries if e.get("stage") == "considering"]


def warm_contacts_pending(entries: list[dict], threshold_days: int) -> list[tuple[dict, int | None]]:
    """Warm-path entries that need outreach action right now: never yet
    contacted, contacted before but gone quiet for threshold_days+, or with
    a still-untouched secondary contact in the free-text `contacts` field
    (see "Warm-path check" in rules/job-search.md) even if the primary
    itself was touched recently - a company isn't done just because its
    first lead was used. Excludes a lead Anna deliberately decided to skip -
    that's a different nudge (see job_context_nudge.py), not a repeat push
    to use it.

    Returns (entry, days_since_last_contact) - days is None for "never
    contacted", so the caller can tell the two cases apart without
    re-deriving it."""
    out = []
    for e in entries:
        if e.get("stage") not in OPEN_STAGES:
            continue
        hp = e.get("human_path")
        if not hp or hp.get("best_rung") in (None, "none"):
            continue
        if hp.get("outreach") == "skipped":
            continue
        untouched = _untouched_count(e.get("contacts", ""))
        last_contacted = hp.get("last_contacted")
        if not last_contacted:
            out.append((e, None))
            continue
        lc_date = last_contacted.get("date") if isinstance(last_contacted, dict) else None
        if lc_date and OUTREACH_DATE.match(lc_date):
            days = (date.today() - date.fromisoformat(lc_date)).days
            if days >= threshold_days or untouched > 0:
                out.append((e, days))
    return out


def _apply_line(e: dict) -> str:
    label = f"{_esc_slack(e['company'])} — {_esc_slack(e.get('role') or '(role unclear)')}"
    url = e.get("url")
    return f"<{_esc_slack_url(url)}|{label}>" if url else label


def _contact_label(hp: dict) -> str:
    name = hp.get("contact_name")
    if name:
        return _esc_slack(name)
    return f"({_esc_slack(hp.get('best_rung') or 'unknown rung')})"


def _touch_status(days: int | None, last_contacted: dict | None) -> str:
    if days is None:
        return "not yet contacted"
    touch_type = _esc_slack(last_contacted.get("type") or "unknown")
    return f"last touched {last_contacted['date']} via {touch_type} ({days}d ago)"


def _untouched_count(contacts_text: str) -> int:
    """human_path tracks exactly one contact per entry, but the free-text
    `contacts` field often names several - every one of them still pending
    gets the literal phrase "not yet contacted" (see "Warm-path check" in
    rules/job-search.md), and the primary's own mention never carries it,
    since that status lives in human_path instead. Counting the phrase - not
    naming who - keeps this on the same "count only, no prose" privacy
    footing as everything else this digest sends."""
    return (contacts_text or "").lower().count("not yet contacted")


def _untouched_suffix(contacts_text: str) -> str:
    n = _untouched_count(contacts_text)
    if n == 0:
        return ""
    return f" (+{n} other{'s' if n != 1 else ''} untouched)"


def due_actions(entries: list[dict]) -> list[tuple[dict, date, int]]:
    """Open entries whose `next_action` is due today or overdue (see "Board
    ordering" in rules/job-search.md). Overdue ones stay listed until the date
    is moved forward, which doubles as a nudge to update it after an event.
    Returns (entry, action_date, days_overdue)."""
    today = date.today()
    out = []
    for e in entries:
        na = e.get("next_action")
        if e.get("stage") not in OPEN_STAGES or not isinstance(na, dict):
            continue
        try:
            d = date.fromisoformat(na["date"])
        except (KeyError, TypeError, ValueError):
            continue
        if d <= today:
            out.append((e, d, (today - d).days))
    return sorted(out, key=lambda t: (t[1], t[0]["next_action"].get("time", "")))


def _due_line(e: dict, days_overdue: int) -> str:
    na = e["next_action"]
    when = f" {na['time']}" if na.get("time") else ""
    what = f" — {_esc_slack(na['what'])}" if na.get("what") else ""
    late = f" (overdue {days_overdue}d)" if days_overdue else ""
    return f"• {_esc_slack(e['company'])}{when}{what}{late}"


def stale_followups(entries: list[dict], threshold_days: int) -> list[tuple[dict, int]]:
    today = date.today()
    out = []
    for e in entries:
        if e.get("stage") not in OPEN_STAGES:
            continue
        last_touch = e.get("last_touch")
        if not last_touch or not OUTREACH_DATE.match(last_touch):
            continue
        days = (today - date.fromisoformat(last_touch)).days
        if days >= threshold_days:
            out.append((e, days))
    return out


def build_blocks(entries: list[dict], threshold_days: int) -> list[dict]:
    to_apply = sorted(worth_applying(entries), key=lambda e: e["company"])
    warm_pending = sorted(warm_contacts_pending(entries, threshold_days),
                           key=lambda t: t[0]["company"])
    stale = sorted(stale_followups(entries, threshold_days), key=lambda t: -t[1])
    due = due_actions(entries)

    header = (
        f"🗂️ *Job search digest* — {len(to_apply)} worth applying to, "
        f"{len(warm_pending)} warm contact(s) to reach out to, "
        f"{len(stale)} stale follow-up(s)"
        + (f", {len(due)} due today" if due else "")
    )
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": header}}]

    if due:
        lines = "\n".join(_due_line(e, late) for e, _, late in due)
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"*📅 Due today*\n{lines}"}})

    if to_apply:
        lines = "\n".join(f"• {_apply_line(e)}" for e in to_apply)
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"*📋 Worth applying to*\n{lines}"}})

    if warm_pending:
        lines = "\n".join(
            f"• {_esc_slack(e['company'])} — {_contact_label(e['human_path'])} — "
            f"{_touch_status(days, e['human_path'].get('last_contacted'))}"
            f"{_untouched_suffix(e.get('contacts', ''))}"
            for e, days in warm_pending
        )
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"*🤝 Warm contacts to reach out to*\n{lines}"}})

    if stale:
        lines = "\n".join(
            f"• {_esc_slack(e['company'])} — last touched {e['last_touch']} ({days}d ago)"
            for e, days in stale
        )
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"*⏰ Follow-up needed ({threshold_days}+ days quiet)*\n{lines}"}})

    if not (to_apply or warm_pending or stale or due):
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": "Nothing pending today."}})

    return blocks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--threshold", type=int, default=FOLLOWUP_THRESHOLD_DAYS,
                         help="days of silence before flagging an entry or a contact "
                              f"(default {FOLLOWUP_THRESHOLD_DAYS})")
    parser.add_argument("--dry-run", action="store_true",
                         help="print the Slack blocks instead of posting them")
    args = parser.parse_args()

    webhook = None
    if not args.dry_run:
        env = load_env()
        webhook = env.get("JOB_DIGEST_SLACK_WEBHOOK_URL")
        if not webhook:
            sys.exit("JOB_DIGEST_SLACK_WEBHOOK_URL not set in .env")

    entries = load_entries()
    blocks = build_blocks(entries, args.threshold)

    if args.dry_run:
        print(json.dumps(blocks, indent=2))
        return 0

    r = requests.post(webhook, json={"blocks": blocks}, timeout=10)
    if r.status_code != 200:
        sys.exit(f"Slack post failed: {r.status_code} {r.text[:200]}")
    print(f"Posted digest: {len(worth_applying(entries))} worth applying to, "
          f"{len(warm_contacts_pending(entries, args.threshold))} warm contact(s), "
          f"{len(stale_followups(entries, args.threshold))} stale follow-up(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
