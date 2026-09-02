"""M4 locks (SPEC CI1–CI11). Stdlib only; no network."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WORKFLOW = os.path.join(ROOT, ".github", "workflows", "tripwire.yml")
RULESET = os.path.join(ROOT, ".github", "required-ruleset.json")
SCRIPT = os.path.join(ROOT, "scripts", "ci_greenwash.py")
HONESTY = os.path.join(ROOT, "hooks", "tripwire_honesty.py")
VENDOR_SRC = os.path.join(ROOT, "vendor", "greenwash", "src")
FORBIDDEN = ("walkaround", "phaseledger", "charterlock", "tripwire_mcp", "unasked")

STRONG_TEST = "def test_invoice_total():\n    total = 105\n    assert total == 105\n"
WEAK_TEST = "def test_invoice_total():\n    total = 105\n    assert total > 0\n"


def _read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read().replace("\r\n", "\n")


def git(cwd: str, *args: str) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def run_ci(cwd: str, extra_args: list[str], env_extra: dict | None = None) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    if env_extra:
        env.update(env_extra)
    return subprocess.run(
        [sys.executable, SCRIPT, *extra_args],
        cwd=cwd,
        capture_output=True,
        text=True,
        timeout=60,
        env=env,
    )


class WorkflowLocks(unittest.TestCase):
    def setUp(self) -> None:
        self.wf = _read(WORKFLOW)

    def test_ci1_job_id_and_name(self) -> None:
        self.assertRegex(self.wf, r"(?m)^jobs:\n  tripwire:\n    name: tripwire\n")

    def test_ci2_calls_entrypoint(self) -> None:
        self.assertIn("scripts/ci_greenwash.py", self.wf)
        src = _read(SCRIPT)
        self.assertIn("vendor", src)
        self.assertIn("greenwash", src)
        self.assertIn("check", src)
        self.assertIn("--fail-on", src)
        self.assertIn("high", src)

    def test_ci4_pull_request_triple_dot(self) -> None:
        self.assertIn("pull_request.base.sha", self.wf)
        self.assertIn("${PR_BASE}...HEAD", self.wf)
        self.assertNotIn("pull_request_target", self.wf)

    def test_ci5_push_before_not_always_head1(self) -> None:
        self.assertIn("${BEFORE}...HEAD", self.wf)
        self.assertIn("0000000000000000000000000000000000000000", self.wf)
        self.assertIn("HEAD~1...HEAD", self.wf)
        self.assertIn("skip=true", self.wf)

    def test_ci6_no_session_judges(self) -> None:
        blob = self.wf + "\n" + _read(SCRIPT)
        for word in FORBIDDEN:
            self.assertNotIn(word, blob, word)

    def test_ci7_uses_are_shas(self) -> None:
        pins = re.findall(r"(?m)^\s+uses:\s+(\S+)", self.wf)
        self.assertTrue(pins)
        for pin in pins:
            self.assertRegex(pin, r"@[0-9a-f]{40}$", pin)
            self.assertNotRegex(pin, r"@v\d", pin)

    def test_permissions_and_credentials(self) -> None:
        self.assertIn("contents: read", self.wf)
        self.assertIn("persist-credentials: false", self.wf)
        self.assertIn("v0.1.47", self.wf)


class RulesetLocks(unittest.TestCase):
    def test_ci8_ruleset_payload(self) -> None:
        data = json.loads(_read(RULESET))
        self.assertEqual(data.get("enforcement"), "active")
        include = data["conditions"]["ref_name"]["include"]
        self.assertIn("~DEFAULT_BRANCH", include)
        rule = data["rules"][0]
        self.assertEqual(rule["type"], "required_status_checks")
        params = rule["parameters"]
        self.assertTrue(params["strict_required_status_checks_policy"])
        contexts = [c["context"] for c in params["required_status_checks"]]
        self.assertEqual(contexts, ["tripwire"])


class Entrypoint(unittest.TestCase):
    def setUp(self) -> None:
        self.assertTrue(os.path.isdir(VENDOR_SRC), "vendored greenwash missing")
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

    def test_ci3_missing_argv(self) -> None:
        proc = run_ci(self.repo, [])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Failing closed", (proc.stdout or "") + (proc.stderr or ""))

    def test_ci3_missing_vendor(self) -> None:
        proc = run_ci(
            self.repo,
            ["HEAD~1...HEAD"],
            env_extra={"TRIPWIRE_GREENWASH_SRC": os.path.join(self.repo, "nope")},
        )
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Failing closed", (proc.stdout or "") + (proc.stderr or ""))

    def test_ci3_unresolvable_left(self) -> None:
        proc = run_ci(self.repo, ["deadbeefdeadbeefdeadbeefdeadbeefdeadbeef...HEAD"])
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("Failing closed", (proc.stdout or "") + (proc.stderr or ""))

    def test_ci9_washed_range_exits_nonzero(self) -> None:
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "wash")
        proc = run_ci(self.repo, ["HEAD~1...HEAD"])
        self.assertNotEqual(proc.returncode, 0, proc.stdout + proc.stderr)


class HonestyM4(unittest.TestCase):
    def test_ci11_workflow_is_not_the_ruleset(self) -> None:
        result = subprocess.run(
            [sys.executable, HONESTY],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        text = result.stdout.lower()
        self.assertIn("workflow", text)
        self.assertIn("ruleset", text)
        self.assertIn("--no-verify", result.stdout)


if __name__ == "__main__":
    unittest.main()
