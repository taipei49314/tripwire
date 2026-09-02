"""M0 locks (SPEC section 3, A2-A9) and M1-R (R2-R8). Pure stdlib; no network.

Requires the vendored judges (scripts/install.ps1) - tests fail loudly rather
than skip, because a missing judge is exactly the failure the gate exists to
catch.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "tripwire_stop.py")
VENDOR_SRC = os.path.join(ROOT, "vendor", "greenwash", "src")
WALKAROUND_ROOT = os.environ.get("TRIPWIRE_WALKAROUND_SRC") or os.path.join(
    ROOT, "vendor", "walkaround"
)
PHASELEDGER_ROOT = os.environ.get("TRIPWIRE_PHASELEDGER_SRC") or os.path.join(
    ROOT, "vendor", "phaseledger"
)

STRONG_TEST = "def test_invoice_total():\n    total = 105\n    assert total == 105\n"
WEAK_TEST = "def test_invoice_total():\n    total = 105\n    assert total > 0\n"


def run_hook_bytes(stdin: bytes, env_extra: dict | None = None) -> tuple[int, str, str]:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    result = subprocess.run(
        [sys.executable, HOOK],
        input=stdin,
        capture_output=True,
        timeout=120,
        env=env,
    )
    return (
        result.returncode,
        result.stdout.decode("utf-8", errors="replace").strip(),
        result.stderr.decode("utf-8", errors="replace"),
    )


def run_hook(payload: dict, env_extra: dict | None = None) -> tuple[int, str, str]:
    return run_hook_bytes(json.dumps(payload).encode("utf-8"), env_extra)


def git(cwd: str, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def plant_admitted(repo: str) -> None:
    if WALKAROUND_ROOT not in sys.path:
        sys.path.insert(0, WALKAROUND_ROOT)
    from walkaround.admit import OrganResult
    from walkaround.session import open_session

    session = open_session(repo)
    session.set_contract(
        {
            "schema_version": 1,
            "goal": "tripwire stop-gate fixture",
            "required_organs": ["o"],
        }
    )
    session.record_write("tests/test_billing.py")
    session.record_observe(["tests/test_billing.py"])
    session.record_organ(OrganResult("o", True, "PASS", output_digest="ab" * 32))
    session.close("done")


def plant_plan_advanced(repo: str) -> None:
    if PHASELEDGER_ROOT not in sys.path:
        sys.path.insert(0, PHASELEDGER_ROOT)
    from phaseledger.ledger import PhaseLedger

    ledger = PhaseLedger.open(os.path.join(repo, ".phaseledger"))
    claim = "plan-ok"
    ledger.record_claim("plan", claim)
    ledger.record_measure(
        "plan",
        {
            "phase": "plan",
            "claim": claim,
            "artifact_present": True,
            "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "checks": [{"name": "ok", "passed": True}],
        },
    )
    ledger.advance("plan")


def plant_incomplete(repo: str) -> None:
    if WALKAROUND_ROOT not in sys.path:
        sys.path.insert(0, WALKAROUND_ROOT)
    from walkaround.session import open_session

    session = open_session(repo)
    session.set_contract(
        {
            "schema_version": 1,
            "goal": "tripwire stop-gate fixture",
            "required_organs": ["o"],
        }
    )
    session.record_write("tests/test_billing.py")
    session.record_observe(["tests/test_billing.py"])
    session.close("done")


class StopGateTest(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(
            os.path.isdir(VENDOR_SRC),
            "vendored greenwash missing - run scripts/install.ps1 first",
        )
        self.assertTrue(
            os.path.isdir(os.path.join(WALKAROUND_ROOT, "walkaround")),
            "vendored walkaround missing - run scripts/install.ps1 first",
        )
        self.assertTrue(
            os.path.isdir(os.path.join(PHASELEDGER_ROOT, "phaseledger")),
            "vendored phaseledger missing - run scripts/install.ps1 first",
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
        plant_admitted(self.repo)
        plant_plan_advanced(self.repo)

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

    def test_a8_bom_payload_still_gates(self) -> None:
        """Dogfood day-one regression: PowerShell pipes prepend a UTF-8 BOM.
        The old parser fell back to os.getcwd() and silently allowed."""
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        stdin = json.dumps({"cwd": self.repo}).encode("utf-8-sig")
        code, out, _ = run_hook_bytes(stdin)
        self.assertEqual(code, 0)
        self.assertEqual(self.decision(out).get("decision"), "block")

    def test_a9_malformed_payload_fails_closed(self) -> None:
        code, out, _ = run_hook_bytes(b"definitely not json")
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        self.assertIn("Failing closed", verdict.get("reason", ""))

    def test_r2_no_receipt_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as bare:
            git(bare, "init", "-q")
            git(bare, "config", "user.name", "tripwire-test")
            git(bare, "config", "user.email", "tripwire-test@example.invalid")
            with open(os.path.join(bare, "ok.py"), "w", encoding="utf-8") as f:
                f.write("x = 1\n")
            git(bare, "add", ".")
            git(bare, "commit", "-q", "-m", "bare")
            code, out, _ = run_hook({"cwd": bare})
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        reason = verdict.get("reason", "")
        self.assertTrue("BYPASSED" in reason or "no receipt" in reason, reason)

    def test_r3_admitted_receipt_allows(self) -> None:
        code, out, _ = run_hook({"cwd": self.repo})
        self.assertEqual(code, 0)
        self.assertEqual(self.decision(out), {})

    def test_r4_incomplete_receipt_blocks(self) -> None:
        with tempfile.TemporaryDirectory() as bare:
            git(bare, "init", "-q")
            git(bare, "config", "user.name", "tripwire-test")
            git(bare, "config", "user.email", "tripwire-test@example.invalid")
            os.makedirs(os.path.join(bare, "tests"), exist_ok=True)
            with open(os.path.join(bare, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
                f.write(STRONG_TEST)
            git(bare, "add", ".")
            git(bare, "commit", "-q", "-m", "bare")
            plant_incomplete(bare)
            code, out, _ = run_hook({"cwd": bare})
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        reason = verdict.get("reason", "")
        self.assertIn("INCOMPLETE", reason)
        self.assertIn("MISSING_ORGAN", reason)

    def test_r5_wash_still_blocks_with_admitted_receipt(self) -> None:
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        code, out, _ = run_hook({"cwd": self.repo})
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        self.assertIn("greenwash", verdict.get("reason", ""))

    def test_r6_missing_walkaround_fails_closed(self) -> None:
        code, out, _ = run_hook(
            {"cwd": self.repo},
            env_extra={"TRIPWIRE_WALKAROUND_SRC": os.path.join(self.repo, "nope")},
        )
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        self.assertIn("Failing closed", verdict.get("reason", ""))

    def test_p2_no_ledger_blocks(self) -> None:
        shutil.rmtree(os.path.join(self.repo, ".phaseledger"))
        code, out, _ = run_hook({"cwd": self.repo})
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        self.assertIn("NO_LEDGER", verdict.get("reason", ""))

    def test_p3_skip_ahead_verify_fails(self) -> None:
        path = os.path.join(self.repo, ".phaseledger", "ledger.json")
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        data["states"]["plan"]["advanced"] = False
        data["states"]["implement"]["advanced"] = True
        data["states"]["implement"]["measure_verdict"] = "PASS"
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh)
        code, out, _ = run_hook({"cwd": self.repo})
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        self.assertIn("VERIFY", verdict.get("reason", ""))

    def test_p4_empty_init_not_a_checkpoint(self) -> None:
        shutil.rmtree(os.path.join(self.repo, ".phaseledger"))
        if PHASELEDGER_ROOT not in sys.path:
            sys.path.insert(0, PHASELEDGER_ROOT)
        from phaseledger.ledger import PhaseLedger

        PhaseLedger.open(os.path.join(self.repo, ".phaseledger"))
        code, out, _ = run_hook({"cwd": self.repo})
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        self.assertIn("NO_PHASE_ADVANCED", verdict.get("reason", ""))

    def test_p6_missing_phaseledger_fails_closed(self) -> None:
        code, out, _ = run_hook(
            {"cwd": self.repo},
            env_extra={"TRIPWIRE_PHASELEDGER_SRC": os.path.join(self.repo, "nope")},
        )
        self.assertEqual(code, 0)
        verdict = self.decision(out)
        self.assertEqual(verdict.get("decision"), "block")
        self.assertIn("Failing closed", verdict.get("reason", ""))


if __name__ == "__main__":
    unittest.main()
