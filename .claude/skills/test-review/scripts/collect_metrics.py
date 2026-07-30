#!/usr/bin/env python3
"""既存のテスト実行結果・カバレッジ・ミューテーションレポートを正規化して集計する。

このスクリプトはテストを実行しない。CI などが既に出力したレポートを読むだけであり、
本番データや外部サービスに触れない。渡されなかった種別は "not_measured" に記録し、
レビュー側が「未計測」と「問題なし」を混同しないようにする。

使い方:
    python3 collect_metrics.py \
        --test-json run1.json --test-json run2.json \
        --nextest-json nextest.jsonl \
        --coverage-lcov lcov.info --coverage-json coverage-final.json \
        --mutation-json stryker.json \
        --targets .claude/test-review/targets.json \
        --out .claude/test-review/metrics.json

レポートの生成コマンドは references/report-inputs.md を参照。
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import dump, load_json, read_text  # noqa: E402


RELATIVE_SLOW_FLOOR_MS = 100.0


def parse_jest_like(path: str) -> list[dict]:
    """Vitest / Jest の JSON reporter 出力（--reporter=json, --json）を読む。"""
    data = load_json(path)
    records: list[dict] = []
    for file_result in data.get("testResults", []):
        file_name = file_result.get("name") or file_result.get("testFilePath") or "(unknown)"
        for case in file_result.get("assertionResults", file_result.get("testResults", [])):
            duration = case.get("duration")
            records.append(
                {
                    "id": case.get("fullName") or case.get("title") or "(unnamed)",
                    "file": file_name,
                    "status": case.get("status", "unknown"),
                    "duration_ms": float(duration) if duration is not None else None,
                    "failure": (case.get("failureMessages") or [None])[0],
                    "source": path,
                }
            )
    return records


def parse_libtest_jsonl(path: str) -> list[dict]:
    """cargo nextest --message-format libtest-json / cargo test --format json を読む。"""
    records: list[dict] = []
    for line in read_text(path).splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") != "test" or event.get("event") in (None, "started"):
            continue
        exec_time = event.get("exec_time")
        records.append(
            {
                "id": event.get("name", "(unnamed)"),
                "file": event.get("name", "").split("::")[0],
                "status": {"ok": "passed", "failed": "failed", "ignored": "skipped"}.get(
                    event.get("event"), event.get("event")
                ),
                "duration_ms": float(exec_time) * 1000 if exec_time is not None else None,
                "failure": event.get("stdout"),
                "source": path,
            }
        )
    return records


def aggregate_tests(records: list[dict], slow_threshold_ms: float) -> tuple[list[dict], list[dict]]:
    grouped: dict[str, list[dict]] = {}
    for r in records:
        grouped.setdefault(r["id"], []).append(r)

    durations_all = [r["duration_ms"] for r in records if r["duration_ms"] is not None]
    p95 = None
    if len(durations_all) >= 20:
        ordered = sorted(durations_all)
        p95 = ordered[int(len(ordered) * 0.95) - 1]

    tests: list[dict] = []
    findings: list[dict] = []
    for test_id, group in grouped.items():
        durations = [g["duration_ms"] for g in group if g["duration_ms"] is not None]
        statuses = [g["status"] for g in group]
        mean = statistics.fmean(durations) if durations else None
        stdev = statistics.pstdev(durations) if len(durations) > 1 else 0.0
        entry = {
            "id": test_id,
            "file": group[0]["file"],
            "runs": len(group),
            "statuses": statuses,
            "durations_ms": durations,
            "mean_ms": mean,
            "stddev_ms": stdev,
            "sources": sorted({g["source"] for g in group}),
        }
        tests.append(entry)

        # 同一レポート内に同名テストが複数ある場合（重複テスト）は反復実行ではないため、
        # 結果や実行時間の差を不安定さの根拠にできない
        repeated_across_reports = len(entry["sources"]) >= 2
        if repeated_across_reports and len(set(statuses)) > 1:
            findings.append(
                {
                    "kind": "unstable_status",
                    "severity_hint": "high",
                    "location": f"{entry['file']}",
                    "test": test_id,
                    "evidence": f"複数レポート間で結果が不一致: {statuses}（{', '.join(entry['sources'])}）",
                    "detail": "同一テストが実行条件によって結果を変えている。不安定なテストは回帰検出を無効化する",
                }
            )
        if "failed" in statuses:
            findings.append(
                {
                    "kind": "failing_test",
                    "severity_hint": "high",
                    "location": f"{entry['file']}",
                    "test": test_id,
                    "evidence": (group[0].get("failure") or "failed")[:200],
                    "detail": "レポート時点で失敗している",
                }
            )
        # p95 は相対順位でしかないため、単独で使うと全テストが十分速い場合でも
        # 常に上位 5% を「遅い」と報告してしまう。相対的に重いテストは絶対下限を
        # 満たすものだけを別 kind として出す。
        if mean is not None and mean >= slow_threshold_ms:
            findings.append(
                {
                    "kind": "slow_test",
                    "severity_hint": "low",
                    "location": f"{entry['file']}",
                    "test": test_id,
                    "evidence": f"平均 {mean:.0f}ms / 閾値 {slow_threshold_ms:.0f}ms",
                    "detail": "実行時間が長いテストは実行頻度を下げ、フィードバックを遅らせる",
                }
            )
        elif mean is not None and p95 is not None and mean >= p95 and mean >= RELATIVE_SLOW_FLOOR_MS:
            findings.append(
                {
                    "kind": "relatively_slow_test",
                    "severity_hint": "low",
                    "location": f"{entry['file']}",
                    "test": test_id,
                    "evidence": f"平均 {mean:.0f}ms（同一レポート内 p95 {p95:.0f}ms、下限 {RELATIVE_SLOW_FLOOR_MS:.0f}ms）",
                    "detail": "絶対値は閾値未満だが、このテスト群の中では上位の実行時間を占める",
                }
            )
        if repeated_across_reports and mean and mean > 50 and stdev > mean * 0.5 and len(durations) > 1:
            findings.append(
                {
                    "kind": "duration_variance",
                    "severity_hint": "medium",
                    "location": f"{entry['file']}",
                    "test": test_id,
                    "evidence": f"実行時間 {durations} ms（平均 {mean:.0f} / 標準偏差 {stdev:.0f}）",
                    "detail": "実行時間のばらつきが大きい。待機・外部依存・共有状態の影響が疑われる",
                }
            )
    return tests, findings


def parse_lcov(path: str) -> dict[str, dict]:
    """LCOV を {file: {"uncovered_lines": [...], "uncovered_branches": [(line, branch)]}} に正規化。"""
    result: dict[str, dict] = {}
    current: dict | None = None
    for line in read_text(path).splitlines():
        if line.startswith("SF:"):
            current = result.setdefault(line[3:].strip(), {"uncovered_lines": [], "uncovered_branches": []})
        elif current is None:
            continue
        elif line.startswith("DA:"):
            parts = line[3:].split(",")
            if len(parts) >= 2 and parts[1].strip() in ("0", "-"):
                current["uncovered_lines"].append(int(parts[0]))
        elif line.startswith("BRDA:"):
            parts = line[5:].split(",")
            if len(parts) >= 4 and parts[3].strip() in ("0", "-"):
                current["uncovered_branches"].append([int(parts[0]), parts[2].strip()])
    return result


def parse_istanbul(path: str) -> dict[str, dict]:
    """istanbul coverage-final.json を正規化。json-summary 形式は行情報が無いため空で返す。"""
    data = load_json(path)
    result: dict[str, dict] = {}
    for file_path, entry in data.items():
        if not isinstance(entry, dict) or "statementMap" not in entry:
            continue
        uncovered_lines = sorted(
            {
                entry["statementMap"][key]["start"]["line"]
                for key, hits in entry.get("s", {}).items()
                if hits == 0 and key in entry["statementMap"]
            }
        )
        uncovered_branches = []
        for key, counts in entry.get("b", {}).items():
            meta = entry.get("branchMap", {}).get(key)
            if not meta:
                continue
            for i, c in enumerate(counts):
                if c == 0:
                    uncovered_branches.append([meta["loc"]["start"]["line"], f"{meta.get('type','branch')}#{i}"])
        result[file_path] = {"uncovered_lines": uncovered_lines, "uncovered_branches": uncovered_branches}
    return result


def parse_mutation(path: str) -> list[dict]:
    """Stryker の report JSON と cargo-mutants の outcomes.json に対応。"""
    data = load_json(path)
    survived: list[dict] = []
    if isinstance(data, dict) and "files" in data:  # Stryker
        for file_path, entry in data["files"].items():
            for mutant in entry.get("mutants", []):
                if mutant.get("status") in ("Survived", "NoCoverage"):
                    survived.append(
                        {
                            "file": file_path,
                            "line": mutant.get("location", {}).get("start", {}).get("line"),
                            "mutator": mutant.get("mutatorName"),
                            "status": mutant.get("status"),
                            "description": mutant.get("description") or mutant.get("replacement"),
                        }
                    )
    elif isinstance(data, dict) and "outcomes" in data:  # cargo-mutants
        for outcome in data["outcomes"]:
            if outcome.get("summary") != "MissedMutant":
                continue
            mutant = (outcome.get("scenario") or {}).get("Mutant") or {}
            # cargo-mutants は行番号を span.start.line に持つ。バージョン差で
            # トップレベル line を持つ形も許容する（無い側を None にしない）
            span_line = ((mutant.get("span") or {}).get("start") or {}).get("line")
            survived.append(
                {
                    "file": mutant.get("file"),
                    "line": mutant.get("line") or span_line,
                    "mutator": mutant.get("genre") or mutant.get("replacement"),
                    "status": "MissedMutant",
                    "description": mutant.get("function", {}).get("function_name")
                    if isinstance(mutant.get("function"), dict)
                    else mutant.get("replacement"),
                }
            )
    return survived


def normalize_path(path: str, repo_root: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(repo_root))
    except (ValueError, OSError):
        return path.lstrip("./")


def intersect_with_targets(coverage: dict[str, dict], survived: list[dict], targets: dict | None) -> dict:
    repo_root = Path.cwd().resolve()
    cov_by_rel = {normalize_path(k, repo_root): v for k, v in coverage.items()}
    if targets is None:
        return {
            "uncovered_changed_lines": [],
            "uncovered_changed_branches": [],
            "survived_mutants_in_changed": [],
            "note": "targets 未指定のため変更範囲との突き合わせは未実施",
        }

    uncovered_lines: list[dict] = []
    uncovered_branches: list[dict] = []
    survived_in_changed: list[dict] = []
    for target in targets.get("targets", []):
        file_rel = normalize_path(target["file"], repo_root)
        changed = {line for lo, hi in target["changed_lines"] for line in range(lo, hi + 1)}
        entry = cov_by_rel.get(file_rel)
        if entry:
            hit_lines = sorted(set(entry["uncovered_lines"]) & changed)
            if hit_lines:
                uncovered_lines.append(
                    {"file": file_rel, "function": target["function"], "lines": hit_lines}
                )
            hit_branches = [b for b in entry["uncovered_branches"] if b[0] in changed]
            if hit_branches:
                uncovered_branches.append(
                    {"file": file_rel, "function": target["function"], "branches": hit_branches}
                )
        for mutant in survived:
            if mutant.get("file") is None or mutant.get("line") is None:
                continue
            if normalize_path(mutant["file"], repo_root) == file_rel and mutant["line"] in changed:
                survived_in_changed.append({**mutant, "file": file_rel, "function": target["function"]})
    return {
        "uncovered_changed_lines": uncovered_lines,
        "uncovered_changed_branches": uncovered_branches,
        "survived_mutants_in_changed": survived_in_changed,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--test-json", action="append", default=[], help="Vitest/Jest の JSON レポート（複数指定でばらつき比較）")
    ap.add_argument("--nextest-json", action="append", default=[], help="cargo nextest / cargo test の libtest JSON")
    ap.add_argument("--coverage-lcov", action="append", default=[])
    ap.add_argument("--coverage-json", action="append", default=[])
    ap.add_argument("--mutation-json", action="append", default=[])
    ap.add_argument("--targets", help="changed_targets.py の出力")
    ap.add_argument("--slow-threshold-ms", type=float, default=1000.0)
    ap.add_argument("--out")
    args = ap.parse_args()

    records: list[dict] = []
    for path in args.test_json:
        records.extend(parse_jest_like(path))
    for path in args.nextest_json:
        records.extend(parse_libtest_jsonl(path))

    coverage: dict[str, dict] = {}
    for path in args.coverage_lcov:
        coverage.update(parse_lcov(path))
    for path in args.coverage_json:
        coverage.update(parse_istanbul(path))

    survived: list[dict] = []
    for path in args.mutation_json:
        survived.extend(parse_mutation(path))

    targets = load_json(args.targets) if args.targets else None
    tests, findings = aggregate_tests(records, args.slow_threshold_ms)
    crossed = intersect_with_targets(coverage, survived, targets)

    not_measured = []
    if not records:
        not_measured.append("実行結果・実行時間")
    # レポート件数ではなく、同一テストが「別のレポートに」2 回以上現れたかで判定する。
    # TypeScript 1 件 + Rust 1 件は合計 2 件でも比較対象が無く、
    # 1 レポート内の同名テスト 2 件（重複テスト）も反復実行ではない。
    if not any(len(t["sources"]) >= 2 for t in tests):
        not_measured.append(
            "複数実行間のばらつき・不安定さ（同一テストを含むレポートが2件以上必要）"
        )
    if not coverage:
        not_measured.append("カバレッジ")
    if not survived:
        not_measured.append("ミューテーションテスト" if not args.mutation_json else None)
    not_measured = [n for n in not_measured if n]

    summary: dict[str, object] = {
        "reports": len(args.test_json) + len(args.nextest_json),
        "tests": len(tests),
        "coverage_files": len(coverage),
        "survived_mutants_total": len(survived),
    }
    for f in findings:
        summary[f["kind"]] = int(summary.get(f["kind"], 0)) + 1

    dump(
        {
            "summary": summary,
            "not_measured": not_measured,
            "findings": findings,
            "changed_scope": crossed,
            "tests": tests,
            "survived_mutants": survived,
        },
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
