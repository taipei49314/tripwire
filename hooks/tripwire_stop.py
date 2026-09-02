#!/usr/bin/env python3
"""tripwire stop gate (M0 + M1-R).

Claude Code Stop hook: before the agent finishes a turn,
  1. run greenwash on HEAD..worktree (M0)
  2. require a walkaround ADMITTED receipt (M1-R)

Speaks the Stop-hook JSON protocol: a decision object on stdout,
exit 0 either way.

Judge boundary (SPEC section 2): judges are vendored at pinned tags and
invoked as-is; verdict text passes through unmodified. Fail-closed: a
crashed or hung judge blocks with an engine-error reason.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

HOOKS_DIR = os.path.dirname(os.path.abspath(__file__))
if HOOKS_DIR not in sys.path:
    sys.path.insert(0, HOOKS_DIR)

import gate  # noqa: E402


def _allow() -> int:
    sys.stdout.write("{}\n")
    return 0


def _block(reason: str) -> int:
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}) + "\n")
    return 0


def main() -> int:
    payload = gate.read_payload()
    if payload is None:
        return _block(
            "tripwire: malformed hook payload (stdin was not JSON). "
            "Failing closed: the stop gate cannot certify this turn."
        )

    # Loop protection: we already blocked this stop once; let it through.
    if payload.get("stop_hook_active"):
        return _allow()

    cwd = payload.get("cwd") or os.getcwd()
    if not gate.is_git_repo(cwd):
        return _allow()

    status, reason = gate.run_greenwash(cwd)
    if status != "allow":
        return _block(reason)
    return _walkaround_gate(cwd)


def _walkaround_gate(cwd: str) -> int:
    """M1-R: Stop is a done-claim. No ADMITTED receipt → not in the lab."""
    root = gate.walkaround_root()
    pkg = os.path.join(root, "walkaround")
    if not os.path.isdir(pkg):
        return _block(
            "tripwire: vendored walkaround not found (run scripts/install.ps1). "
            "Failing closed: the stop gate cannot certify this turn."
        )
    env = dict(os.environ)
    env["PYTHONPATH"] = root + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "walkaround", "--root", cwd, "hook"],
            capture_output=True,
            text=True,
            timeout=gate.TIMEOUT_SECONDS,
            env=env,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return _block(
            f"tripwire: walkaround timed out after {gate.TIMEOUT_SECONDS}s. "
            "Failing closed: the stop gate cannot certify this turn."
        )
    except Exception as err:
        return _block(f"tripwire: walkaround could not run ({err!r}). Failing closed.")

    text = ((result.stdout or "") + "\n" + (result.stderr or "")).strip()
    if result.returncode == 0:
        return _allow()
    reason = text[-1500:] if text else f"walkaround hook exit {result.returncode}"
    if result.returncode == 2:
        return _block(
            "tripwire: walkaround engine error (exit 2). Failing closed.\n" + reason
        )
    return _block(reason + "\ntripwire: enter the lab; a done-claim needs an ADMITTED receipt.")


if __name__ == "__main__":
    raise SystemExit(main())
