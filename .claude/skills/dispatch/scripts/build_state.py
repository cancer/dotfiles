#!/usr/bin/env python3
"""Build a source-only companion state from supplied text and repository facts."""

import argparse
import subprocess
import sys
from pathlib import Path

MAX_STATE_LENGTH = 30000
MANIFESTS = ("package.json", "Cargo.toml", "pyproject.toml")
TEST_PATTERNS = ("*.test.*", "*_test.*", "test_*.py")


def read_optional(path):
    return Path(path).read_text(encoding="utf-8") if path else ""


def has_tests(cwd):
    if any((cwd / name).is_dir() for name in ("tests", "test")):
        return True
    return any(path.is_file() for pattern in TEST_PATTERNS for path in cwd.rglob(pattern))


def issue_kind(reference):
    if not reference:
        return "未指定"
    value = reference.rstrip("/")
    if "github.com/" in value:
        value = value.split("github.com/", 1)[1]
    value = value.removesuffix(".git")
    parts = value.split("/")
    if len(parts) == 2 and "#" in parts[1]:
        owner, repository_number = parts
        repository, number = repository_number.rsplit("#", 1)
    elif len(parts) >= 4 and parts[2] in ("issues", "pull"):
        owner, repository, _, number = parts[:4]
    else:
        return "未確認"
    endpoint = f"repos/{owner}/{repository}/issues/{number}"
    try:
        result = subprocess.run(["gh", "api", endpoint], text=True, capture_output=True, check=True)
        import json
        return "PR" if json.loads(result.stdout).get("pull_request") else "issue"
    except (OSError, subprocess.CalledProcessError, ValueError):
        print("build_state.py: gh api で issue / PR 種別を確認できませんでした", file=sys.stderr)
        return "未確認"


def collect_facts(cwd_arg, reference, plan):
    if not cwd_arg:
        return ["対象ディレクトリ: 未確認", "git: 未確認", "マニフェスト: 未確認",
                f"issue / PR 種別: {issue_kind(reference)}",
                f"計画書: {'あり' if plan and Path(plan).is_file() else ('なし' if plan else '未指定')}",
                "既存テスト: 未確認"]
    cwd = Path(cwd_arg)
    manifests = [name for name in MANIFESTS if (cwd / name).is_file()]
    manifest_text = ", ".join(manifests) if manifests else "なし"
    return [
        f"対象ディレクトリ: {cwd}",
        f".git: {'あり' if (cwd / '.git').exists() else 'なし'}",
        f"マニフェスト: {manifest_text}",
        f"issue / PR 種別: {issue_kind(reference)}",
        f"計画書: {'あり' if plan and Path(plan).is_file() else ('なし' if plan else '未指定')}",
        f"既存テスト: {'あり' if has_tests(cwd) else 'なし'}",
    ]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--user-quotes", required=True)
    parser.add_argument("--request")
    parser.add_argument("--worker-report")
    parser.add_argument("--cwd")
    parser.add_argument("--ref")
    parser.add_argument("--plan")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    try:
        sections = ["ユーザー発言の引用\n" + read_optional(args.user_quotes).rstrip(),
                    "依頼の原文\n" + read_optional(args.request).rstrip(),
                    "事実\nスクリプト収集分:\n- " + "\n- ".join(collect_facts(args.cwd, args.ref, args.plan))]
        report = read_optional(args.worker_report).rstrip()
        if report:
            sections[2] += "\n作業係の報告:\n" + report
        state = "\n\n".join(sections) + "\n"
        if len(state) > MAX_STATE_LENGTH:
            raise ValueError(f"State が {MAX_STATE_LENGTH} 字を超えています")
        Path(args.out).write_text(state, encoding="utf-8")
        return 0
    except (OSError, UnicodeError, ValueError) as error:
        print(f"build_state.py: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
