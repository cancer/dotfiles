import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DECIDE = ROOT / "decide.py"


def question(question_type="noul", **extra):
    value = {"type": question_type, "instructions": "判定してください"}
    if question_type == "choice":
        value["criteria"] = {
            "stronger_or_equal": "同等以上",
            "weaker": "弱い",
            "no_counterpart": "該当なし",
        }
    value.update(extra)
    return value


def noul_rule(condition="noul_below", threshold=0.5):
    return {
        "fail_if": {condition: threshold},
        "axis": "instruction",
        "summary": "要件を満たしていない",
        "files": ["src/example.py"],
    }


def choice_rule(values=None):
    return {
        "fail_if": {"choice_in": values or ["weaker", "no_counterpart"]},
        "axis": "verification",
        "summary": "検証が弱い",
        "files": ["test/example.py"],
    }


class DecideTests(unittest.TestCase):
    def run_decide(self, questions, rules, answers, *, raw_questions=None):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inputs = {
                "questions": raw_questions if raw_questions is not None else questions,
                "rules": rules,
                "answers": answers,
            }
            paths = {}
            for name, value in inputs.items():
                path = root / f"{name}.json"
                path.write_text(
                    value if isinstance(value, str) else json.dumps(value),
                    encoding="utf-8",
                )
                paths[name] = path
            output = root / "verdict.json"
            process = subprocess.run(
                [
                    sys.executable,
                    str(DECIDE),
                    "--questions", str(paths["questions"]),
                    "--rules", str(paths["rules"]),
                    "--answers", str(paths["answers"]),
                    "--out", str(output),
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            result = json.loads(output.read_text(encoding="utf-8")) if output.exists() else None
            return process, result

    def assert_invalid(self, questions, rules, answers):
        process, result = self.run_decide(questions, rules, answers)
        self.assertEqual(process.returncode, 2, process.stderr)
        self.assertEqual(result["verdict"], "INVALID")
        self.assertTrue(result["invalid"])
        return result["invalid"]

    def test_passes_when_no_question_meets_a_fail_condition(self):
        questions = {"first": question(), "second": question("choice")}
        rules = {"first": noul_rule(), "second": choice_rule()}
        answers = {
            "first": {"type": "noul", "noul": 0.8},
            "second": {"type": "choice", "choice": "stronger_or_equal"},
        }

        process, result = self.run_decide(questions, rules, answers)

        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result, {
            "verdict": "PASS",
            "reasons": [],
            "questions": 2,
            "failed_questions": 0,
            "invalid": [],
        })

    def test_fails_in_question_order_and_returns_compact_answers(self):
        questions = {"second": question("choice"), "first": question()}
        rules = {"first": noul_rule(), "second": choice_rule()}
        answers = {
            "first": {"type": "noul", "noul": 0.1, "extra": "omit"},
            "second": {"type": "choice", "choice": "weaker", "confidence": 0.8},
        }

        process, result = self.run_decide(questions, rules, answers)

        self.assertEqual(process.returncode, 0, process.stderr)
        self.assertEqual(result["verdict"], "FAIL")
        self.assertEqual(result["failed_questions"], 2)
        self.assertEqual([reason["question"] for reason in result["reasons"]], ["second", "first"])
        self.assertEqual(result["reasons"][0]["answer"], {"type": "choice", "choice": "weaker"})
        self.assertEqual(result["reasons"][1]["answer"], {"type": "noul", "noul": 0.1})

    def test_noul_below_uses_strict_boundary(self):
        questions = {"q": question()}
        rules = {"q": noul_rule("noul_below", 0.5)}
        for value, expected in ((0.499, "FAIL"), (0.5, "PASS")):
            with self.subTest(value=value):
                process, result = self.run_decide(
                    questions, rules, {"q": {"type": "noul", "noul": value}}
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(result["verdict"], expected)

    def test_noul_at_least_uses_inclusive_boundary(self):
        questions = {"q": question()}
        rules = {"q": noul_rule("noul_at_least", 0.5)}
        for value, expected in ((0.499, "PASS"), (0.5, "FAIL")):
            with self.subTest(value=value):
                process, result = self.run_decide(
                    questions, rules, {"q": {"type": "noul", "noul": value}}
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(result["verdict"], expected)

    def test_choice_in_matches_only_listed_choices(self):
        questions = {"q": question("choice")}
        rules = {"q": choice_rule(["weaker"])}
        for value, expected in (("weaker", "FAIL"), ("stronger_or_equal", "PASS")):
            with self.subTest(value=value):
                process, result = self.run_decide(
                    questions, rules, {"q": {"type": "choice", "choice": value}}
                )
                self.assertEqual(process.returncode, 0, process.stderr)
                self.assertEqual(result["verdict"], expected)

    def test_invalid_when_rule_is_missing(self):
        invalid = self.assert_invalid(
            {"q": question()}, {}, {"q": {"type": "noul", "noul": 0.9}}
        )
        self.assertIn("q", [item["question"] for item in invalid])

    def test_invalid_when_rule_has_no_question(self):
        self.assert_invalid(
            {}, {"orphan": noul_rule()}, {}
        )

    def test_invalid_when_answer_is_missing(self):
        self.assert_invalid({"q": question()}, {"q": noul_rule()}, {})

    def test_invalid_when_answer_type_does_not_match_question(self):
        self.assert_invalid(
            {"q": question()}, {"q": noul_rule()},
            {"q": {"type": "choice", "choice": "weaker"}},
        )

    def test_invalid_when_fail_if_is_empty_or_has_multiple_keys(self):
        for fail_if in ({}, {"noul_below": 0.5, "noul_at_least": 0.6}):
            with self.subTest(fail_if=fail_if):
                rules = {"q": noul_rule()}
                rules["q"]["fail_if"] = fail_if
                self.assert_invalid(
                    {"q": question()}, rules, {"q": {"type": "noul", "noul": 0.9}}
                )

    def test_invalid_when_fail_if_has_unknown_key(self):
        rules = {"q": noul_rule()}
        rules["q"]["fail_if"] = {"unknown": 0.5}
        self.assert_invalid({"q": question()}, rules, {"q": {"type": "noul", "noul": 0.9}})

    def test_invalid_when_noul_threshold_is_outside_zero_to_one(self):
        for threshold in (-0.1, 1.1):
            with self.subTest(threshold=threshold):
                self.assert_invalid(
                    {"q": question()}, {"q": noul_rule(threshold=threshold)},
                    {"q": {"type": "noul", "noul": 0.9}},
                )

    def test_invalid_when_choice_rule_names_unknown_criterion(self):
        self.assert_invalid(
            {"q": question("choice")}, {"q": choice_rule(["unknown"])},
            {"q": {"type": "choice", "choice": "weaker"}},
        )

    def test_invalid_when_rule_form_does_not_match_question_type(self):
        self.assert_invalid(
            {"q": question()}, {"q": choice_rule()},
            {"q": {"type": "noul", "noul": 0.9}},
        )
        self.assert_invalid(
            {"q": question("choice")}, {"q": noul_rule()},
            {"q": {"type": "choice", "choice": "weaker"}},
        )

    def test_score_question_is_invalid(self):
        self.assert_invalid(
            {"q": question("score")}, {"q": noul_rule()},
            {"q": {"type": "score", "score": 1}},
        )

    def test_malformed_json_returns_one(self):
        process, result = self.run_decide(
            {}, {}, {}, raw_questions='{"broken": ',
        )
        self.assertEqual(process.returncode, 1)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
