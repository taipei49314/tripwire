#!/usr/bin/env python3
"""M4: run vendored greenwash on an explicit git range. Do not guess HEAD~1."""

from __future__ import annotations

import os
import subprocess
import sys

TIMEOUT_SECONDS = 30


def _src() -> str:
    override = os.environ.get("TRIPWIRE_GREENWASH_SRC")
    if override:
        return override
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, "vendor", "greenwash", "src")


def _left(rng: str) -> str:
    if "..." in rng:
        return rng.split("...", 1)[0].strip()
    if ".." in rng:
        return rng.split("..", 1)[0].strip()
    return rng.strip()


def _fail(message: str) -> int:
    sys.stderr.write(message + "\n")
    return 2


def main(argv: list[str] | None = None) -> int:
    args = sys.argv if argv is None else argv
    if len(args) != 2 or not str(args[1]).strip():
        return _fail(
            "tripwire: missing git range. Failing closed: "
            "the merge check cannot certify this push."
        )
    rng = str(args[1]).strip()
    left = _left(rng)
    if not left:
        return _fail(
            "tripwire: empty range left side. Failing closed: "
            "the merge check cannot certify this push."
        )
    src = _src()
    if not os.path.isdir(src):
        return _fail(
            "tripwire: vendored greenwash not found (run scripts/install.ps1). "
            "Failing closed: the merge check cannot certify this push."
        )
    try:
        # Bare 40-hex names pass `rev-parse --verify` even when the object
        # is missing. Peel to a commit so a fake left side fail-closes.
        probe = subprocess.run(
            ["git", "rev-parse", "--verify", left + "^{commit}"],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except Exception as err:
        return _fail(f"tripwire: git rev-parse failed ({err!r}). Failing closed.")
    if probe.returncode != 0:
        return _fail(
            "tripwire: range left side does not resolve. "
            "Failing closed: the merge check cannot certify this push."
        )
    env = dict(os.environ)
    env["PYTHONPATH"] = src + os.pathsep + env.get("PYTHONPATH", "")
    try:
        result = subprocess.run(
            [sys.executable, "-m", "greenwash", "check", rng, "--fail-on", "high"],
            env=env,
            timeout=TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return _fail(
            f"tripwire: greenwash timed out after {TIMEOUT_SECONDS}s. Failing closed."
        )
    except Exception as err:
        return _fail(f"tripwire: greenwash could not run ({err!r}). Failing closed.")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
