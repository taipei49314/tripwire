#!/usr/bin/env python3
"""tripwire PreToolUse gate (M1-C).

Before Bash runs `git commit` / `git push`, scan the range that would
enter history. Worktree for commit (the wash is still on disk). Unpushed
commits for push (the wash may already be in HEAD).

Speaks the PreToolUse protocol: hookSpecificOutput.permissionDecision,
exit 0 either way.
"""

from __future__ import annotations

import json
import os
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if HOOKS_DIR not in sys.path:
    sys.path.insert(0, HOOKS_DIR)

import gate  # noqa: E402


def _allow() -> int:
    sys.stdout.write("{}\n")
    return 0


def _deny(reason: str) -> int:
    sys.stdout.write(
        json.dumps(
            {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": reason,
                }
            }
        )
        + "\n"
    )
    return 0


def _command(payload: dict) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    for key in ("command", "cmd"):
        val = tool_input.get(key)
        if isinstance(val, str):
            return val
    return ""


def main() -> int:
    payload = gate.read_payload()
    if payload is None:
        return _deny(
            "tripwire: malformed hook payload (stdin was not JSON). "
            "Failing closed: the submit gate cannot certify this action."
        )

    cwd = payload.get("cwd") or os.getcwd()
    if not gate.is_git_repo(cwd):
        return _allow()

    command = _command(payload)
    verbs = gate.git_commit_push_verbs(command)
    if not verbs:
        return _allow()

    if "commit" in verbs:
        status, reason = gate.run_greenwash(cwd)
        if status != "allow":
            return _deny(reason)

    if "push" in verbs:
        rev_range = gate.unpushed_range(cwd)
        if rev_range:
            status, reason = gate.run_greenwash(cwd, rev_range)
            if status != "allow":
                return _deny(reason)

    return _allow()


if __name__ == "__main__":
    raise SystemExit(main())
