#!/usr/bin/env python3
"""Aggregate question answers into a deterministic PASS/FAIL verdict."""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
import sys
from typing import Any


AXES = {"instruction", "scope", "behavior", "verification"}
NOUL_RULES = {"noul_below", "noul_at_least"}


def _read_json(path: str) -> Any:
    with open(path, encoding="utf-8") as input_file:
        return json.load(input_file)


def _problem(invalid: list[dict[str, str]], question_id: str, message: str) -> None:
    invalid.append({"question": question_id, "problem": message})


def _is_probability(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and 0 <= value <= 1
        and math.isfinite(value)
    )


def _validate_rule(
    question_id: str,
    question: dict[str, Any],
    rule: Any,
    invalid: list[dict[str, str]],
) -> str | None:
    if not isinstance(rule, dict):
        _problem(invalid, question_id, "rule must be an object")
        return None

    axis = rule.get("axis")
    if not isinstance(axis, str) or axis not in AXES:
        _problem(invalid, question_id, "axis must be instruction, scope, behavior, or verification")
    if not isinstance(rule.get("summary"), str):
        _problem(invalid, question_id, "summary must be a string")
    files = rule.get("files")
    if not isinstance(files, list) or not all(isinstance(path, str) for path in files):
        _problem(invalid, question_id, "files must be an array of strings")

    fail_if = rule.get("fail_if")
    if not isinstance(fail_if, dict) or len(fail_if) != 1:
        _problem(invalid, question_id, "fail_if must contain exactly one condition")
        return None

    condition, expected = next(iter(fail_if.items()))
    question_type = question.get("type")
    if condition in NOUL_RULES:
        if question_type != "noul":
            _problem(invalid, question_id, "noul condition requires a noul question")
        if not _is_probability(expected):
            _problem(invalid, question_id, "noul threshold must be between 0 and 1")
            return None
    elif condition == "choice_in":
        if question_type != "choice":
            _problem(invalid, question_id, "choice_in condition requires a choice question")
        criteria = question.get("criteria")
        if not isinstance(criteria, dict):
            _problem(invalid, question_id, "choice question criteria must be an object")
            return None
        if (
            not isinstance(expected, list)
            or not all(isinstance(choice, str) and choice in criteria for choice in expected)
        ):
            _problem(invalid, question_id, "choice_in must contain only criteria choices")
            return None
    else:
        _problem(invalid, question_id, "fail_if contains an unknown condition")
        return None
    return condition


def decide(questions: Any, rules: Any, answers: Any) -> dict[str, Any]:
    """Return the verdict document for decoded JSON inputs."""
    invalid: list[dict[str, str]] = []
    if not isinstance(questions, dict):
        _problem(invalid, "<questions>", "questions must be an object")
        questions = {}
    if not isinstance(rules, dict):
        _problem(invalid, "<rules>", "rules must be an object")
        rules = {}
    if not isinstance(answers, dict):
        _problem(invalid, "<answers>", "answers must be an object")
        answers = {}

    for question_id in questions:
        if question_id not in rules:
            _problem(invalid, question_id, "rule is missing")
    for question_id in rules:
        if question_id not in questions:
            _problem(invalid, question_id, "question is missing")

    validated: dict[str, str | None] = {}
    for question_id, question in questions.items():
        if not isinstance(question, dict):
            _problem(invalid, question_id, "question must be an object")
            continue
        question_type = question.get("type")
        if question_type == "score":
            _problem(invalid, question_id, "score questions are not supported")
        elif not isinstance(question_type, str) or question_type not in {"noul", "choice"}:
            _problem(invalid, question_id, "question type must be noul or choice")
        elif question_type == "choice" and not isinstance(question.get("criteria"), dict):
            _problem(invalid, question_id, "choice question criteria must be an object")

        if question_id in rules:
            validated[question_id] = _validate_rule(
                question_id, question, rules[question_id], invalid
            )

        if question_id not in answers:
            _problem(invalid, question_id, "answer is missing")
            continue
        answer = answers[question_id]
        if not isinstance(answer, dict):
            _problem(invalid, question_id, "answer must be an object")
            continue
        if answer.get("type") != question_type:
            _problem(invalid, question_id, "answer type does not match question type")
            continue
        if question_type == "noul" and not _is_probability(answer.get("noul")):
            _problem(invalid, question_id, "noul answer must be between 0 and 1")
        elif question_type == "choice":
            criteria = question.get("criteria")
            choice = answer.get("choice")
            if isinstance(criteria, dict) and (not isinstance(choice, str) or choice not in criteria):
                _problem(invalid, question_id, "choice answer is not a question criterion")

    reasons: list[dict[str, Any]] = []
    for question_id, question in questions.items():
        if invalid:
            break
        if question_id not in rules or question_id not in answers:
            continue
        rule = rules[question_id]
        answer = answers[question_id]
        if not isinstance(question, dict) or not isinstance(rule, dict) or not isinstance(answer, dict):
            continue
        condition = validated.get(question_id)
        if condition is None or answer.get("type") != question.get("type"):
            continue
        if question["type"] == "noul":
            value = answer.get("noul")
            if not _is_probability(value):
                continue
            threshold = rule["fail_if"][condition]
            failed = value < threshold if condition == "noul_below" else value >= threshold
            compact_answer = {"type": "noul", "noul": value}
        else:
            choice = answer.get("choice")
            criteria = question.get("criteria")
            if not isinstance(criteria, dict) or not isinstance(choice, str) or choice not in criteria:
                continue
            failed = choice in rule["fail_if"][condition]
            compact_answer = {"type": "choice", "choice": choice}

        if failed:
            reasons.append(
                {
                    "question": question_id,
                    "axis": rule["axis"],
                    "summary": rule["summary"],
                    "files": rule["files"],
                    "answer": compact_answer,
                }
            )

    if invalid:
        verdict = "INVALID"
        reasons = []
    else:
        verdict = "FAIL" if reasons else "PASS"

    return {
        "verdict": verdict,
        "reasons": reasons,
        "questions": len(questions),
        "failed_questions": len(reasons),
        "invalid": invalid,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--questions", required=True)
    parser.add_argument("--rules", required=True)
    parser.add_argument("--answers", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    try:
        questions = _read_json(args.questions)
        rules = _read_json(args.rules)
        answers = _read_json(args.answers)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        print(f"decide.py: {error}", file=sys.stderr)
        return 1

    result = decide(questions, rules, answers)
    try:
        Path(args.out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError as error:
        print(f"decide.py: {error}", file=sys.stderr)
        return 1
    return 2 if result["verdict"] == "INVALID" else 0


if __name__ == "__main__":
    raise SystemExit(main())
