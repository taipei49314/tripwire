"""M3 locks (SPEC section 3, S1-S6). Skills are method, not enforcement."""

from __future__ import annotations

import json
import os
import re
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SKILLS = os.path.join(ROOT, "skills")
SETTINGS = os.path.join(ROOT, ".claude", "settings.json")
NAMES = ("preregister", "adversarial-verify", "verdict-format")


def _skill_md(name: str) -> str:
    path = os.path.join(SKILLS, name, "SKILL.md")
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class SkillsPresent(unittest.TestCase):
    def test_s1_three_skills_named(self) -> None:
        for name in NAMES:
            text = _skill_md(name)
            self.assertTrue(text.startswith("---\n"), name)
            match = re.search(r"^name:\s*(\S+)\s*$", text, re.M)
            self.assertIsNotNone(match, name)
            self.assertEqual(match.group(1), name)

    def test_s2_preregister_tokens(self) -> None:
        text = _skill_md("preregister").lower()
        self.assertIn("claim before measure", text)
        self.assertIn("no backfill", text)

    def test_s3_adversarial_names_gates(self) -> None:
        text = _skill_md("adversarial-verify")
        for token in ("greenwash", "walkaround", "phaseledger", "git push"):
            self.assertIn(token, text)

    def test_s4_verdict_vocabulary(self) -> None:
        text = _skill_md("verdict-format")
        for token in (
            "ADMITTED",
            "BYPASSED",
            "NO_LEDGER",
            "NO_PHASE_ADVANCED",
            "permissionDecision",
            "isError",
        ):
            self.assertIn(token, text)

    def test_s5_skills_not_in_hooks(self) -> None:
        with open(SETTINGS, encoding="utf-8") as fh:
            blob = json.dumps(json.load(fh))
        self.assertNotIn("SKILL.md", blob)
        self.assertNotIn("skills/", blob)


if __name__ == "__main__":
    unittest.main()
