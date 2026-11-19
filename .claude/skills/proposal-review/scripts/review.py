#!/usr/bin/env python3
"""Review a proposal outline or Slides deck and write a C5 JSON result."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

import check_rules
import judge_review


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workdir", required=True)
    parser.add_argument("--target", required=True, choices=("outline", "deck"))
    parser.add_argument("--round", required=True, type=int)
    parser.add_argument("--out", required=True)
    return parser


def _result(
    target: str,
    round_number: int,
    rule_findings: list[dict[str, Any]],
    semantic: dict[str, Any],
) -> dict[str, Any]:
    findings = [*rule_findings, *semantic["findings"]]
    reader = semantic["reader"]
    return {
        "target": target,
        "round": round_number,
        "reader": reader,
        "findings": findings,
        "passed": not findings and reader["score"] >= semantic["yes_threshold"],
    }


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.round < 1:
            raise ValueError("round は 1 以上である必要があります")
        workdir = Path(args.workdir)
        if args.target == "outline":
            rule_findings = check_rules.check_outline(workdir / "outline.md")
        else:
            rule_findings = check_rules.check_deck(workdir)
        semantic = judge_review.review(workdir, args.target)
        output = Path(args.out)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(_result(args.target, args.round, rule_findings, semantic), ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        return 0
    except (OSError, UnicodeError, json.JSONDecodeError, KeyError, TypeError, ValueError, RuntimeError) as error:
        print(f"review.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
