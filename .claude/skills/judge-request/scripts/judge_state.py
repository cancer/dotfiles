#!/usr/bin/env python3
"""Ask Jev to classify a conversation state and assess its declared requirements."""

import argparse
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_JUDGE = Path(__file__).resolve().parents[2] / "verify-task" / "scripts" / "judge.py"


def call_judge(state_file, questions, log_file):
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".json", delete=False) as stream:
        json.dump(questions, stream, ensure_ascii=False)
        questions_file = stream.name
    try:
        judge_script = os.environ.get("DIRECTOR_JUDGE_SCRIPT", str(DEFAULT_JUDGE))
        result = subprocess.run([sys.executable, judge_script, "--state-file", str(state_file), "--questions-file", questions_file, "--log", str(log_file)],
                                text=True, capture_output=True)
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or f"judge.py exited {result.returncode}")
        answers = json.loads(result.stdout)
        if not isinstance(answers, dict):
            raise ValueError("judge.py の回答は JSON object ではありません")
        return answers
    finally:
        Path(questions_file).unlink(missing_ok=True)


def verdict(probability, thresholds):
    if probability >= thresholds["yes"]:
        return "yes"
    if probability <= thresholds["no"]:
        return "no"
    return "ask"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--thresholds", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--kind", choices=("implement", "know", "write"))
    args = parser.parse_args(argv)
    try:
        catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        thresholds = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
        probabilities = {}
        if args.kind:
            kind = args.kind
        else:
            answer = call_judge(args.state_file, {"kind": {key: value for key, value in catalog["kind"].items() if key != "ask"}}, args.log)["kind"]
            choice = answer["choice"]
            probabilities = answer.get("probabilities")
            if not isinstance(probabilities, dict):
                probabilities = choice if isinstance(choice, dict) else {}
            kind = choice if isinstance(choice, str) else max(probabilities, key=probabilities.get)
            if kind == "none" or probabilities.get(kind, 0) < thresholds["yes"]:
                output = {"kind": None, "kind_probabilities": probabilities, "ask": "何を受け取りたいか"}
                Path(args.out).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
                return 0
        item_ids = [key for key in catalog if key.startswith(kind + ".")] + ["common.contradiction"]
        questions = {key: {name: value for name, value in catalog[key].items() if name != "ask"} for key in item_ids}
        answers = call_judge(args.state_file, questions, args.log)
        items = {}
        for key in item_ids:
            probability = answers[key]["noul"]
            decision = verdict(probability, thresholds)
            ask = catalog[key]["ask"] if (key == "common.contradiction" and decision in ("yes", "ask")) or (key != "common.contradiction" and decision in ("no", "ask")) else None
            entry = {"noul": probability, "verdict": decision, "ask": ask}
            if key == "common.contradiction":
                contradiction = entry
            else:
                items[key] = entry
        output = {"kind": kind, "kind_probabilities": probabilities, "items": items, "contradiction": contradiction,
                  "ready": all(item["verdict"] == "yes" for item in items.values()) and contradiction["verdict"] == "no"}
        Path(args.out).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as error:
        print(f"judge_state.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
