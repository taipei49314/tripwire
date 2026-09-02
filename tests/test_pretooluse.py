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
        self.assertEqual(pre[0]["matcher"], "Bash")
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


if __name__ == "__main__":
    unittest.main()
