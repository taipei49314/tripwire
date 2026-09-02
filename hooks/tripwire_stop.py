#!/usr/bin/env python3
"""tripwire stop gate (M0 + M1-R).

Claude Code Stop hook: before the agent finishes a turn,
  1. run greenwash on HEAD..worktree (M0)
  2. require a walkaround ADMITTED receipt (M1-R)

Speaks the Stop-hook JSON protocol: a decision object on stdout, exit 0
either way.

Judge boundary (SPEC section 2): judges are vendored at pinned tags and
invoked as-is; verdict text passes through unmodified. Fail-closed: a
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


def _walkaround_root() -> str:
    override = os.environ.get("TRIPWIRE_WALKAROUND_SRC")
    if override:
        return override
    return os.path.join(_tripwire_root(), "vendor", "walkaround")


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


def _read_payload() -> dict | None:
    """Read the hook payload. BOM-tolerant; None means malformed (fail closed).

    Empty stdin is tolerated as a manual invocation ({} -> cwd fallback). A
    non-empty, non-JSON payload is NOT guessed around: guessing (the old
    os.getcwd() fallback on parse failure) plus the non-git pass-through
    composed into a silent fail-open, found on dogfood day one.
    """
    raw = sys.stdin.buffer.read()
    text = raw.decode("utf-8-sig", errors="replace").strip()
    if not text:
        return {}
    try:
        parsed = json.loads(text)
    except Exception:
        return None
    return parsed if isinstance(parsed, dict) else None


def main() -> int:
    payload = _read_payload()
    if payload is None:
        return _block(
            "tripwire: malformed hook payload (stdin was not JSON). "
            "Failing closed: the stop gate cannot certify this turn."
        )

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
    return _walkaround_gate(cwd)


def _walkaround_gate(cwd: str) -> int:
    """M1-R: Stop is a done-claim. No ADMITTED receipt → not in the lab."""
    root = _walkaround_root()
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
            timeout=TIMEOUT_SECONDS,
            env=env,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired:
        return _block(
            f"tripwire: walkaround timed out after {TIMEOUT_SECONDS}s. "
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
