"""smallestlie evaluation (E1, E3) plus M5 MCP probe locks. No network."""

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


class SmallestlieEvalHistory(unittest.TestCase):
    def test_e1_eval_section_still_records_the_hold(self) -> None:
        spec = _read(os.path.join(ROOT, "SPEC.md"))
        self.assertIn("不接", spec)
        self.assertIn("git tag", spec)
        self.assertIn("smallestlie", spec)
        self.assertIn("### M5", spec)

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


class M5Probe(unittest.TestCase):
    def test_m5_1_seventh_tool_is_repo_probe(self) -> None:
        reply = mcp.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = [t["name"] for t in reply["result"]["tools"]]
        self.assertEqual(
            names,
            [
                "trust.score",
                "ledger.preregister",
                "ledger.score",
                "receipt.verify",
                "repo.investigate",
                "repo.passport",
                "repo.probe",
            ],
        )

    def test_m5_2_doctor_invoked(self) -> None:
        reply = mcp.handle(
            {
                "jsonrpc": "2.0",
                "id": 21,
                "method": "tools/call",
                "params": {"name": "repo.probe", "arguments": {}},
            }
        )
        text = reply["result"]["content"][0]["text"]
        self.assertIn("doctor", text.lower(), text)
        self.assertNotIn("Failing closed: the query plane cannot certify", text)
        if sys.version_info >= (3, 12):
            self.assertFalse(reply["result"]["isError"], text)
            self.assertIn("doctor: PASS", text)
        else:
            self.assertIn("python>=3.12", text)

    def test_m5_3_campaign_missing_target(self) -> None:
        reply = mcp.handle(
            {
                "jsonrpc": "2.0",
                "id": 22,
                "method": "tools/call",
                "params": {"name": "repo.probe", "arguments": {"mode": "campaign"}},
            }
        )
        text = reply["result"]["content"][0]["text"]
        self.assertTrue(reply["result"]["isError"])
        self.assertTrue("missing" in text.lower() or "campaign" in text.lower())

    def test_m5_4_missing_vendor_fail_closed(self) -> None:
        old = os.environ.get("TRIPWIRE_SMALLESTLIE_SRC")
        os.environ["TRIPWIRE_SMALLESTLIE_SRC"] = os.path.join(ROOT, "nope-smallestlie")
        try:
            reply = mcp.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 23,
                    "method": "tools/call",
                    "params": {"name": "repo.probe", "arguments": {}},
                }
            )
        finally:
            if old is None:
                os.environ.pop("TRIPWIRE_SMALLESTLIE_SRC", None)
            else:
                os.environ["TRIPWIRE_SMALLESTLIE_SRC"] = old
        text = reply["result"]["content"][0]["text"]
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("Failing closed", text)

    def test_m5_6_installer_pins_tag(self) -> None:
        blob = _read(os.path.join(ROOT, "scripts", "install.ps1"))
        self.assertIn("smallestlie", blob)
        self.assertIn("v0.7.1", blob)


if __name__ == "__main__":
    unittest.main()
