#!/usr/bin/env python3
"""H1: say what --no-verify does. Do not pretend it is solved."""

from __future__ import annotations

TEXT = """tripwire honesty
--no-verify skips git's own hooks. It does not skip Claude PreToolUse:
an agent `git commit --no-verify` still hits tripwire_pretooluse.py.
A human at a raw terminal `git commit --no-verify` bypasses git hooks
and also bypasses tripwire, because tripwire is not a git hook.
Merge enforcement is a required status check, not a local hook.
"""


def main() -> int:
    import sys

    sys.stdout.write(TEXT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
