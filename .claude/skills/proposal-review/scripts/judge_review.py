"""Use Jev to assess proposal meaning and reader confidence."""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
from typing import Any

from check_rules import deck_visible_texts


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_JUDGE = SCRIPT_DIR.parents[1] / "verify-task" / "scripts" / "judge.py"
CATALOG_PATH = SCRIPT_DIR / "catalog.json"
THRESHOLDS_PATH = SCRIPT_DIR / "thresholds.json"
READER_IDS = (
    "reader.entrust",
    "reader.understand_problem",
    "reader.why_us",
    "reader.next_step",
)


def _read_confirmed_facts(path: Path) -> str:
    lines = path.read_text(encoding="utf-8").splitlines()
    start = next(
        (index for index, line in enumerate(lines) if line.strip() == "## 確認済み事実"),
        None,
    )
    if start is None:
        # 事実の裏付けなしに判定させないため、入力の失敗として止める
        raise ValueError(f"{path.name} に「## 確認済み事実」節がありません")
    end = next(
        (index for index in range(start + 1, len(lines)) if re.match(r"^## (?!#)", lines[index])),
        len(lines),
    )
    return "\n".join(lines[start:end]).strip()


def _target_text(workdir: Path, target: str) -> str:
    if target == "outline":
        return (workdir / "outline.md").read_text(encoding="utf-8")
    project = workdir / "deck" / "project"
    deck = json.loads((project / "deck.json").read_text(encoding="utf-8"))
    order = deck.get("order") if isinstance(deck, dict) else None
    slide_texts = deck_visible_texts(workdir, order if isinstance(order, list) else None)
    return "\n".join(f"{slide_id}: {text}" for slide_id, text in slide_texts.items())


def build_state(workdir: Path | str, target: str) -> str:
    root = Path(workdir)
    request = (root / "request.md").read_text(encoding="utf-8")
    confirmed_facts = _read_confirmed_facts(root / "industry-notes.md")
    target_document = _target_text(root, target)
    return (
        "## request.md\n"
        f"{request}\n\n"
        "## industry-notes.md / 確認済み事実\n"
        f"{confirmed_facts}\n\n"
        f"## target: {target}\n"
        f"{target_document}"
    )


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path.name} は JSON object である必要があります")
    return value


def _call_judge(state: str, questions: dict[str, Any]) -> dict[str, Any]:
    judge_script = Path(os.environ.get("PROPOSAL_JUDGE_SCRIPT", str(DEFAULT_JUDGE)))
    with tempfile.TemporaryDirectory(prefix="proposal-review-") as temporary_directory:
        temporary = Path(temporary_directory)
        state_path = temporary / "state.txt"
        questions_path = temporary / "questions.json"
        log_path = temporary / "judge.jsonl"
        state_path.write_text(state, encoding="utf-8")
        questions_path.write_text(json.dumps(questions, ensure_ascii=False), encoding="utf-8")
        process = subprocess.run(
            [
                sys.executable,
                str(judge_script),
                "--state-file",
                str(state_path),
                "--questions-file",
                str(questions_path),
                "--log",
                str(log_path),
            ],
            text=True,
            capture_output=True,
        )
        if process.returncode != 0:
            detail = process.stderr.strip() or f"judge.py exited {process.returncode}"
            raise RuntimeError(f"judge.py: {detail}")
        try:
            answers = json.loads(process.stdout)
        except json.JSONDecodeError as error:
            raise ValueError(f"judge.py の回答を JSON として読めません: {error}") from error
        if not isinstance(answers, dict):
            raise ValueError("judge.py の回答は JSON object ではありません")
        return answers


def _probability(answers: dict[str, Any], key: str) -> float:
    answer = answers.get(key)
    if not isinstance(answer, dict) or "noul" not in answer:
        raise ValueError(f"judge.py の回答に {key}.noul がありません")
    value = answer["noul"]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"judge.py の {key}.noul は数値ではありません")
    probability = float(value)
    if not math.isfinite(probability) or not 0 <= probability <= 1:
        raise ValueError(f"judge.py の {key}.noul は 0 から 1 の範囲外です")
    return probability


def review(workdir: Path | str, target: str) -> dict[str, Any]:
    if target not in {"outline", "deck"}:
        raise ValueError("target は outline または deck である必要があります")
    catalog = _load_json(CATALOG_PATH)
    thresholds = _load_json(THRESHOLDS_PATH)
    yes_threshold = thresholds.get("yes")
    if isinstance(yes_threshold, bool) or not isinstance(yes_threshold, (int, float)) or not 0 <= yes_threshold <= 1:
        raise ValueError("thresholds.json の yes は 0 から 1 の数値である必要があります")
    state = build_state(workdir, target)
    questions = {
        key: {"type": config["type"], "instructions": config["instructions"]}
        for key, config in catalog.items()
    }
    answers = _call_judge(state, questions)
    findings: list[dict[str, Any]] = []
    probabilities: dict[str, float] = {}

    for key, config in catalog.items():
        probability = _probability(answers, key)
        probabilities[key] = probability
        if probability < yes_threshold:
            findings.append(
                {
                    "id": f"{key}@all",
                    "rule": key,
                    "slide": None,
                    "category": config["category"],
                    "message": config["message"],
                    "source": "jev",
                }
            )

    return {
        "reader": {
            "score": probabilities["reader.entrust"],
            "diagnostics": {
                key: probabilities[key] for key in READER_IDS if key != "reader.entrust"
            },
        },
        "findings": findings,
        "yes_threshold": float(yes_threshold),
    }
