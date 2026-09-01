"""M0 locks (SPEC section 3, A2-A7). Pure stdlib; no network.

Requires the vendored judge (scripts/install.ps1) - tests fail loudly rather
than skip, because a missing judge is exactly the failure the gate exists to
catch.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "tripwire_stop.py")
VENDOR_SRC = os.path.join(ROOT, "vendor", "greenwash", "src")

STRONG_TEST = "def test_invoice_total():\n    total = 105\n    assert total == 105\n"
WEAK_TEST = "def test_invoice_total():\n    total = 105\n    assert total > 0\n"


def run_hook(payload: dict, env_extra: dict | None = None) -> tuple[int, str, str]:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        [sys.executable, HOOK],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        timeout=120,
        env=env,
    )
    return result.returncode, result.stdout.strip(), result.stderr


def git(cwd: str, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


class StopGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            os.path.isdir(VENDOR_SRC),
            "vendored greenwash missing - run scripts/install.ps1 first",
        )
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "tripwire-test")
        git(self.repo, "config", "user.email", "tripwire-test@example.invalid")
        os.makedirs(os.path.join(self.repo, "tests"), exist_ok=True)
        with open(os.path.join(self.repo, "billing.py"), "w", encoding="utf-8") as f:
            f.write("def total():\n    return 105\n")
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(STRONG_TEST)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "baseline")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def decision(self, stdout: str) -> dict:
        return json.loads(stdout.splitlines()[-1]) if stdout else {}

    def test_a2_weakened_assertion_blocks(self) -> None:
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        code, out, _ = run_hook({"cwd": self.repo})
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        self.assertIn("greenwash", verdict.get("reason", ""))

    def test_a3_clean_tree_allows(self) -> None:
        code, out, _ = run_hook({"cwd": self.repo})
        self.assertEqual(code, 0)
        self.assertEqual(self.decision(out), {})

    def test_a3_honest_change_allows(self) -> None:
        with open(os.path.join(self.repo, "billing.py"), "w", encoding="utf-8") as f:
            f.write("def total():\n    return 105\n\n\ndef tax():\n    return 5\n")
        code, out, _ = run_hook({"cwd": self.repo})
        self.assertEqual(code, 0)
        self.assertEqual(self.decision(out), {})

    def test_a4_stop_hook_active_short_circuits(self) -> None:
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        code, out, _ = run_hook({"cwd": self.repo, "stop_hook_active": True})
        self.assertEqual(code, 0)
        self.assertEqual(self.decision(out), {})

    def test_a5_missing_judge_fails_closed(self) -> None:
        code, out, _ = run_hook(
            {"cwd": self.repo},
            env_extra={"TRIPWIRE_GREENWASH_SRC": os.path.join(self.repo, "nope")},
        )
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        self.assertIn("Failing closed", verdict.get("reason", ""))

    def test_a6_non_git_directory_allows(self) -> None:
        with tempfile.TemporaryDirectory() as plain:
            code, out, _ = run_hook({"cwd": plain})
        self.assertEqual(code, 0)
        self.assertEqual(self.decision(out), {})


if __name__ == "__main__":
    unittest.main()
