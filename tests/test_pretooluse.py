"""M1-C locks (SPEC section 3, C2-C11). Pure stdlib; no network."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOOK = os.path.join(ROOT, "hooks", "tripwire_pretooluse.py")
VENDOR_SRC = os.path.join(ROOT, "vendor", "greenwash", "src")
HOOKS = os.path.join(ROOT, "hooks")

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


def bash_payload(cwd: str, command: str) -> dict:
    return {"cwd": cwd, "tool_name": "Bash", "tool_input": {"command": command}}


class SettingsWired(unittest.TestCase):
    def test_c1_pretooluse_bash_matcher(self) -> None:
        path = os.path.join(ROOT, ".claude", "settings.json")
        with open(path, encoding="utf-8") as fh:
            data = json.loads(fh.read())
        pre = data["hooks"]["PreToolUse"]
        self.assertTrue(pre)
        matcher = pre[0]["matcher"]
        self.assertIn("Bash", matcher)
        self.assertIn("Write", matcher)
        self.assertIn("Edit", matcher)
        command = pre[0]["hooks"][0]["command"]
        self.assertIn("tripwire_pretooluse.py", command)


class DetectVerbs(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        if HOOKS not in sys.path:
            sys.path.insert(0, HOOKS)
        import gate as gate_mod  # noqa: PLC0415

        cls.gate = gate_mod

    def test_c7_commit_tree_and_graph_do_not_trigger(self) -> None:
        self.assertEqual(self.gate.git_commit_push_verbs("git commit-tree HEAD^{tree}"), frozenset())
        self.assertEqual(self.gate.git_commit_push_verbs("git commit-graph write"), frozenset())

    def test_commit_and_push_in_chain(self) -> None:
        verbs = self.gate.git_commit_push_verbs("git add . && git commit -m x && git push")
        self.assertEqual(verbs, frozenset({"commit", "push"}))

    def test_git_c_and_exe(self) -> None:
        self.assertEqual(
            self.gate.git_commit_push_verbs(r"git.exe -C C:\tmp commit -m x"),
            frozenset({"commit"}),
        )

    def test_c2_parse_all_and_refspec(self) -> None:
        parsed = self.gate.parse_git_push("git push --all origin")
        self.assertTrue(parsed["all"])
        parsed = self.gate.parse_git_push("git push origin HEAD:other")
        self.assertEqual(parsed["refspecs"], ["HEAD"])
        parsed = self.gate.parse_git_push("git push origin side:other")
        self.assertEqual(parsed["refspecs"], ["side"])

    def test_path_is_meta_keeps_leading_dot(self) -> None:
        self.assertTrue(self.gate.path_is_meta(".phaseledger/notes.txt"))
        self.assertTrue(self.gate.path_is_meta("./.walkaround/receipt.json"))
        self.assertTrue(self.gate.path_is_meta(".charterlock"))
        self.assertFalse(self.gate.path_is_meta("src/app.py"))
        self.assertFalse(self.gate.path_is_meta("phaseledger/notes.txt"))


class PreToolUseGate(unittest.TestCase):
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

    def parsed(self, stdout: str) -> dict:
        if not stdout:
            return {}
        return json.loads(stdout.splitlines()[-1])

    def specific(self, stdout: str) -> dict:
        return self.parsed(stdout).get("hookSpecificOutput") or {}

    def test_c2_unrelated_bash_allows(self) -> None:
        code, out, _ = run_hook(bash_payload(self.repo, "git status"))
        self.assertEqual(code, 0)
        self.assertEqual(self.parsed(out), {})

    def test_c3_commit_washed_worktree_denies(self) -> None:
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        code, out, _ = run_hook(bash_payload(self.repo, "git add . && git commit -m wash"))
        self.assertEqual(code, 0)
        spec = self.specific(out)
        self.assertEqual(spec.get("permissionDecision"), "deny")
        self.assertIn("greenwash", spec.get("permissionDecisionReason", ""))

    def test_c4_commit_clean_allows(self) -> None:
        code, out, _ = run_hook(bash_payload(self.repo, "git commit -m ok"))
        self.assertEqual(code, 0)
        self.assertEqual(self.parsed(out), {})

    def test_c4_commit_honest_change_allows(self) -> None:
        with open(os.path.join(self.repo, "billing.py"), "w", encoding="utf-8") as f:
            f.write("def total():\n    return 105\n\n\ndef tax():\n    return 5\n")
        code, out, _ = run_hook(bash_payload(self.repo, "git commit -am honest"))
        self.assertEqual(code, 0)
        self.assertEqual(self.parsed(out), {})

    def test_c5_push_already_committed_wash_denies(self) -> None:
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "wash already in history")
        # worktree is clean vs HEAD — M0 Stop would allow
        code, out, _ = run_hook(bash_payload(self.repo, "git push"))
        self.assertEqual(code, 0)
        spec = self.specific(out)
        self.assertEqual(spec.get("permissionDecision"), "deny")
        self.assertIn("greenwash", spec.get("permissionDecisionReason", ""))

    def test_c6_push_clean_range_allows(self) -> None:
        code, out, _ = run_hook(bash_payload(self.repo, "git push"))
        self.assertEqual(code, 0)
        self.assertEqual(self.parsed(out), {})

    def test_c8_malformed_payload_fails_closed(self) -> None:
        code, out, _ = run_hook_bytes(b"definitely not json")
        self.assertEqual(code, 0)
        spec = self.specific(out)
        self.assertEqual(spec.get("permissionDecision"), "deny")
        self.assertIn("Failing closed", spec.get("permissionDecisionReason", ""))

    def test_c9_missing_judge_fails_closed(self) -> None:
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        code, out, _ = run_hook(
            bash_payload(self.repo, "git commit -am x"),
            env_extra={"TRIPWIRE_GREENWASH_SRC": os.path.join(self.repo, "nope")},
        )
        self.assertEqual(code, 0)
        spec = self.specific(out)
        self.assertEqual(spec.get("permissionDecision"), "deny")
        self.assertIn("Failing closed", spec.get("permissionDecisionReason", ""))

    def test_c10_non_git_directory_allows(self) -> None:
        with tempfile.TemporaryDirectory() as plain:
            code, out, _ = run_hook(bash_payload(plain, "git commit -m x"))
        self.assertEqual(code, 0)
        self.assertEqual(self.parsed(out), {})

    def test_c2_1_push_all_washes_side_branch(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "side")
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "wash on side")
        git(self.repo, "checkout", "-q", "-")
        code, out, _ = run_hook(bash_payload(self.repo, "git push --all origin"))
        self.assertEqual(code, 0)
        spec = self.specific(out)
        self.assertEqual(spec.get("permissionDecision"), "deny")
        self.assertIn("greenwash", spec.get("permissionDecisionReason", ""))

    def test_c2_2_push_refspec_scans_head(self) -> None:
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "wash on HEAD")
        code, out, _ = run_hook(bash_payload(self.repo, "git push origin HEAD:other"))
        self.assertEqual(code, 0)
        spec = self.specific(out)
        self.assertEqual(spec.get("permissionDecision"), "deny")
        self.assertIn("greenwash", spec.get("permissionDecisionReason", ""))

    def test_c2_2_push_refspec_scans_side_src(self) -> None:
        git(self.repo, "checkout", "-q", "-b", "side")
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "wash on side")
        git(self.repo, "checkout", "-q", "-")
        code, out, _ = run_hook(bash_payload(self.repo, "git push origin side:other"))
        self.assertEqual(code, 0)
        spec = self.specific(out)
        self.assertEqual(spec.get("permissionDecision"), "deny")
        self.assertIn("greenwash", spec.get("permissionDecisionReason", ""))

    def test_h1_2_no_verify_still_scans(self) -> None:
        with open(os.path.join(self.repo, "tests", "test_billing.py"), "w", encoding="utf-8") as f:
            f.write(WEAK_TEST)
        code, out, _ = run_hook(bash_payload(self.repo, "git commit --no-verify -am wash"))
        self.assertEqual(code, 0)
        spec = self.specific(out)
        self.assertEqual(spec.get("permissionDecision"), "deny")
        self.assertIn("greenwash", spec.get("permissionDecisionReason", ""))

    def test_w2_write_without_ledger_denies(self) -> None:
        code, out, _ = run_hook(
            {
                "cwd": self.repo,
                "tool_name": "Write",
                "tool_input": {"file_path": "src/app.py"},
            }
        )
        self.assertEqual(code, 0)
        spec = self.specific(out)
        self.assertEqual(spec.get("permissionDecision"), "deny")
        self.assertIn("NO_LEDGER", spec.get("permissionDecisionReason", ""))

    def test_w5_meta_write_allowed(self) -> None:
        code, out, _ = run_hook(
            {
                "cwd": self.repo,
                "tool_name": "Write",
                "tool_input": {"file_path": ".phaseledger/notes.txt"},
            }
        )
        self.assertEqual(code, 0)
        self.assertEqual(self.parsed(out), {})


class WritePlanGate(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = self.tmp.name
        git(self.repo, "init", "-q")
        git(self.repo, "config", "user.name", "tripwire-test")
        git(self.repo, "config", "user.email", "tripwire-test@example.invalid")
        with open(os.path.join(self.repo, "ok.py"), "w", encoding="utf-8") as f:
            f.write("x = 1\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-q", "-m", "base")

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_w3_pending_plan_denies_src(self) -> None:
        sys.path.insert(0, os.path.join(ROOT, "vendor", "phaseledger"))
        from phaseledger.ledger import PhaseLedger

        PhaseLedger.open(os.path.join(self.repo, ".phaseledger"))
        code, out, _ = run_hook(
            {
                "cwd": self.repo,
                "tool_name": "Write",
                "tool_input": {"file_path": "src/app.py"},
            }
        )
        self.assertEqual(code, 0)
        spec = json.loads(out.splitlines()[-1]).get("hookSpecificOutput") or {}
        self.assertEqual(spec.get("permissionDecision"), "deny")
        self.assertIn("PLAN_NOT_ADVANCED", spec.get("permissionDecisionReason", ""))

    def test_w4_advanced_plan_allows_src(self) -> None:
        sys.path.insert(0, os.path.join(ROOT, "vendor", "phaseledger"))
        from phaseledger.ledger import PhaseLedger

        ledger = PhaseLedger.open(os.path.join(self.repo, ".phaseledger"))
        ledger.record_claim("plan", "plan-ok")
        ledger.record_measure(
            "plan",
            {
                "phase": "plan",
                "claim": "plan-ok",
                "artifact_present": True,
                "artifact_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "checks": [{"name": "ok", "passed": True}],
            },
        )
        ledger.advance("plan")
        code, out, _ = run_hook(
            {
                "cwd": self.repo,
                "tool_name": "Write",
                "tool_input": {"file_path": "src/app.py"},
            }
        )
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out.splitlines()[-1]) if out else {}, {})


if __name__ == "__main__":
    unittest.main()
