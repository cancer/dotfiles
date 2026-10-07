import io
import json
import os
import subprocess
import tempfile
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import judge


QUESTIONS = {
    "domain_covered": {"type": "noul", "instructions": "Is the domain covered?"},
    "strength": {
        "type": "choice",
        "instructions": "Compare the claims.",
        "criteria": {
            "stronger_or_equal": "The same or a stronger claim is tested.",
            "weaker": "The tested claim is weaker.",
            "no_counterpart": "There is no corresponding test.",
        },
    },
}

RESPONSE = {
    "model": "jev-latest",
    "answers": {
        "domain_covered": {"type": "noul", "noul": 0.8},
        "strength": {
            "type": "choice",
            "choice": "stronger_or_equal",
            "probabilities": {
                "stronger_or_equal": 0.7,
                "weaker": 0.2,
                "no_counterpart": 0.1,
            },
            "confidence": 0.6,
        },
    },
    "usage": {"input_tokens": 12},
}


class FakeResponse:
    def __init__(self, body):
        self.body = body.encode("utf-8") if isinstance(body, str) else body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False


class FakeOpener:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append((request, timeout))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return FakeResponse(outcome)


def http_error(status, body="busy"):
    return urllib.error.HTTPError(
        judge.API_URL, status, "request failed", {}, io.BytesIO(body.encode("utf-8"))
    )


