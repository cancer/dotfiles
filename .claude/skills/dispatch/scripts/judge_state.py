#!/usr/bin/env python3
"""Ask Jev to classify a conversation state and check each interpreted item against fixed questions."""

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


def judge_kind(state_file, catalog, thresholds, log_file):
    answer = call_judge(state_file, {"kind": catalog["kind"]}, log_file)["kind"]
    choice = answer["choice"]
    probabilities = answer.get("probabilities")
    if not isinstance(probabilities, dict):
        probabilities = choice if isinstance(choice, dict) else {}
    kind = choice if isinstance(choice, str) else max(probabilities, key=probabilities.get)
    if kind == "none" or probabilities.get(kind, 0) < thresholds["yes"]:
        return None, probabilities
    return kind, probabilities


def assess(entries, answers, thresholds, passing):
    """Return {entry id: {questions, passed}} where passing is the verdict every question must reach."""
    assessed = {}
    for entry_id, entry in entries.items():
        questions = {}
        for question_id, text in entry["questions"].items():
            probability = answers[question_id]["noul"]
            questions[question_id] = {"text": text, "noul": probability, "verdict": verdict(probability, thresholds)}
        assessed[entry_id] = {"questions": questions, "passed": all(question["verdict"] == passing for question in questions.values())}
    return assessed


def describe_item(item_id, item, catalog_item):
    lines = [f"{item_id} で止まっています"]
    if item["value"]:
        lines.append(f"  解釈の値: 「{item['value']}」（出どころ: {item['source']}）")
    else:
        lines.append("  解釈の値: なし")
    for question in item["questions"].values():
        if question["verdict"] != "yes":
            lines.append(f"  満たしていない条件: {question['text']}（{question['verdict']}, noul {question['noul']}）")
    default = catalog_item["default"]
    lines.append(f"  既定値: {default['value']}（出どころ: {default['source']}）" if default else "  既定値: なし")
    lines.append(f"→ {catalog_item['ask']}")
    return "\n".join(lines)


def describe_common(common_id, common, catalog_common):
    lines = [f"{common_id} で止まっています"]
    for question in common["questions"].values():
        if question["verdict"] != "no":
            lines.append(f"  該当すると判定された条件: {question['text']}（{question['verdict']}, noul {question['noul']}）")
    lines.append(f"→ {catalog_common['ask']}")
    return "\n".join(lines)


def judge_items(state_file, catalog, thresholds, log_file, kind, interpretation, answered):
    item_catalog = {item_id: {**item, "questions": {**item["questions"], **{f"{item_id}.{name}": text.format(item=item_id) for name, text in catalog["item_questions"].items()}}}
                    for item_id, item in catalog["items"].items() if item_id.startswith(kind + ".")}
    common_catalog = catalog["common"]
    questions = {question_id: {"type": "noul", "instructions": text}
                 for entry in [*item_catalog.values(), *common_catalog.values()]
                 for question_id, text in entry["questions"].items()}
    answers = call_judge(state_file, questions, log_file)
    items = {}
    for item_id, result in assess(item_catalog, answers, thresholds, "yes").items():
        interpreted = interpretation.get(item_id, {})
        status = "ok" if result["passed"] else ("answered" if item_id in answered else "ask")
        items[item_id] = {"value": interpreted.get("value", ""), "source": interpreted.get("source", "none"),
                          "questions": result["questions"], "status": status}
    commons = {}
    for common_id, result in assess(common_catalog, answers, thresholds, "no").items():
        commons[common_id] = {"questions": result["questions"], "status": "ok" if result["passed"] else "ask"}
    messages = [describe_item(item_id, item, item_catalog[item_id]) for item_id, item in items.items() if item["status"] == "ask"]
    messages += [describe_common(common_id, common, common_catalog[common_id]) for common_id, common in commons.items() if common["status"] == "ask"]
    return {"items": items, "common": commons, "ready": not messages, "message": "\n\n".join(messages)}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--state-file", required=True)
    parser.add_argument("--catalog", required=True)
    parser.add_argument("--thresholds", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--log", required=True)
    parser.add_argument("--kind", choices=("implement", "know", "write"))
    parser.add_argument("--interpretation", help="interpretation.json。無ければ種類の判定だけ行う")
    parser.add_argument("--answered-file", help="一度聞いて答えを得た項目 ID を 1 行に 1 つ")
    args = parser.parse_args(argv)
    try:
        catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
        thresholds = json.loads(Path(args.thresholds).read_text(encoding="utf-8"))
        probabilities = {}
        kind = args.kind
        if not kind:
            kind, probabilities = judge_kind(args.state_file, catalog, thresholds, args.log)
        if kind is None:
            output = {"kind": None, "kind_probabilities": probabilities, "ready": False,
                      "message": "成果物の種類が決まっていません\n→ 何を受け取りたいですか（実装 / 調査結果 / 文書）"}
        elif not args.interpretation:
            output = {"kind": kind, "kind_probabilities": probabilities, "ready": False,
                      "message": "種類が決まりました。interpretation.json を書いて、--kind と --interpretation を付けて判定し直してください"}
        else:
            interpretation = json.loads(Path(args.interpretation).read_text(encoding="utf-8"))["items"]
            answered = set(Path(args.answered_file).read_text(encoding="utf-8").split()) if args.answered_file else set()
            output = {"kind": kind, "kind_probabilities": probabilities,
                      **judge_items(args.state_file, catalog, thresholds, args.log, kind, interpretation, answered)}
        Path(args.out).write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as error:
        print(f"judge_state.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
