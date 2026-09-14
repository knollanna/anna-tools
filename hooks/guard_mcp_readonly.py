#!/usr/bin/env python3
"""PreToolUse hook — enforce read-only on specific MCP connectors.

"Read only" is doctrine everywhere else in this project (agent prompts, session
instructions); it is not a technical lock unless something outside the model's
own judgment enforces it. Confirmed against the real connectors in the MCP
registry: neither Gmail nor Google Drive offers a read-only variant to connect.
Each grants its full tool surface via one OAuth connect — Gmail includes
create_draft, forward, create_filter, delete_label, apply_sensitive_*_label;
Drive includes share_file (the classic poisoned-document -> reshare/exfiltrate
vector), update_file, create_file, copy_file, and trash_file (destructive, no
tool-level confirmation). This hook is the enforcement layer those connectors
don't provide.

Default-deny per connector, not a blocklist: each entry in MCP_ALLOWLISTS names
the tools believed safe to read with; everything else on that connector is
denied by default. A blocklist only stops the dangerous names already known
about; an allowlist fails safe against names not yet seen.

MCP_ALLOWLISTS below is the ONLY place the set of guarded connectors lives.
hooks/hooks.json's matcher is deliberately broad ("mcp__.*", every MCP tool
call on the machine) rather than carrying its own copy of these UUIDs — an
earlier version kept the UUID list in both files, which meant adding a
connector (or fixing a UUID) could update one file and silently forget the
other, and a tool call from the forgotten side would fall through to an
unlogged allow. Single-sourcing the list here removes that failure mode
structurally instead of just documenting the risk. The cost is that every MCP
tool call (not just Gmail/Drive) now spawns this process — accepted as cheap
enough given the alternative.

A connector not in MCP_ALLOWLISTS at all (Google Calendar, visualize,
scheduled-tasks, etc.) is correctly a no-op — this hook only guards the
connectors listed here, not every MCP connector on the machine. That's scope,
not a gap: broadening it to deny-by-default for every unknown connector would
also block benign, no-data-access tools like visualize's show_widget.

Gmail's allowlist is a best guess made before the account was ever connected —
the registry only showed 8 of its ~29 tools. Google Drive's allowlist is built
from its actual tool list (11 tools, all visible — Drive is already connected
in this session), so it should be accurate as of when this was written; recheck
if Drive's tool surface ever changes.

Uses hooks/_lib.py's payload() for stdin parsing (it already fails soft on
non-dict JSON, which a hand-rolled json.load(sys.stdin) here previously did
not — that gap let a valid-but-non-dict payload crash the hook with an
uncaught AttributeError instead of failing open like every other hook in this
repo). The whole entry point is wrapped the same way job_context_nudge.py and
session_init.py are: any unexpected exception fails open rather than crashing
mid-tool-call.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import _lib  # noqa: E402

import json

# uuid -> (label, allowlist). Label is only for the deny message.
MCP_ALLOWLISTS = {
    "2701e52f-b826-4aaf-8b25-11f2a97c98b0": (
        "Gmail",
        {
            "get_message",
            "get_thread",
            "list_messages",
            "list_threads",
            "search_messages",
            "search_threads",
            "list_labels",
            "get_attachment",
        },
    ),
    "27b5f497-98e1-4a23-bda1-e8dfcd61e80c": (
        "Google Drive",
        {
            "download_file_content",
            "get_file_metadata",
            "list_recent_files",
            "read_file_content",
            "search_files",
            "get_file_permissions",
        },
    ),
}


def deny(label: str, suffix: str) -> None:
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": (
                f'"{suffix}" is not on the {label} read-only allowlist '
                f"(hooks/guard_mcp_readonly.py) — denied by default. "
                f"If this is actually a safe read, add it to that connector's "
                f"allowlist there after confirming the real tool name, don't "
                f"just approve the prompt."
            ),
        }
    }))


def main() -> int:
    payload = _lib.payload()  # already fails soft to {} on any parse/shape error
    tool_name = str(payload.get("tool_name", ""))

    if not tool_name.startswith("mcp__"):
        return 0  # not an MCP call at all — not this hook's concern

    rest = tool_name[len("mcp__"):]
    for conn_uuid, (label, allowlist) in MCP_ALLOWLISTS.items():
        prefix = f"{conn_uuid}__"
        if not rest.startswith(prefix):
            continue
        suffix = rest[len(prefix):]
        if suffix in allowlist:
            return 0
        deny(label, suffix)
        return 0

    return 0  # an MCP call, but not from a connector this hook guards


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