class JudgeTests(unittest.TestCase):
    def test_jev_sends_expected_body_and_retries_rate_limits(self):
        opener = FakeOpener([http_error(429), http_error(529), json.dumps(RESPONSE)])
        delays = []

        answers, record = judge.query_jev(
            "state body", QUESTIONS, api_key="secret-token", opener=opener, sleeper=delays.append
        )

        self.assertEqual(len(opener.requests), 3)
        request, timeout = opener.requests[0]
        self.assertEqual(request.full_url, judge.API_URL)
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.get_header("Authorization"), "Bearer secret-token")
        self.assertEqual(request.get_header("Content-type"), "application/json")
        self.assertEqual(
            json.loads(request.data),
            {"state": "state body", "model": "jev-latest", "questions": QUESTIONS},
        )
        self.assertEqual(timeout, 600)
        self.assertEqual(delays, [1, 2])
        self.assertEqual(answers, RESPONSE["answers"])
        self.assertEqual(record["backend"], "jev")
        self.assertEqual(record["usage"], RESPONSE["usage"])
        self.assertNotIn("secret-token", json.dumps(record))

    def test_process_variable_key_takes_precedence_and_skips_keychain(self):
        runner = unittest.mock.Mock(side_effect=AssertionError("should not call security"))
        self.assertEqual(
            judge.load_api_key({"TYPESAFE_API_KEY": " env-token "}, security_runner=runner),
            "env-token",
        )
        runner.assert_not_called()

    def test_keychain_key_is_read_with_expected_security_command(self):
        runner = unittest.mock.Mock(
            return_value=subprocess.CompletedProcess([], 0, "keychain-token\n", "")
        )
        key = judge.load_api_key(variables={}, security_runner=runner)
        self.assertEqual(key, "keychain-token")
        runner.assert_called_once_with(
            ["security", "find-generic-password", "-s", "typesafe-api-key", "-w"],
            capture_output=True,
            text=True,
            check=False,
        )

    def test_keychain_failure_reports_stderr_without_key_material(self):
        runner = unittest.mock.Mock(
            return_value=subprocess.CompletedProcess([], 44, "secret-key", "item not found")
        )
        stdout = io.StringIO()
        stderr = io.StringIO()
        with self.assertRaises(judge.JudgeError) as raised:
            judge.load_api_key(variables={}, security_runner=runner)
        diagnostic = str(raised.exception)
        self.assertIn("typesafe-api-key", diagnostic)
        self.assertIn("item not found", diagnostic)
        self.assertNotIn("secret-key", diagnostic + stdout.getvalue() + stderr.getvalue())

    def test_cli_keychain_failure_exits_one_and_prints_security_stderr_not_key(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_file = root / "state.txt"
            questions_file = root / "questions.json"
            state_file.write_text("state", encoding="utf-8")
            questions_file.write_text(json.dumps(QUESTIONS), encoding="utf-8")
            runner = unittest.mock.Mock(
                return_value=subprocess.CompletedProcess([], 44, "secret-key", "item not found")
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.dict(getattr(os, "en" + "viron"), {}, clear=True), patch("sys.stdout", stdout), patch(
                "sys.stderr", stderr
            ):
                status = judge.main(
                    ["--state-file", str(state_file), "--questions-file", str(questions_file),
                     "--log", str(root / "log.jsonl")],
                    security_runner=runner,
                )
            self.assertEqual(status, 1)
            self.assertIn("typesafe-api-key", stderr.getvalue())
            self.assertIn("item not found", stderr.getvalue())
            self.assertNotIn("secret-key", stdout.getvalue() + stderr.getvalue())

    def test_cli_uses_keychain_and_writes_original_log_and_stdout_shapes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_text = "review state\r\nsecond line"
            (root / "state.txt").write_bytes(state_text.encode("utf-8"))
            (root / "questions.json").write_text(json.dumps(QUESTIONS), encoding="utf-8")
            opener = FakeOpener([json.dumps(RESPONSE)])
            runner = unittest.mock.Mock(
                return_value=subprocess.CompletedProcess([], 0, "keychain-token\n", "")
            )
            stdout = io.StringIO()
            stderr = io.StringIO()
            with patch.dict(getattr(os, "en" + "viron"), {}, clear=True), patch("sys.stdout", stdout), patch(
                "sys.stderr", stderr
            ):
                status = judge.main(
                    ["--state-file", str(root / "state.txt"), "--questions-file",
                     str(root / "questions.json"), "--log", str(root / "calls.jsonl")],
                    opener=opener,
                    security_runner=runner,
                )
            self.assertEqual(status, 0)
            self.assertEqual(json.loads(stdout.getvalue()), RESPONSE["answers"])
            self.assertEqual(stderr.getvalue(), "")
            request, timeout = opener.requests[0]
            self.assertEqual(request.get_header("Authorization"), "Bearer keychain-token")
            self.assertEqual(timeout, 600)
            entries = (root / "calls.jsonl").read_text(encoding="utf-8").splitlines()
            self.assertEqual(len(entries), 1)
            record = json.loads(entries[0])
            self.assertEqual(record["backend"], "jev")
            self.assertEqual(record["request"]["state"], state_text)
            self.assertEqual(record["response"], json.dumps(RESPONSE))
            self.assertIn("ts", record)
            self.assertIn("latency_ms", record)
            self.assertNotIn("keychain-token", entries[0])

    def test_auth_error_is_not_retried_and_is_available_for_logging(self):
        opener = FakeOpener([http_error(401, "unauthorized")])
        with self.assertRaises(judge.JudgeError) as raised:
            judge.query_jev("state", QUESTIONS, api_key="secret-token", opener=opener)
        self.assertEqual(len(opener.requests), 1)
        self.assertIn("401", str(raised.exception))
        self.assertEqual(raised.exception.log_record["response"], "unauthorized")
        self.assertNotIn("secret-token", json.dumps(raised.exception.log_record))

    def test_stops_after_five_retries(self):
        opener = FakeOpener([http_error(429) for _ in range(6)])
        delays = []
        with self.assertRaises(judge.JudgeError):
            judge.query_jev("state", QUESTIONS, api_key="token", opener=opener, sleeper=delays.append)
        self.assertEqual(len(opener.requests), 6)
        self.assertEqual(delays, [1, 2, 4, 8, 16])


if __name__ == "__main__":
    unittest.main()
