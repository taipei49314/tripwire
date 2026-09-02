"""M2 locks (SPEC section 3). Protocol + receipt.verify; missing vendors fail closed."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP = os.path.join(ROOT, "mcp", "tripwire_mcp.py")
HOOKS = os.path.join(ROOT, "hooks")
WALKAROUND_ROOT = os.environ.get("TRIPWIRE_WALKAROUND_SRC") or os.path.join(
    ROOT, "vendor", "walkaround"
)
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")

if HOOKS not in sys.path:
    sys.path.insert(0, HOOKS)
sys.path.insert(0, os.path.join(ROOT, "mcp"))

import tripwire_mcp as mcp  # noqa: E402  # type: ignore


def plant_admitted(repo: str) -> None:
    if WALKAROUND_ROOT not in sys.path:
        sys.path.insert(0, WALKAROUND_ROOT)
    from walkaround.admit import OrganResult
    from walkaround.session import open_session

    session = open_session(repo)
    session.set_contract(
        {
            "schema_version": 1,
            "goal": "tripwire mcp fixture",
            "required_organs": ["o"],
        }
    )
    session.record_write("tests/test_billing.py")
    session.record_observe(["tests/test_billing.py"])
    session.record_organ(OrganResult("o", True, "PASS", output_digest="ab" * 32))
    session.close("done")


def decode_all(raw: bytes) -> list[dict]:
    leftover = raw
    out: list[dict] = []
    while leftover.strip():
        msg, leftover, _ = mcp.read_message(b"", leftover)
        if msg is None:
            break
        out.append(msg)
    return out


class Protocol(unittest.TestCase):
    def test_m2_1_initialize(self) -> None:
        reply = mcp.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
        self.assertEqual(reply["result"]["serverInfo"]["name"], "tripwire")
        self.assertEqual(reply["result"]["protocolVersion"], "2024-11-05")
        self.assertIn("tools", reply["result"]["capabilities"])

    def test_m2_2_tools_list_order(self) -> None:
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
            ],
        )

    def test_m2_3_unknown_tool_is_error_not_crash(self) -> None:
        reply = mcp.handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "not.a.tool", "arguments": {}},
            }
        )
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("Failing closed", reply["result"]["content"][0]["text"])

    def test_m2_4_missing_vendor_fail_closed(self) -> None:
        old = os.environ.get("TRIPWIRE_TRUST_METER_SRC")
        os.environ["TRIPWIRE_TRUST_METER_SRC"] = os.path.join(ROOT, "nope-trust")
        try:
            reply = mcp.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 4,
                    "method": "tools/call",
                    "params": {"name": "trust.score", "arguments": {"target": "."}},
                }
            )
        finally:
            if old is None:
                os.environ.pop("TRIPWIRE_TRUST_METER_SRC", None)
            else:
                os.environ["TRIPWIRE_TRUST_METER_SRC"] = old
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("Failing closed", reply["result"]["content"][0]["text"])

    def test_parse_error(self) -> None:
        reply = mcp.handle("not-an-object")
        self.assertEqual(reply["error"]["code"], -32600)

    def test_stdio_roundtrip_initialize(self) -> None:
        proc = subprocess.Popen(
            [sys.executable, MCP],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        payload = mcp.encode_message(
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        )
        out, err = proc.communicate(payload, timeout=15)
        self.assertEqual(proc.returncode, 0, err.decode("utf-8", errors="replace"))
        msgs = decode_all(out)
        self.assertEqual(msgs[0]["result"]["serverInfo"]["name"], "tripwire")


class ReceiptVerify(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            os.path.isdir(os.path.join(WALKAROUND_ROOT, "walkaround")),
            "vendored walkaround missing",
        )

    def test_m2_5_admitted_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            plant_admitted(tmp)
            reply = mcp.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 5,
                    "method": "tools/call",
                    "params": {"name": "receipt.verify", "arguments": {"root": tmp}},
                }
            )
        self.assertFalse(reply["result"]["isError"], reply["result"]["content"][0]["text"])
        self.assertIn("ADMITTED", reply["result"]["content"][0]["text"])

    def test_m2_6_no_receipt_is_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reply = mcp.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 6,
                    "method": "tools/call",
                    "params": {"name": "receipt.verify", "arguments": {"root": tmp}},
                }
            )
        self.assertTrue(reply["result"]["isError"])


class VendorPins(unittest.TestCase):
    def test_m2_vendor_trees_present(self) -> None:
        for rel in (
            os.path.join("vendor", "trust-meter", "src", "trust_meter"),
            os.path.join("vendor", "unasked", "src", "unasked"),
            os.path.join("vendor", "nullbench", "src", "nullbench"),
        ):
            self.assertTrue(os.path.isdir(os.path.join(ROOT, rel)), rel)

    def test_live_trust_score(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reply = mcp.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 7,
                    "method": "tools/call",
                    "params": {"name": "trust.score", "arguments": {"target": tmp}},
                }
            )
        text = reply["result"]["content"][0]["text"]
        self.assertFalse(reply["result"]["isError"], text)
        self.assertIn("overall_score", text)

    def test_live_unasked_doctor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            reply = mcp.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 8,
                    "method": "tools/call",
                    "params": {"name": "repo.investigate", "arguments": {"workspace": tmp}},
                }
            )
        text = reply["result"]["content"][0]["text"]
        self.assertFalse(reply["result"]["isError"], text)
        self.assertIn("doctor", text)

    def test_m21_investigate_missing_args(self) -> None:
        reply = mcp.handle(
            {
                "jsonrpc": "2.0",
                "id": 9,
                "method": "tools/call",
                "params": {
                    "name": "repo.investigate",
                    "arguments": {"workspace": ".", "mode": "full"},
                },
            }
        )
        text = reply["result"]["content"][0]["text"]
        self.assertTrue(reply["result"]["isError"])
        self.assertTrue("missing" in text.lower() or "investigate" in text.lower())

    def test_m21_passport_missing_vendor(self) -> None:
        old = os.environ.get("TRIPWIRE_REPOPASS_SRC")
        os.environ["TRIPWIRE_REPOPASS_SRC"] = os.path.join(ROOT, "nope-passport")
        try:
            reply = mcp.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 10,
                    "method": "tools/call",
                    "params": {"name": "repo.passport", "arguments": {"root": "."}},
                }
            )
        finally:
            if old is None:
                os.environ.pop("TRIPWIRE_REPOPASS_SRC", None)
            else:
                os.environ["TRIPWIRE_REPOPASS_SRC"] = old
        self.assertTrue(reply["result"]["isError"])
        self.assertIn("Failing closed", reply["result"]["content"][0]["text"])

    def test_m21_live_nullbench_freeze(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            init = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nullbench",
                    "init",
                    "try1",
                    "-d",
                    "demo649",
                    "--path",
                    tmp,
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(init.returncode, 0, init.stderr)
            study = os.path.join(tmp, "try1")
            add = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "nullbench",
                    "strategy",
                    "add",
                    "random",
                    "--study",
                    study,
                    "--tickets",
                    "5",
                    "--seed",
                    "1",
                ],
                capture_output=True,
                text=True,
                timeout=60,
            )
            self.assertEqual(add.returncode, 0, add.stderr)
            reply = mcp.handle(
                {
                    "jsonrpc": "2.0",
                    "id": 11,
                    "method": "tools/call",
                    "params": {
                        "name": "ledger.preregister",
                        "arguments": {"study": study},
                    },
                }
            )
        text = reply["result"]["content"][0]["text"]
        self.assertFalse(reply["result"]["isError"], text)


class NotEnforcement(unittest.TestCase):
    def test_m2_7_hooks_do_not_call_mcp(self) -> None:
        with open(SETTINGS, encoding="utf-8") as fh:
            data = json.load(fh)
        blob = json.dumps(data)
        self.assertNotIn("tripwire_mcp", blob)
        self.assertNotIn("mcp/", blob)


if __name__ == "__main__":
    unittest.main()
