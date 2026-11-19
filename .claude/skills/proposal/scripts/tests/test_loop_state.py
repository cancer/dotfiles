import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "loop_state.py"


class LoopStateTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.review_path = self.root / "review.json"
        self.history_path = self.root / "loop-history.json"

    def tearDown(self):
        self.temporary.cleanup()

    def run_review(self, review):
        self.review_path.write_text(json.dumps(review), encoding="utf-8")
        return subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--review",
                str(self.review_path),
                "--history",
                str(self.history_path),
            ],
            capture_output=True,
            text=True,
        )

    @staticmethod
    def make_review(target="outline", findings=None, passed=False, round_number=1):
        return {
            "target": target,
            "round": round_number,
            "reader": {
                "score": 0.8 if passed else 0.6,
                "diagnostics": {
                    "reader.understand_problem": 0.6,
                    "reader.why_us": 0.6,
                    "reader.next_step": 0.6,
                },
            },
            "findings": findings or [],
            "passed": passed,
        }

    @staticmethod
    def finding(identifier, category="auto"):
        rule, _, slide = identifier.partition("@")
        return {
            "id": identifier,
            "rule": rule,
            "slide": slide if slide.startswith("S") else None,
            "category": category,
            "message": "修正してください。",
            "source": "script",
        }

    def read_history(self):
        return json.loads(self.history_path.read_text(encoding="utf-8"))

    def test_passed_review_returns_done_and_appends_empty_id_column(self):
        result = self.run_review(self.make_review(passed=True))

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(
            output,
            {"next": "done", "findings": [], "stalled_ids": []},
        )
        self.assertEqual(self.read_history(), {"outline": [{"round": 1, "ids": []}]})

    def test_ask_finding_returns_ask(self):
        finding = self.finding("J-unagreed@S2", category="ask")
        result = self.run_review(self.make_review(findings=[finding]))

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["next"], "ask")
        self.assertEqual(output["findings"], [finding])
        self.assertEqual(output["stalled_ids"], [])
        self.assertEqual(
            self.read_history(), {"outline": [{"round": 1, "ids": ["J-unagreed@S2"]}]}
        )

    def test_same_finding_stalls_only_on_third_consecutive_review(self):
        finding = self.finding("J-scope@S3")
        first = self.run_review(self.make_review(findings=[finding], round_number=1))
        second = self.run_review(self.make_review(findings=[finding], round_number=2))
        third = self.run_review(self.make_review(findings=[finding], round_number=3))

        self.assertEqual([json.loads(run.stdout)["next"] for run in (first, second)], ["fix", "fix"])
        self.assertEqual(third.returncode, 0, third.stderr)
        self.assertEqual(
            json.loads(third.stdout),
            {"next": "stalled", "findings": [finding], "stalled_ids": ["J-scope@S3"]},
        )
        self.assertEqual(
            self.read_history(),
            {
                "outline": [
                    {"round": 1, "ids": ["J-scope@S3"]},
                    {"round": 2, "ids": ["J-scope@S3"]},
                    {"round": 3, "ids": ["J-scope@S3"]},
                ]
            },
        )

    def test_missing_finding_in_between_resets_consecutive_count(self):
        first = self.finding("J-scope@S3")
        second = self.finding("J-heading@S4")

        self.run_review(self.make_review(findings=[first], round_number=1))
        self.run_review(self.make_review(findings=[second], round_number=2))
        final = self.run_review(self.make_review(findings=[first], round_number=3))

        self.assertEqual(final.returncode, 0, final.stderr)
        self.assertEqual(json.loads(final.stdout)["next"], "fix")
        self.assertEqual(json.loads(final.stdout)["stalled_ids"], [])

    def test_history_is_separate_for_outline_and_deck(self):
        finding = self.finding("R-format@S1")

        self.run_review(self.make_review(target="outline", findings=[finding], round_number=1))
        self.run_review(self.make_review(target="outline", findings=[finding], round_number=2))
        deck_result = self.run_review(
            self.make_review(target="deck", findings=[finding], round_number=1)
        )

        self.assertEqual(deck_result.returncode, 0, deck_result.stderr)
        self.assertEqual(json.loads(deck_result.stdout)["next"], "fix")
        self.assertEqual(
            self.read_history(),
            {
                "outline": [
                    {"round": 1, "ids": ["R-format@S1"]},
                    {"round": 2, "ids": ["R-format@S1"]},
                ],
                "deck": [{"round": 1, "ids": ["R-format@S1"]}],
            },
        )

    def test_passed_review_returns_done_even_with_ask_and_stalled_findings(self):
        finding = self.finding("J-scope@S3", category="ask")
        self.run_review(self.make_review(findings=[finding], round_number=1))
        self.run_review(self.make_review(findings=[finding], round_number=2))
        result = self.run_review(
            self.make_review(findings=[finding], passed=True, round_number=3)
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["next"], "done")
        self.assertEqual(output["stalled_ids"], ["J-scope@S3"])

    def test_ask_takes_priority_over_stalled(self):
        stalled = self.finding("J-scope@S3")
        asked = self.finding("J-unagreed@S2", category="ask")
        self.run_review(self.make_review(findings=[stalled], round_number=1))
        self.run_review(self.make_review(findings=[stalled], round_number=2))
        result = self.run_review(
            self.make_review(findings=[stalled, asked], round_number=3)
        )

        self.assertEqual(result.returncode, 0, result.stderr)
        output = json.loads(result.stdout)
        self.assertEqual(output["next"], "ask")
        self.assertEqual(output["stalled_ids"], ["J-scope@S3"])

    def test_rerunning_same_round_replaces_history_entry(self):
        finding = self.finding("J-scope@S3")
        self.run_review(self.make_review(findings=[finding], round_number=1))
        self.run_review(self.make_review(findings=[finding], round_number=2))
        rerun = self.run_review(self.make_review(findings=[finding], round_number=2))

        self.assertEqual(rerun.returncode, 0, rerun.stderr)
        self.assertEqual(json.loads(rerun.stdout)["next"], "fix")
        self.assertEqual(json.loads(rerun.stdout)["stalled_ids"], [])
        self.assertEqual(
            self.read_history(),
            {
                "outline": [
                    {"round": 1, "ids": ["J-scope@S3"]},
                    {"round": 2, "ids": ["J-scope@S3"]},
                ]
            },
        )

    def test_rerunning_same_round_uses_latest_findings(self):
        self.run_review(self.make_review(findings=[self.finding("J-scope@S3")]))
        self.run_review(self.make_review(findings=[self.finding("J-heading@S4")]))

        self.assertEqual(
            self.read_history(), {"outline": [{"round": 1, "ids": ["J-heading@S4"]}]}
        )

    def assert_rejected(self, result, reason):
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertIn(reason, result.stderr)

    def test_invalid_review_exits_1_and_keeps_history(self):
        valid = self.finding("J-scope@S3")
        cases = {
            "target": (self.make_review(target="appendix"), "target"),
            "round": (dict(self.make_review(), round="1"), "round"),
            "round_bool": (dict(self.make_review(), round=True), "round"),
            "passed": (dict(self.make_review(), passed="yes"), "passed"),
            "findings": (dict(self.make_review(), findings={"id": "x"}), "findings"),
            "finding_id": (
                self.make_review(findings=[dict(valid, id=1)]),
                "id",
            ),
            "category": (
                self.make_review(findings=[dict(valid, category="manual")]),
                "category",
            ),
            "not_object": ([], "object"),
        }
        self.run_review(self.make_review(findings=[valid]))
        before = self.history_path.read_bytes()

        for name, (review, reason) in cases.items():
            with self.subTest(name):
                self.assert_rejected(self.run_review(review), reason)
                self.assertEqual(self.history_path.read_bytes(), before)

    def test_unparsable_review_exits_1_without_creating_history(self):
        self.review_path.write_text("{not json", encoding="utf-8")
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--review",
                str(self.review_path),
                "--history",
                str(self.history_path),
            ],
            capture_output=True,
            text=True,
        )

        self.assert_rejected(result, "loop_state.py:")
        self.assertFalse(self.history_path.exists())

    def test_missing_review_file_exits_1(self):
        self.review_path = self.root / "missing" / "review.json"
        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT),
                "--review",
                str(self.review_path),
                "--history",
                str(self.history_path),
            ],
            capture_output=True,
            text=True,
        )

        self.assert_rejected(result, "loop_state.py:")
        self.assertFalse(self.history_path.exists())

    def test_invalid_history_exits_1_and_keeps_history(self):
        cases = {
            "not_object": [],
            "unknown_target": {"appendix": []},
            "rounds_not_list": {"outline": {}},
            "entry_not_object": {"outline": [["J-scope@S3"]]},
            "entry_round": {"outline": [{"round": "1", "ids": []}]},
            "entry_ids": {"outline": [{"round": 1, "ids": [1]}]},
        }
        for name, history in cases.items():
            with self.subTest(name):
                self.history_path.write_text(json.dumps(history), encoding="utf-8")
                before = self.history_path.read_bytes()

                self.assert_rejected(
                    self.run_review(self.make_review()), "history"
                )
                self.assertEqual(self.history_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
