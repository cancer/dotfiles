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

    def run_judge(self, answers, kind=None):
        environment = os.environ.copy()
        environment["DIRECTOR_JUDGE_SCRIPT"] = str(self.stub)
        environment["DIRECTOR_ANSWERS"] = json.dumps(answers)
        command = [sys.executable, str(SCRIPT), "--state-file", str(self.state), "--catalog", str(ROOT / "catalog.json"),
                   "--thresholds", str(ROOT / "thresholds.json"), "--out", str(self.output), "--log", str(self.log)]
        if kind:
            command.extend(["--kind", kind])
        return subprocess.run(command, text=True, capture_output=True, env=environment)

    def test_none_returns_kind_probabilities_and_ask_without_second_query(self):
        answers = {"kind": {"type": "choice", "choice": "none", "probabilities": {"none": 0.8, "implement": 0.1, "know": 0.05, "write": 0.05}}}
        result = self.run_judge(answers)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.output.read_text()), {"kind": None, "kind_probabilities": answers["kind"]["probabilities"], "ask": "何を受け取りたいか"})

    def test_kind_override_uses_empty_probabilities_and_requires_all_items_and_no_contradiction(self):
        answers = {"implement.target": {"type": "noul", "noul": 0.7}, "implement.completion": {"type": "noul", "noul": 0.9},
                   "implement.out_of_scope": {"type": "noul", "noul": 0.9}, "implement.constraints": {"type": "noul", "noul": 0.9},
                   "implement.deliverable": {"type": "noul", "noul": 0.9}, "implement.rejected_policy": {"type": "noul", "noul": 0.9},
                   "common.contradiction": {"type": "noul", "noul": 0.1}}
        result = self.run_judge(answers, "implement")
        self.assertEqual(result.returncode, 0, result.stderr)
        response = json.loads(self.output.read_text())
        self.assertEqual(response["kind_probabilities"], {})
        self.assertTrue(response["ready"])
        self.assertEqual(response["items"]["implement.target"]["verdict"], "yes")

    def test_judge_failure_is_reported_without_output(self):
        environment = os.environ.copy()
        environment["DIRECTOR_JUDGE_SCRIPT"] = str(self.root / "missing.py")
        result = subprocess.run([sys.executable, str(SCRIPT), "--state-file", str(self.state), "--catalog", str(ROOT / "catalog.json"),
                                 "--thresholds", str(ROOT / "thresholds.json"), "--kind", "implement", "--out", str(self.output), "--log", str(self.log)],
                                text=True, capture_output=True, env=environment)
        self.assertEqual(result.returncode, 1)
        self.assertIn("judge_state.py:", result.stderr)
        self.assertFalse(self.output.exists())
