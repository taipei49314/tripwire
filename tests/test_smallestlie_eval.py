"""smallestlie evaluation locks (SPEC E1–E5). Not connected. No network."""

from __future__ import annotations

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

if os.path.join(ROOT, "mcp") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "mcp"))
if os.path.join(ROOT, "hooks") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "hooks"))

import tripwire_mcp as mcp  # noqa: E402  # type: ignore


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read().replace("\r\n", "\n")


class SmallestlieStaysOff(unittest.TestCase):
    def test_e1_spec_says_not_connected(self) -> None:
        spec = _read(os.path.join(ROOT, "SPEC.md"))
        self.assertIn("不接", spec)
        self.assertIn("git tag", spec)
        self.assertIn("smallestlie", spec)

    def test_e2_tools_list_unchanged(self) -> None:
        reply = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = [t["name"] for t in reply["result"]["tools"]]
        self.assertEqual(len(names), 6)
        self.assertNotIn("smallestlie", names)
        joined = " ".join(names)
        self.assertNotIn("smallestlie", joined)

    def test_e3_enforcement_paths_do_not_call_it(self) -> None:
        files = (
            os.path.join(ROOT, "hooks", "tripwire_stop.py"),
            os.path.join(ROOT, "hooks", "tripwire_pretooluse.py"),
            os.path.join(ROOT, "scripts", "ci_greenwash.py"),
            os.path.join(ROOT, ".github", "workflows", "tripwire.yml"),
        )
        for path in files:
            blob = _read(path)
            self.assertNotIn("smallestlie", blob, path)

    def test_e4_installer_does_not_clone_it(self) -> None:
        blob = _read(os.path.join(ROOT, "scripts", "install.ps1"))
        self.assertNotIn("smallestlie", blob)


if __name__ == "__main__":
    unittest.main()
