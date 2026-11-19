import contextlib
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1]
FIXTURES = SCRIPT_DIR / "fixtures"
REVIEW_SCRIPT = SCRIPT_DIR / "review.py"
RULE_IDS = (
    "J-scope",
    "J-unrelated",
    "J-industry",
    "J-unagreed",
    "J-hypothesis",
    "J-heading",
    "J-unknown-names",
    "reader.entrust",
    "reader.understand_problem",
    "reader.why_us",
    "reader.next_step",
)


class ReviewCliTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.stub = self.root / "judge_stub.py"
        self.stub.write_text(
            "import json, os, pathlib, sys\n"
            "args = dict(zip(sys.argv[1::2], sys.argv[2::2]))\n"
            "if os.environ.get('PROPOSAL_TEST_FAILURE'):\n"
            "    print(os.environ['PROPOSAL_TEST_FAILURE'], file=sys.stderr)\n"
            "    raise SystemExit(7)\n"
            "if 'PROPOSAL_TEST_RAW' in os.environ:\n"
            "    print(os.environ['PROPOSAL_TEST_RAW'])\n"
            "    raise SystemExit(0)\n"
            "questions = json.loads(pathlib.Path(args['--questions-file']).read_text(encoding='utf-8'))\n"
            "answers = json.loads(os.environ['PROPOSAL_TEST_ANSWERS'])\n"
            "print(json.dumps({key: answers[key] for key in questions}, ensure_ascii=False))\n",
            encoding="utf-8",
        )
        self.output = self.root / "review.json"

    def tearDown(self):
        self.temporary.cleanup()

    def answers(self, probability=0.8):
        return {key: {"type": "noul", "noul": probability} for key in RULE_IDS}

    def run_cli(self, answers, failure=None, *, target="outline", workdir=None, raw=None, round_number="3"):
        environment = os.environ.copy()
        environment["PROPOSAL_JUDGE_SCRIPT"] = str(self.stub)
        environment["PROPOSAL_TEST_ANSWERS"] = json.dumps(answers)
        if failure is not None:
            environment["PROPOSAL_TEST_FAILURE"] = failure
        if raw is not None:
            environment["PROPOSAL_TEST_RAW"] = raw
        target_workdir = FIXTURES / "clean" if workdir is None else workdir
        self.output.unlink(missing_ok=True)
        return subprocess.run(
            [
                sys.executable,
                str(REVIEW_SCRIPT),
                "--workdir",
                str(target_workdir),
                "--target",
                target,
                "--round",
                round_number,
                "--out",
                str(self.output),
            ],
            text=True,
            capture_output=True,
            env=environment,
        )

    def test_cli_writes_c5_json_and_succeeds_when_findings_exist(self):
        answers = self.answers(0.8)
        answers["J-scope"]["noul"] = 0.69

        result = self.run_cli(answers)

        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(response["target"], "outline")
        self.assertEqual(response["round"], 3)
        self.assertEqual(response["findings"][0]["id"], "J-scope@all")
        self.assertFalse(response["passed"])

    def test_cli_accepts_deck_target(self):
        result = self.run_cli(self.answers(0.8), target="deck", workdir=FIXTURES / "deck_clean")

        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(response["target"], "deck")
        self.assertEqual(response["findings"], [])
        self.assertTrue(response["passed"])

    def test_passed_requires_no_findings_and_entrust_at_least_threshold(self):
        passing = self.run_cli(self.answers(0.7))
        self.assertEqual(passing.returncode, 0, passing.stderr)
        self.assertTrue(json.loads(self.output.read_text(encoding="utf-8"))["passed"])

        low_reader = self.answers(0.8)
        low_reader["reader.entrust"]["noul"] = 0.69
        rejected_reader = self.run_cli(low_reader)
        self.assertEqual(rejected_reader.returncode, 0, rejected_reader.stderr)
        low_reader_result = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertFalse(low_reader_result["passed"])
        self.assertEqual(low_reader_result["findings"][0]["id"], "reader.entrust@all")

        has_finding = self.answers(0.8)
        has_finding["J-heading"]["noul"] = 0.69
        rejected_findings = self.run_cli(has_finding)
        self.assertEqual(rejected_findings.returncode, 0, rejected_findings.stderr)
        finding_result = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertFalse(finding_result["passed"])
        self.assertGreaterEqual(finding_result["reader"]["score"], 0.7)

    def test_judge_failure_returns_nonzero_and_explains_reason(self):
        result = self.run_cli(self.answers(), failure="stub judge failed")

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("stub judge failed", result.stderr)
        self.assertFalse(self.output.exists())

    def test_script_findings_fail_even_when_jev_passes_everything(self):
        cases = {
            "violations": ("outline", FIXTURES / "violations"),
            "deck_drift": ("deck", FIXTURES / "deck_drift"),
        }
        for name, (target, workdir) in cases.items():
            with self.subTest(case=name):
                result = self.run_cli(self.answers(0.9), target=target, workdir=workdir)

                self.assertEqual(result.returncode, 0, result.stderr)
                response = json.loads(self.output.read_text(encoding="utf-8"))
                self.assertGreaterEqual(response["reader"]["score"], 0.7)
                self.assertTrue(response["findings"])
                self.assertEqual({item["source"] for item in response["findings"]}, {"script"})
                self.assertFalse(response["passed"])

    def test_output_matches_c5_shape(self):
        answers = self.answers(0.9)
        answers["reader.entrust"]["noul"] = 0.81
        answers["reader.understand_problem"]["noul"] = 0.72
        answers["reader.why_us"]["noul"] = 0.73
        answers["reader.next_step"]["noul"] = 0.74
        answers["J-scope"]["noul"] = 0.2

        result = self.run_cli(answers, workdir=FIXTURES / "violations")

        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text(encoding="utf-8"))
        self.assertEqual(set(response), {"target", "round", "reader", "findings", "passed"})
        self.assertEqual(set(response["reader"]), {"score", "diagnostics"})
        self.assertEqual(response["reader"]["score"], 0.81)
        self.assertEqual(
            response["reader"]["diagnostics"],
            {"reader.understand_problem": 0.72, "reader.why_us": 0.73, "reader.next_step": 0.74},
        )
        self.assertEqual({item["source"] for item in response["findings"]}, {"script", "jev"})
        for finding in response["findings"]:
            with self.subTest(finding=finding["id"]):
                self.assertEqual(set(finding), {"id", "rule", "slide", "category", "message", "source"})
                self.assertIn(finding["source"], {"script", "jev"})
                self.assertEqual(finding["category"], "auto")
                self.assertIsInstance(finding["message"], str)
                self.assertTrue(finding["message"])
                if finding["slide"] is None:
                    self.assertEqual(finding["id"], f"{finding['rule']}@all")
                else:
                    self.assertRegex(finding["slide"], r"^S\d+$")
                    self.assertEqual(finding["id"], f"{finding['rule']}@{finding['slide']}")

    def assert_failed_without_output(self, result, reason_pattern):
        self.assertNotEqual(result.returncode, 0)
        self.assertRegex(result.stderr, reason_pattern)
        self.assertFalse(self.output.exists())

    def test_invalid_judge_answers_fail_without_output(self):
        def with_scope(value):
            answers = self.answers(0.8)
            answers["J-scope"] = value
            return json.dumps(answers)

        cases = {
            "not_json": ("not json", "JSON"),
            "not_object": ("[]", "JSON object"),
            "missing_noul": (with_scope({"type": "noul"}), "J-scope.noul"),
            "string_noul": (with_scope({"type": "noul", "noul": "0.8"}), "数値"),
            "bool_noul": (with_scope({"type": "noul", "noul": True}), "数値"),
            "above_range": (with_scope({"type": "noul", "noul": 1.2}), "範囲外"),
            "below_range": (with_scope({"type": "noul", "noul": -0.1}), "範囲外"),
            "nan": (with_scope({"type": "noul", "noul": float("nan")}), "範囲外"),
        }
        for name, (raw, reason) in cases.items():
            with self.subTest(case=name):
                self.assert_failed_without_output(self.run_cli(self.answers(), raw=raw), reason)

    def test_round_below_one_fails_without_output(self):
        self.assert_failed_without_output(self.run_cli(self.answers(), round_number="0"), "round")

    def test_missing_input_files_fail_without_output(self):
        cases = {
            "outline.md": ("outline", FIXTURES / "clean"),
            "request.md": ("outline", FIXTURES / "clean"),
            "industry-notes.md": ("outline", FIXTURES / "clean"),
            "deck/project/deck.json": ("deck", FIXTURES / "deck_clean"),
        }
        for missing, (target, source) in cases.items():
            with self.subTest(missing=missing):
                workdir = self.root / f"workdir-{target}-{Path(missing).name}"
                shutil.copytree(source, workdir)
                (workdir / missing).unlink()

                result = self.run_cli(self.answers(), target=target, workdir=workdir)

                self.assert_failed_without_output(result, re.escape(Path(missing).name))

    def test_industry_notes_without_confirmed_facts_fail_without_output(self):
        # C6: 事実の裏付けが無いまま判定させず、入力の失敗として止める
        workdir = self.root / "workdir-no-facts"
        shutil.copytree(FIXTURES / "clean", workdir)
        (workdir / "industry-notes.md").write_text(
            "# 業界理解メモ\n\n## 不明点\n- 現場で使っている記録方法。\n", encoding="utf-8"
        )

        result = self.run_cli(self.answers(), workdir=workdir)

        self.assert_failed_without_output(result, "確認済み事実")

    def test_invalid_thresholds_fail_without_output(self):
        sys.path.insert(0, str(SCRIPT_DIR))
        import judge_review
        import review

        cases = {
            "missing_yes": {"no": 0.3},
            "string_yes": {"yes": "0.7"},
            "bool_yes": {"yes": True},
            "above_range": {"yes": 1.5},
            "not_object": [0.7],
        }
        for name, thresholds in cases.items():
            with self.subTest(case=name):
                self.output.unlink(missing_ok=True)
                thresholds_path = self.root / f"thresholds-{name}.json"
                thresholds_path.write_text(json.dumps(thresholds), encoding="utf-8")
                stderr = io.StringIO()
                environment = {
                    "PROPOSAL_JUDGE_SCRIPT": str(self.stub),
                    "PROPOSAL_TEST_ANSWERS": json.dumps(self.answers()),
                }
                with patch.object(judge_review, "THRESHOLDS_PATH", thresholds_path), \
                        patch.dict(os.environ, environment), contextlib.redirect_stderr(stderr):
                    code = review.main([
                        "--workdir", str(FIXTURES / "clean"), "--target", "outline",
                        "--round", "1", "--out", str(self.output),
                    ])

                self.assertNotEqual(code, 0)
                self.assertIn("thresholds", stderr.getvalue())
                self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
