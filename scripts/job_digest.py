#!/usr/bin/env python3
"""Daily Slack digest of job-search follow-ups: warm contacts found but not
yet reached out to, applications sitting at `applied` awaiting a response,
and entries that have gone quiet past a threshold.

`hooks/job_context_nudge.py` already computes most of this, but only
reactively - injected into a session when a prompt happens to look
job-search-related. This pushes the same category of nudge proactively, once
a day, to Slack.

job/pipeline.json is exactly the data rules/job-search.md says must never
leave this machine unnamed-contact-free, so this can't run on a cron host the
way JobWatch does - meant to run locally on a schedule (see
scripts/launchd/com.annaknoll.job-digest.plist.example). Sends company, role,
stage, and dates only - never a contact's name, a comp figure, or note prose.
Warm-contact entries use human_path.best_rung (a category: "linkedin",
"pipeline", etc.), never human_path.summary, which routinely contains a
contact's actual name and title.

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


def applications_pending(entries: list[dict]) -> list[dict]:
    return [e for e in entries if e.get("stage") == "applied"]


def warm_contacts_pending(entries: list[dict]) -> list[dict]:
    out = []
    for e in entries:
        if e.get("stage") not in OPEN_STAGES:
            continue
        hp = e.get("human_path")
        if not hp or hp.get("best_rung") in (None, "none"):
            continue
        if outreach_state(hp) != "pending":
            continue
        out.append(e)
    return out


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
    pending_apps = sorted(applications_pending(entries), key=lambda e: e["company"])
    warm_pending = sorted(warm_contacts_pending(entries), key=lambda e: e["company"])
    stale = sorted(stale_followups(entries, threshold_days), key=lambda t: -t[1])

    header = (
        f"🗂️ *Job search digest* — {len(pending_apps)} application(s) pending, "
        f"{len(warm_pending)} warm contact(s) to reach out to, "
        f"{len(stale)} stale follow-up(s)"
    )
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": header}}]

    if pending_apps:
        lines = "\n".join(
            f"• {_esc_slack(e['company'])} — {_esc_slack(e.get('role') or '(role unclear)')}"
            for e in pending_apps
        )
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": f"*📋 Applications pending*\n{lines}"}})

    if warm_pending:
        lines = "\n".join(
            f"• {_esc_slack(e['company'])} — warm path found "
            f"({_esc_slack(e['human_path'].get('best_rung') or 'unknown rung')}), not yet contacted"
            for e in warm_pending
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

    if not (pending_apps or warm_pending or stale):
        blocks.append({"type": "section", "text": {"type": "mrkdwn",
                       "text": "Nothing pending today."}})

    return blocks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--threshold", type=int, default=FOLLOWUP_THRESHOLD_DAYS,
                         help=f"days since last_touch before flagging (default {FOLLOWUP_THRESHOLD_DAYS})")
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
    print(f"Posted digest: {len(applications_pending(entries))} pending application(s), "
          f"{len(warm_contacts_pending(entries))} warm contact(s), "
          f"{len(stale_followups(entries, args.threshold))} stale follow-up(s).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
