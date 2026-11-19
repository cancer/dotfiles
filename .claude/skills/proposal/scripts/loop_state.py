#!/usr/bin/env python3
"""Choose the next proposal-loop action from one C5 review."""

import argparse
import json
import sys
from pathlib import Path


TARGETS = ("outline", "deck")


def read_json_file(path):
    return json.loads(path.read_text(encoding="utf-8"))


def is_round_number(value):
    return isinstance(value, int) and not isinstance(value, bool)


def validate_review(review):
    if not isinstance(review, dict):
        raise ValueError("review must be a JSON object")
    if review.get("target") not in TARGETS:
        raise ValueError("review target must be outline or deck")
    if not is_round_number(review.get("round")):
        raise ValueError("review round must be an integer")
    if not isinstance(review.get("passed"), bool):
        raise ValueError("review passed must be a boolean")

    findings = review.get("findings")
    if not isinstance(findings, list):
        raise ValueError("review findings must be a list")
    for finding in findings:
        if not isinstance(finding, dict) or not isinstance(finding.get("id"), str):
            raise ValueError("each finding must have a string id")
        if finding.get("category") not in ("auto", "ask"):
            raise ValueError("each finding category must be auto or ask")
    return findings


def load_history(path):
    if not path.exists():
        return {}

    history = read_json_file(path)
    if not isinstance(history, dict):
        raise ValueError("history must be a JSON object")
    for target, rounds in history.items():
        if target not in TARGETS or not isinstance(rounds, list):
            raise ValueError("history must map outline and deck to review entries")
        for entry in rounds:
            if (
                not isinstance(entry, dict)
                or not is_round_number(entry.get("round"))
                or not isinstance(entry.get("ids"), list)
                or any(not isinstance(item, str) for item in entry["ids"])
            ):
                raise ValueError(
                    "each history entry must have an integer round and a list of finding ids"
                )
    return history


def record_round(rounds, round_number, round_ids):
    """Return rounds with this round's ids, replacing an earlier record of the same round."""
    entry = {"round": round_number, "ids": round_ids}
    if any(existing["round"] == round_number for existing in rounds):
        return [entry if existing["round"] == round_number else existing for existing in rounds]
    return rounds + [entry]


def find_stalled_ids(rounds):
    if len(rounds) < 3:
        return []
    repeated = set(rounds[-1]["ids"]) & set(rounds[-2]["ids"]) & set(rounds[-3]["ids"])
    return sorted(repeated)


def choose_next(review, findings, stalled_ids):
    if review["passed"]:
        return "done"
    if any(finding["category"] == "ask" for finding in findings):
        return "ask"
    if stalled_ids:
        return "stalled"
    return "fix"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--review", required=True, type=Path, help="C5 review JSON")
    parser.add_argument("--history", required=True, type=Path, help="C0 loop-history.json")
    args = parser.parse_args(argv)

    try:
        review = read_json_file(args.review)
        findings = validate_review(review)
        history = load_history(args.history)
        target = review["target"]
        round_ids = [finding["id"] for finding in findings]
        target_history = record_round(history.get(target, []), review["round"], round_ids)
        history[target] = target_history
        stalled_ids = find_stalled_ids(target_history)
        output = {
            "next": choose_next(review, findings, stalled_ids),
            "findings": findings,
            "stalled_ids": stalled_ids,
        }

        args.history.parent.mkdir(parents=True, exist_ok=True)
        args.history.write_text(
            json.dumps(history, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(json.dumps(output, ensure_ascii=False))
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError) as error:
        print(f"loop_state.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
