#!/usr/bin/env python3
"""PreToolUse hook — enforce read-only on the Gmail MCP connector.

"Read only" is doctrine everywhere else in this project (agent prompts, session
instructions); it is not a technical lock unless something outside the model's
own judgment enforces it. Confirmed against the actual Gmail connector in the
MCP registry: there is no read-only variant to connect. Its tool surface
includes create_draft, forward, create_filter, create_label, delete_label,
apply_sensitive_message_label, apply_sensitive_thread_label, and more — all
granted by the same single OAuth connect. This hook is the enforcement layer
that connector doesn't provide.

Default-deny, not a blocklist: anything not explicitly named as a safe read is
denied. A blocklist only stops the dangerous names already known about; an
allowlist fails safe against tool names not yet seen. READ_ONLY_ALLOWLIST below
is a best guess made before ever connecting the account — Gmail's registry
listing showed only 8 of its ~29 tools before connecting. Refine this list once
the real tool names are visible (see hooks/hooks.json's PreToolUse entry for how
this is wired, and rules/job-search.md or the plan history for the verification
steps run before trusting this).

Silent (exit 0, no output) for any non-Gmail tool, and for anything on the
allowlist. Denies everything else with a reason naming the tool.

Wired on PreToolUse, matcher scoped to the Gmail connector's directory UUID only
— this hook must never fire for, or restrict, any other connector (Google
Drive, etc.). Reads the hook payload as JSON on stdin.
"""

import json
import re
import sys

GMAIL_UUID = "2701e52f-b826-4aaf-8b25-11f2a97c98b0"

# Suffix after "mcp__<uuid>__" — matched case-sensitively against the exact tool
# name. Extend this list once Gmail's real tool names are visible post-connect;
# do not extend it with a guess "to be safe" — an unverified name defeats the
# fail-safe design just as much as skipping the hook entirely.
READ_ONLY_ALLOWLIST = {
    "get_message",
    "get_thread",
    "list_messages",
    "list_threads",
    "search_messages",
    "search_threads",
    "list_labels",
    "get_attachment",
}

TOOL_NAME_RE = re.compile(rf"^mcp__{re.escape(GMAIL_UUID)}__(.+)$")


def deny(tool_name: str, suffix: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f'"{suffix}" is not on the Gmail read-only allowlist '
                f"(hooks/guard_mcp_readonly.py) — denied by default. "
                f"If this is actually a safe read, add it to READ_ONLY_ALLOWLIST "
                f"there after confirming the real tool name, don't just approve "
                f"the prompt."
            ),
        }
    }))


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        return 0  # never block on a hook-parsing failure — fail open on OUR bug,
                  # fail closed only on an actual unrecognized tool call, below.

    tool_name = str(payload.get("tool_name", ""))
    m = TOOL_NAME_RE.match(tool_name)
    if not m:
        return 0  # not a Gmail call — not this hook's concern

    suffix = m.group(1)
    if suffix in READ_ONLY_ALLOWLIST:
        return 0

    deny(tool_name, suffix)
    return 0


if __name__ == "__main__":
    sys.exit(main())
