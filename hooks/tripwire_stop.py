#!/usr/bin/env python3
"""tripwire stop gate (M0).

Claude Code Stop hook: before the agent finishes a turn, run greenwash on
HEAD..worktree and block the stop when the verification layer was tampered
with. Speaks the Stop-hook JSON protocol: a decision object on stdout,
exit 0 either way.

Judge boundary (SPEC section 2): greenwash is vendored at a pinned tag and
invoked as-is; its verdict text passes through unmodified. Fail-closed: a
crashed or hung judge blocks with an engine-error reason.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys

TIMEOUT_SECONDS = 30


def _tripwire_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _greenwash_src() -> str:
    override = os.environ.get("TRIPWIRE_GREENWASH_SRC")
    if override:
        return override
    return os.path.join(_tripwire_root(), "vendor", "greenwash", "src")


def _allow() -> int:
    sys.stdout.write("{}\n")
    return 0


def _block(reason: str) -> int:
    sys.stdout.write(json.dumps({"decision": "block", "reason": reason}) + "\n")
    return 0


def _is_git_repo(cwd: str) -> bool:
    try:
        probe = subprocess.run(
            ["git", "rev-parse", "--is-inside-work-tree"],
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception:
        return False
    return probe.returncode == 0 and probe.stdout.strip() == "true"


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except Exception:
        payload = {}

    # Loop protection: we already blocked this stop once; let it through.
    if payload.get("stop_hook_active"):
        return _allow()

    cwd = payload.get("cwd") or os.getcwd()
    if not _is_git_repo(cwd):
        return _allow()

    src = _greenwash_src()
    if not os.path.isdir(src):
        return _block(
            "tripwire: vendored greenwash not found (run scripts/install.ps1). "
            "Failing closed: the stop gate cannot certify this turn."
        )

    env = dict(os.environ)
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "greenwash", "check", "--format", "hook-json", "--repo", cwd],
            capture_output=True,
            text=True,
            timeout=TIMEOUT_SECONDS,
            env=env,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return _block(
            f"tripwire: greenwash timed out after {TIMEOUT_SECONDS}s. "
            "Failing closed: the stop gate cannot certify this turn."
        )
    except Exception as err:  # spawn failure and friends
        return _block(f"tripwire: greenwash could not run ({err!r}). Failing closed.")

    out = result.stdout.strip()
    # hook-json contract: decision JSON on stdout, exit 0 either way. Anything
    # else is an engine failure -> fail closed, judge stderr attached.
    if result.returncode != 0 or not out:
        tail = (result.stderr or result.stdout or "").strip()[-1500:]
        return _block(
            "tripwire: greenwash engine error (exit "
            f"{result.returncode}). Failing closed.\n{tail}"
        )
    try:
        decision = json.loads(out.splitlines()[-1])
    except Exception:
        return _block(
            "tripwire: greenwash produced non-JSON hook output. Failing closed.\n"
            + out[-1500:]
        )

    if decision.get("decision") == "block":
        reason = decision.get("reason") or "greenwash: blocking finding."
        return _block(reason + "\ntripwire: fix the production code; do not weaken the judge.")
    return _allow()


if __name__ == "__main__":
    raise SystemExit(main())
