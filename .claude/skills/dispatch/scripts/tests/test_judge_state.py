import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "judge_state.py"


class JudgeStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.state = self.root / "state.txt"
        self.state.write_text("ユーザー発言の引用\n依頼の原文\n事実\n", encoding="utf-8")
        self.stub = self.root / "judge_stub.py"
        self.stub.write_text(
            "import json, os, pathlib, sys\n"
            "args = dict(zip(sys.argv[1::2], sys.argv[2::2]))\n"
            "questions = json.loads(pathlib.Path(args['--questions-file']).read_text())\n"
            "answers = json.loads(os.environ['DIRECTOR_ANSWERS'])\n"
            "print(json.dumps({key: answers[key] for key in questions}))\n",
            encoding="utf-8",
        )
        self.output = self.root / "result.json"
        self.log = self.root / "judge.jsonl"

    def tearDown(self):
        self.temporary.cleanup()

    def run_judge(self, answers, kind=None, interpretation=None, answered=None):
        environment = os.environ.copy()
        environment["DIRECTOR_JUDGE_SCRIPT"] = str(self.stub)
        environment["DIRECTOR_ANSWERS"] = json.dumps(answers)
        command = [sys.executable, str(SCRIPT), "--state-file", str(self.state), "--catalog", str(ROOT / "catalog.json"),
                   "--thresholds", str(ROOT / "thresholds.json"), "--out", str(self.output), "--log", str(self.log)]
        if kind:
            command.extend(["--kind", kind])
        if interpretation is not None:
            path = self.root / "interpretation.json"
            path.write_text(json.dumps({"items": interpretation}, ensure_ascii=False), encoding="utf-8")
            command.extend(["--interpretation", str(path)])
        if answered is not None:
            path = self.root / "answered.txt"
            path.write_text("\n".join(answered), encoding="utf-8")
            command.extend(["--answered-file", str(path)])
        return subprocess.run(command, text=True, capture_output=True, env=environment)

    def implement_answers(self, **overrides):
        catalog = json.loads((ROOT / "catalog.json").read_text())
        answers = {}
        for item_id, item in catalog["items"].items():
            if item_id.startswith("implement."):
                answers.update({question_id: {"type": "noul", "noul": 0.9} for question_id in item["questions"]})
                answers.update({f"{item_id}.{name}": {"type": "noul", "noul": 0.9} for name in catalog["item_questions"]})
        for common in catalog["common"].values():
            answers.update({question_id: {"type": "noul", "noul": 0.1} for question_id in common["questions"]})
        answers.update({key: {"type": "noul", "noul": value} for key, value in overrides.items()})
        return answers

    def test_none_returns_kind_null_with_message_without_second_query(self):
        answers = {"kind": {"type": "choice", "choice": "none", "probabilities": {"none": 0.8, "implement": 0.1, "know": 0.05, "write": 0.05}}}
        result = self.run_judge(answers)
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text())
        self.assertIsNone(response["kind"])
        self.assertFalse(response["ready"])
        self.assertIn("何を受け取りたいですか", response["message"])

    def test_kind_without_interpretation_stops_after_layer_one(self):
        answers = {"kind": {"type": "choice", "choice": "implement", "probabilities": {"implement": 0.9, "know": 0.05, "write": 0.03, "none": 0.02}}}
        result = self.run_judge(answers)
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text())
        self.assertEqual(response["kind"], "implement")
        self.assertNotIn("items", response)

    def test_all_questions_pass_makes_ready(self):
        result = self.run_judge(self.implement_answers(), "implement", {})
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text())
        self.assertTrue(response["ready"])
        self.assertEqual(response["message"], "")

    def test_failed_question_is_shown_with_value_default_and_ask(self):
        interpretation = {"implement.completion": {"value": "整理の完了まで", "source": "user"}}
        result = self.run_judge(self.implement_answers(**{"implement.completion.end_state": 0.21}), "implement", interpretation)
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text())
        self.assertFalse(response["ready"])
        self.assertEqual(response["items"]["implement.completion"]["status"], "ask")
        message = response["message"]
        self.assertIn("implement.completion で止まっています", message)
        self.assertIn("「整理の完了まで」", message)
        self.assertIn("範囲語", message)
        self.assertNotIn("確認手段", message)
        self.assertIn("既定値: 既存のテストと lint が通る", message)
        self.assertIn("→ 何ができていれば完了ですか", message)

    def test_answered_item_does_not_block(self):
        result = self.run_judge(self.implement_answers(**{"implement.completion.end_state": 0.5}), "implement", {}, ["implement.completion"])
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text())
        self.assertEqual(response["items"]["implement.completion"]["status"], "answered")
        self.assertTrue(response["ready"])

    def test_unsupported_content_names_the_item(self):
        interpretation = {"implement.completion": {"value": "追加の 1 件が通る", "source": "推測"}}
        result = self.run_judge(self.implement_answers(**{"implement.completion.supported": 0.4}), "implement", interpretation)
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text())
        self.assertEqual(response["items"]["implement.completion"]["status"], "ask")
        self.assertIn("implement.completion で止まっています", response["message"])
        self.assertIn("解釈の implement.completion に書かれた内容は", response["message"])

    def test_contradiction_blocks_and_is_shown(self):
        result = self.run_judge(self.implement_answers(**{"common.contradiction.conflict": 0.8}), "implement", {})
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text())
        self.assertFalse(response["ready"])
        self.assertIn("common.contradiction で止まっています", response["message"])

    def test_judge_failure_is_reported_without_output(self):
        environment = os.environ.copy()
        environment["DIRECTOR_JUDGE_SCRIPT"] = str(self.root / "missing.py")
        interpretation = self.root / "interpretation.json"
        interpretation.write_text('{"items": {}}', encoding="utf-8")
        result = subprocess.run([sys.executable, str(SCRIPT), "--state-file", str(self.state), "--catalog", str(ROOT / "catalog.json"),
                                 "--thresholds", str(ROOT / "thresholds.json"), "--kind", "implement", "--interpretation", str(interpretation), "--out", str(self.output), "--log", str(self.log)],
                                text=True, capture_output=True, env=environment)
        self.assertEqual(result.returncode, 1)
        self.assertIn("judge_state.py:", result.stderr)
        self.assertFalse(self.output.exists())
