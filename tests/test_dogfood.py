"""Dogfood field + CODEOWNERS locks (SPEC D1–D5, CO1–CO2). No network."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WALKAROUND = os.path.join(ROOT, "vendor", "walkaround")
PHASELEDGER = os.path.join(ROOT, "vendor", "phaseledger")
HONESTY = os.path.join(ROOT, "hooks", "tripwire_honesty.py")
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "tripwire.yml")
CI_SCRIPT = os.path.join(ROOT, "scripts", "ci_greenwash.py")


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read().replace("\r\n", "\n")


class DogfoodField(unittest.TestCase):
    def test_d1_plan_advanced(self) -> None:
        ledger = os.path.join(ROOT, ".phaseledger", "ledger.json")
        self.assertTrue(os.path.isfile(ledger))
        env = dict(os.environ)
        env["PYTHONPATH"] = PHASELEDGER + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-m", "phaseledger", "status", "--ledger", os.path.join(ROOT, ".phaseledger")],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=ROOT,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertIn("- plan: ADVANCED |", proc.stdout)

    def test_d2_charter_present(self) -> None:
        self.assertTrue(os.path.isfile(os.path.join(ROOT, ".charterlock", "charter.json")))

    def test_d3_receipt_admitted(self) -> None:
        receipt = os.path.join(ROOT, ".walkaround", "receipt.json")
        self.assertTrue(os.path.isfile(receipt))
        env = dict(os.environ)
        env["PYTHONPATH"] = WALKAROUND + os.pathsep + env.get("PYTHONPATH", "")
        proc = subprocess.run(
            [sys.executable, "-m", "walkaround", "--root", ROOT, "verify"],
            capture_output=True,
            text=True,
            timeout=30,
            env=env,
            cwd=ROOT,
        )
        text = (proc.stdout or "") + "\n" + (proc.stderr or "")
        self.assertEqual(proc.returncode, 0, text)
        self.assertIn("ADMITTED", text)

    def test_d5_ci_still_session_free(self) -> None:
        blob = _read(CI_SCRIPT) + "\n" + _read(WORKFLOW)
        for word in ("walkaround", "phaseledger", "charterlock"):
            self.assertNotIn(word, blob, word)


class Codeowners(unittest.TestCase):
    def test_co1_github_owned(self) -> None:
        text = _read(os.path.join(ROOT, ".github", "CODEOWNERS"))
        self.assertIn(".github/", text)
        self.assertIn("@taipei49314", text)

    def test_co2_honesty_not_required_review(self) -> None:
        proc = subprocess.run(
            [sys.executable, HONESTY],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(proc.returncode, 0)
        lower = proc.stdout.lower()
        self.assertIn("codeowners", lower)
        self.assertIn("required review", lower)


if __name__ == "__main__":
    unittest.main()
