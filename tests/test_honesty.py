"""H1: --no-verify honesty surface."""

from __future__ import annotations

import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPT = os.path.join(ROOT, "hooks", "tripwire_honesty.py")


class Honesty(unittest.TestCase):
    def test_h1_1_script(self) -> None:
        result = subprocess.run(
            [sys.executable, SCRIPT],
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("--no-verify", result.stdout)
        self.assertIn("required status check", result.stdout)


if __name__ == "__main__":
    unittest.main()
