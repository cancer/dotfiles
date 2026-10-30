import subprocess
import sys
import os
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "build_state.py"


class BuildStateTests(unittest.TestCase):
    def test_builds_sections_in_order_and_collects_repository_facts(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            cwd = root / "repo"
            cwd.mkdir()
            (cwd / ".git").mkdir()
            (cwd / "pyproject.toml").write_text("", encoding="utf-8")
            (cwd / "tests").mkdir()
            quotes = root / "quotes.txt"
            quotes.write_text('ユーザー: 「この範囲だけ」\n', encoding="utf-8")
            output = root / "state.txt"

            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--cwd", str(cwd), "--user-quotes", str(quotes), "--out", str(output)],
                text=True, capture_output=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            state = output.read_text(encoding="utf-8")
            self.assertLess(state.index("ユーザー発言の引用"), state.index("依頼の原文"))
            self.assertLess(state.index("依頼の原文"), state.index("事実"))
            self.assertIn(".git: あり", state)
            self.assertIn("マニフェスト: pyproject.toml", state)
            self.assertIn("既存テスト: あり", state)
            self.assertIn('「この範囲だけ」', state)

    def test_queries_github_reference_through_gh(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            quotes = root / "quotes.txt"
            quotes.write_text("引用", encoding="utf-8")
            executable = root / "gh"
            executable.write_text("#!/bin/sh\nprintf '%s\\n' \"$*\" > \"$GH_ARGS_FILE\"\nprintf '{\"number\":42}'\n", encoding="utf-8")
            executable.chmod(0o755)
            args_file = root / "gh-args.txt"
            environment = os.environ.copy()
            environment["PATH"] = str(root) + os.pathsep + environment["PATH"]
            environment["GH_ARGS_FILE"] = str(args_file)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--user-quotes", str(quotes), "--ref", "owner/repo#42", "--out", str(root / "state.txt")],
                text=True, capture_output=True, env=environment,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("repos/owner/repo/issues/42", args_file.read_text())
            self.assertIn("issue / PR 種別: issue", (root / "state.txt").read_text())

    def test_stops_when_state_exceeds_limit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            quotes = root / "quotes.txt"
            quotes.write_text("x" * 30001, encoding="utf-8")
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--user-quotes", str(quotes), "--out", str(root / "state.txt")],
                text=True, capture_output=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertIn("30000", result.stderr)
            self.assertFalse((root / "state.txt").exists())
