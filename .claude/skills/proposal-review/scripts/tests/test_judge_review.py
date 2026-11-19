import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1]
FIXTURES = SCRIPT_DIR / "fixtures"
sys.path.insert(0, str(SCRIPT_DIR))

import judge_review  # noqa: E402


RULE_IDS = (
    "J-scope",
    "J-unrelated",
    "J-industry",
    "J-unagreed",
    "J-hypothesis",
    "J-heading",
    "J-unknown-names",
)
READER_IDS = (
    "reader.entrust",
    "reader.understand_problem",
    "reader.why_us",
    "reader.next_step",
)


class JudgeReviewTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.stub = self.root / "judge_stub.py"
        self.stub.write_text(
            "import json, os, pathlib, sys\n"
            "args = dict(zip(sys.argv[1::2], sys.argv[2::2]))\n"
            "state = pathlib.Path(args['--state-file']).read_text(encoding='utf-8')\n"
            "capture = os.environ.get('PROPOSAL_CAPTURE_STATE')\n"
            "if capture: pathlib.Path(capture).write_text(state, encoding='utf-8')\n"
            "questions = json.loads(pathlib.Path(args['--questions-file']).read_text(encoding='utf-8'))\n"
            "answers = json.loads(os.environ['PROPOSAL_TEST_ANSWERS'])\n"
            "print(json.dumps({key: answers[key] for key in questions}, ensure_ascii=False))\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary.cleanup()

    def answers(self, probability=0.8):
        return {
            key: {"type": "noul", "noul": probability}
            for key in (*RULE_IDS, *READER_IDS)
        }

    def run_review(self, answers, capture_state=None, workdir=FIXTURES / "clean", target="outline"):
        environment = {
            "PROPOSAL_JUDGE_SCRIPT": str(self.stub),
            "PROPOSAL_TEST_ANSWERS": json.dumps(answers),
        }
        if capture_state is not None:
            environment["PROPOSAL_CAPTURE_STATE"] = str(capture_state)
        with patch.dict(os.environ, environment):
            return judge_review.review(workdir, target)

    def test_j_rule_probabilities_at_or_above_threshold_pass(self):
        result = self.run_review(self.answers(0.7))

        self.assertEqual(result["findings"], [])

    def test_each_low_j_probability_creates_an_all_finding(self):
        answers = self.answers(0.8)
        for rule in RULE_IDS:
            answers[rule]["noul"] = 0.69
        result = self.run_review(answers)
        finding_ids = {item["id"] for item in result["findings"]}

        self.assertEqual(finding_ids, {f"{rule}@all" for rule in RULE_IDS})

    def test_low_entrust_creates_finding_when_diagnostics_pass(self):
        answers = self.answers(0.8)
        answers["reader.entrust"]["noul"] = 0.69

        result = self.run_review(answers)

        self.assertEqual([item["id"] for item in result["findings"]], ["reader.entrust@all"])

    def test_low_diagnostic_creates_its_own_finding(self):
        answers = self.answers(0.8)
        answers["reader.why_us"]["noul"] = 0.69

        result = self.run_review(answers)

        self.assertEqual([item["id"] for item in result["findings"]], ["reader.why_us@all"])

    def test_judge_receives_request_and_confirmed_facts_but_not_unknowns(self):
        capture_state = self.root / "received-state.txt"
        self.run_review(self.answers(), capture_state)
        state = capture_state.read_text(encoding="utf-8")

        self.assertIn("REQUEST_BODY_MARKER", state)
        self.assertIn("CONFIRMED_FACT_MARKER", state)
        self.assertNotIn("UNKNOWN_MARKER", state)

    def capture(self, workdir, target):
        capture_state = self.root / "received-state.txt"
        self.run_review(self.answers(), capture_state, workdir, target)
        return capture_state.read_text(encoding="utf-8")

    def test_state_keeps_only_confirmed_facts_section_of_industry_notes(self):
        # C2: industry-notes.md からは「確認済み事実」節だけを渡す
        for workdir, target in ((FIXTURES / "clean", "outline"), (FIXTURES / "deck_clean", "deck")):
            with self.subTest(target=target):
                state = self.capture(workdir, target)

                self.assertIn("CONFIRMED_FACT_MARKER", state)
                self.assertNotIn("UNKNOWN_MARKER", state)
                self.assertNotIn("FLOW_MARKER", state)
                self.assertNotIn("TERM_MARKER", state)

    def notes_workdir(self, notes):
        workdir = self.root / "notes_case"
        shutil.copytree(FIXTURES / "clean", workdir)
        (workdir / "industry-notes.md").write_text(notes, encoding="utf-8")
        return workdir

    def test_confirmed_facts_section_keeps_subsections_and_stops_at_next_section(self):
        notes = (
            "# 業界理解メモ\n\n"
            "## 確認済み事実\n- CONFIRMED_FACT_MARKER\n"
            "### 現場\n- SUBSECTION_MARKER\n\n"
            "## 不明点\n- UNKNOWN_MARKER\n"
        )
        state = self.capture(self.notes_workdir(notes), "outline")

        self.assertIn("SUBSECTION_MARKER", state)
        self.assertNotIn("UNKNOWN_MARKER", state)

    def test_confirmed_facts_as_last_section_reads_to_end_of_file(self):
        notes = "# 業界理解メモ\n\n## 不明点\n- UNKNOWN_MARKER\n\n## 確認済み事実\n- CONFIRMED_FACT_MARKER\n- LAST_LINE_MARKER"
        state = self.capture(self.notes_workdir(notes), "outline")

        self.assertIn("LAST_LINE_MARKER", state)
        self.assertNotIn("UNKNOWN_MARKER", state)

    def test_deck_state_has_visible_text_without_notes_fixed_elements_or_tags(self):
        state = self.capture(FIXTURES / "deck_clean", "deck")
        target_section = state.split("## target: deck\n", 1)[1]

        self.assertIn("s1: 物流現場の状況を整理します 入出庫の流れを確認する 日々の記録方法を確認する", target_section)
        self.assertIn("s7: まず対象業務を一緒に確認します", target_section)
        self.assertNotIn("OUTSIDE_ASIDE_MARKER", state)
        self.assertNotIn("FIXED_ELEMENT_MARKER", state)
        self.assertNotRegex(target_section, r"</?[A-Za-z][^>]*>")


if __name__ == "__main__":
    unittest.main()
