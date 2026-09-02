#!/usr/bin/env python3
"""tripwire PreToolUse (M1-C + M1-C2 + M1-W + H1-2).

Bash git commit/push: greenwash worktree or unpushed ranges (incl. --all / refspec).
Write/Edit: plan must be ADVANCED unless the path is a gate directory.
git commit --no-verify still runs this harness gate (H1).
"""

from __future__ import annotations

import json
import os
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if HOOKS_DIR not in sys.path:
    sys.path.insert(0, HOOKS_DIR)

import gate  # noqa: E402

WRITE_TOOLS = {"Write", "Edit", "MultiEdit"}


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


def _write_path(payload: dict) -> str:
    tool_input = payload.get("tool_input")
    if not isinstance(tool_input, dict):
        return ""
    for key in ("file_path", "path"):
        val = tool_input.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    edits = tool_input.get("edits")
    if isinstance(edits, list) and edits and isinstance(edits[0], dict):
        p = edits[0].get("file_path") or edits[0].get("path")
        if isinstance(p, str):
            return p.strip()
    return ""


def _write_gate(cwd: str, path: str) -> int:
    if gate.path_is_meta(path):
        return _allow()
    state = gate.plan_advanced(cwd)
    if state == "missing":
        return _deny(
            "tripwire: NO_LEDGER — Write/Edit before a measured plan is not an exam. "
            "Advance phaseledger plan first."
        )
    if state == "pending":
        return _deny(
            "tripwire: PLAN_NOT_ADVANCED — production writes wait for plan: ADVANCED. "
            "claim → measure → advance."
        )
    return _allow()


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

    tool = str(payload.get("tool_name") or "")
    if tool in WRITE_TOOLS:
        return _write_gate(cwd, _write_path(payload))

    command = _command(payload)
    verbs = gate.git_commit_push_verbs(command)
    if not verbs:
        return _allow()

    if "commit" in verbs:
        status, reason = gate.run_greenwash(cwd)
        if status != "allow":
            return _deny(reason)

    if "push" in verbs:
        ranges = gate.push_ranges(cwd, command)
        for rng in ranges:
            status, reason = gate.run_greenwash(cwd, rng)
            if status != "allow":
                return _deny(reason)

    return _allow()


if __name__ == "__main__":
    raise SystemExit(main())
