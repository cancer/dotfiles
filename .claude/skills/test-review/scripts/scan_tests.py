#!/usr/bin/env python3
"""テストコードの静的スキャン（TypeScript/JavaScript, Rust）。

検出する事実だけを出力し、重要度の確定や是非の判断は行わない。
各 finding は必ず file:line と evidence（観測したトークン）を持つ。

使い方:
    python3 scan_tests.py [<path>...] [--targets targets.json] [--out out.json] [--exclude PATTERN]...

path はファイルでもディレクトリでもよい。--targets には changed_targets.py の出力を渡し、
変更されたテストファイルと対応テスト候補を対象に加える。ディレクトリは再帰的に走査し、
テストファイルらしいパス（*.test.*, *.spec.*, tests/, __tests__/）と、
`#[test]` を含む .rs を対象にする。
"""

from __future__ import annotations

import argparse
import fnmatch
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    LineIndex,
    block_span,
    declared_level,
    detect_lang,
    dump,
    load_json,
    looks_like_test_path,
    mask_source,
    read_text,
)

SKIP_DIRS = {"node_modules", ".git", "target", "dist", "build", ".next", "coverage", "vendor"}

# 外部依存シグナル。kind は指摘の分類に、pattern は evidence にそのまま載せる。
DEP_PATTERNS = {
    "ts": [
        ("network", r"\bfetch\s*\(|\baxios\b|\bgot\s*\(|\bsupertest\b|\brequest\s*\(\s*app|https?\.request\s*\(|new\s+WebSocket\b|\bnock\b|\bmsw\b"),
        ("db", r"\bprisma\b|PrismaClient|@prisma/client|\$(executeRaw|queryRaw)|\bknex\b|\bmongoose\b|\bTypeORM\b|\bdrizzle\b|\bnew\s+(Pool|Client)\s*\(|(create|get)Connection\s*\(|\bredis\b|\bDynamoDB\b"),
        ("filesystem", r"\bfs\.[a-zA-Z]|\bfs/promises\b|readFileSync\s*\(|writeFileSync\s*\(|\bmkdtemp|os\.tmpdir\s*\("),
        ("time", r"Date\.now\s*\(|new\s+Date\s*\(\s*\)|performance\.now\s*\(|setTimeout\s*\(|setInterval\s*\(|\bdayjs\s*\(\s*\)|\bmoment\s*\(\s*\)"),
        ("random", r"Math\.random\s*\(|crypto\.randomUUID\s*\(|randomBytes\s*\(|\buuidv4\s*\(|\bfaker\."),
        ("app_boot", r"\bapp\.listen\s*\(|createServer\s*\(|NestFactory\.|createApp\s*\(|\btestcontainers\b|startServer\s*\(|\bbuildServer\s*\("),
        ("browser", r"\bpage\.(goto|click|fill)\s*\(|\bbrowser\.(newPage|launch)\s*\(|\bcy\.\w+\s*\("),
        ("process", r"child_process|execSync\s*\(|\bspawn\s*\("),
        ("env", r"process\.env\.[A-Z_]+"),
    ],
    "rust": [
        ("network", r"\breqwest::|\bhyper::|TcpStream::|TcpListener::|UdpSocket::|\bwiremock\b"),
        ("db", r"\bsqlx::|\bdiesel::|tokio_postgres|\bredis::|PgPool|SqlitePool|\bmongodb::"),
        ("filesystem", r"\bstd::fs::|\bfs::(read|write|create|remove)|\btempfile::|\btempdir\s*\(|File::(open|create)\s*\("),
        ("time", r"SystemTime::now\s*\(|Instant::now\s*\(|Utc::now\s*\(|Local::now\s*\(|thread::sleep\s*\(|tokio::time::sleep\s*\("),
        ("random", r"\brand::|thread_rng\s*\(|\brandom\s*\(\s*\)|Uuid::new_v4\s*\("),
        ("app_boot", r"\btestcontainers\b|\baxum::serve\b|\bactix_web::test\b|Server::bind\s*\(|\brocket::local\b"),
        ("process", r"Command::new\s*\("),
        ("env", r"\benv::var\s*\(|\bstd::env::var\s*\("),
    ],
}

ASSERT_PATTERNS = {
    "ts": r"\bexpect\s*\(|\bassert(?:\.\w+)?\s*\(|\.should\b|\btoMatchSnapshot\s*\(|\btoMatchInlineSnapshot\s*\(",
    "rust": r"\bassert(?:_eq|_ne|_matches)?!\s*[\(\[]|\bclaim::assert|\binsta::assert",
}
WEAK_PATTERNS = {
    "ts": r"\.(toBeDefined|toBeUndefined|toBeTruthy|toBeFalsy|toBeNull|toBeInstanceOf|toBeTypeOf)\s*\(|expect\s*\(\s*(true|false)\s*\)\s*\.toBe\s*\(\s*(true|false)\s*\)|\.not\.toThrow\s*\(\s*\)",
    "rust": r"assert!\s*\(\s*(true|[^)]*\.is_ok\s*\(\s*\)|[^)]*\.is_some\s*\(\s*\))\s*[,)]",
}
MOCK_ASSERT_PATTERNS = {
    "ts": r"\.(toHaveBeenCalled|toHaveBeenCalledTimes|toHaveBeenCalledWith|toHaveBeenNthCalledWith|toHaveBeenLastCalledWith|toHaveReturnedWith)\s*\(|\.mock\.(calls|results)\b|\bverify\s*\(",
    "rust": r"\.times\s*\(|\.checkpoint\s*\(|expect_\w+\s*\(\s*\)\s*\.\s*(times|returning)",
}

TS_TEST_RE = re.compile(
    r"\b(?P<fn>it|test|describe|xit|xtest|xdescribe|fit|fdescribe)\s*"
    r"(?:\.\s*(?P<mod>skip|only|todo|failing|concurrent|sequential|skipIf|runIf|each)\b[^(]*)?\s*\(",
)
TS_HOOK_RE = re.compile(r"\b(?P<fn>beforeEach|beforeAll|afterEach|afterAll)\s*\(")
RUST_TEST_ATTR_RE = re.compile(r"#\s*\[\s*(?:tokio::|async_std::|actix_web::|rstest\b)?[\w:]*test[\w:]*\b")
RUST_FN_RE = re.compile(r"\bfn\s+(?P<name>\w+)\s*\(")

SEVERITY_HINT = {
    "disabled_test": "high",
    "focused_test": "high",
    "no_assertion": "high",
    "weak_assertion_only": "medium",
    "mock_only_assertion": "medium",
    "level_mismatch": "medium",
    "duplicate_test_body": "low",
    "duplicate_test_name": "medium",
    "external_dependency": "low",
}


def iter_target_files(paths: list[str], excludes: list[str]) -> list[str]:
    found: list[str] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            found.append(str(p))
            continue
        for child in p.rglob("*"):
            if not child.is_file():
                continue
            if SKIP_DIRS & set(child.parts):
                continue
            lang = detect_lang(str(child))
            if lang is None:
                continue
            if looks_like_test_path(str(child)):
                found.append(str(child))
            elif lang == "rust" and "#[test" in read_text(str(child)):
                found.append(str(child))
    result = []
    for f in sorted(set(found)):
        if any(fnmatch.fnmatch(f, pat) for pat in excludes):
            continue
        if detect_lang(f):
            result.append(f)
    return result


def first_string_literal(text: str, start: int, window: int = 300) -> str | None:
    m = re.search(r"['\"`](?P<s>[^'\"`\n]{0,200})['\"`]", text[start : start + window])
    return m.group("s") if m else None


def call_close(masked: str, open_paren: int) -> int | None:
    depth = 0
    for i in range(open_paren, len(masked)):
        if masked[i] == "(":
            depth += 1
        elif masked[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return None


def call_arg_region(masked: str, open_paren: int) -> tuple[int, int] | None:
    """テスト呼び出しの引数リストの範囲 (開始, 終了) を返す。

    `it.each(table)("name", cb)` のような 2 段呼び出しでは、コールバックは 2 段目に
    あるため範囲を 2 段目へ進める。1 段目に留まると、テーブルデータ内のアロー関数
    （`cases.map(c => …)`）を本体と誤認する。
    """
    close = call_close(masked, open_paren)
    if close is None:
        return None
    chained = re.match(r"[ \t]*\(", masked[close + 1 :])
    if chained:
        second_open = close + chained.end()
        second_close = call_close(masked, second_open)
        if second_close is not None:
            return second_open + 1, second_close
    return open_paren + 1, close


def callback_body_span(masked: str, arg_start: int, arg_end: int) -> tuple[int, int] | None:
    """引数リスト内のコールバック本体を返す。本体を持たない呼び出しでは None。

    探索範囲を引数リストに限るのは、`it.todo("later")` のように本体の無い呼び出しが
    後続テストの本体を取り込むのを、セミコロンの有無に依存せず防ぐため。
    `{` を伴う `=>` を優先するのは、引数の分割代入（Playwright の fixture、
    Vitest の context）が先に `{` を出す形と、データ側のアロー関数を区別するため。
    """
    window = masked[arg_start:arg_end]
    arrows = [arg_start + m.end() for m in re.finditer("=>", window)]
    for after in arrows:
        if masked[after:arg_end].lstrip()[:1] == "{":
            return block_span(masked, after)
    if arrows:
        # 式本体のアロー関数（`it("n", (done) => done())`）。ブロックは無いが
        # テストではあるため引数リストの残りを本文として扱う。対象外にすると
        # 検証を持たないテストが集計から消える
        return arrows[-1], arg_end
    fn_kw = re.search(r"\bfunction\b", window)
    if fn_kw is not None:
        close = masked.find(")", arg_start + fn_kw.end())
        if 0 <= close < arg_end:
            return block_span(masked, close)
    return None


def extract_ts_tests(text: str, masked: str, path: str) -> list[dict]:
    idx = LineIndex(text)
    tests: list[dict] = []
    disabled_suites: list[tuple[int, int, str]] = []
    for m in TS_TEST_RE.finditer(masked):
        fn, mod = m.group("fn"), m.group("mod")
        disabled = fn in {"xit", "xtest", "xdescribe"} or mod in {"skip", "todo"}
        is_container = fn in {"describe", "xdescribe", "fdescribe"}
        region = call_arg_region(masked, m.end() - 1)
        if region is None:
            continue
        # テスト名は引数リストの先頭にある。2 段呼び出しでは 2 段目が名前を持つ
        name = first_string_literal(text, region[0]) or "(名前未取得)"
        span = callback_body_span(masked, *region)
        if span is None:
            # 本体が無い呼び出し。it.todo は無効化として残し、それ以外は対象外
            if disabled and not is_container:
                tests.append(
                    {
                        "file": path,
                        "lang": "ts",
                        "kind": "case",
                        "name": name,
                        "line": idx.line_of(m.start()),
                        "disabled": True,
                        "disabled_marker": f"{fn}.{mod}" if mod else fn,
                        "focused": False,
                        "body": "",
                        "masked_body": "",
                        "span": None,
                        "body_start_line": idx.line_of(m.start()),
                        "end_line": idx.line_of(m.start()),
                    }
                )
            continue
        open_i, close_i = span
        if is_container:
            focused_suite = mod == "only" or fn == "fdescribe"
            if disabled or focused_suite:
                marker = f"{fn}.{mod}" if mod else fn
                if disabled:
                    disabled_suites.append((idx.line_of(m.start()), idx.line_of(close_i), marker))
                tests.append(
                    {
                        "file": path,
                        "lang": "ts",
                        "kind": "suite",
                        "name": name,
                        "line": idx.line_of(m.start()),
                        "disabled": disabled,
                        "disabled_marker": marker if disabled else None,
                        "focused": focused_suite,
                        "body": text[open_i : close_i + 1],
                        "masked_body": masked[open_i : close_i + 1],
                        "span": (open_i, close_i),
                        "body_start_line": idx.line_of(open_i),
                        "end_line": idx.line_of(close_i),
                    }
                )
            continue  # 有効な describe 自体は検証単位ではない
        tests.append(
            {
                "file": path,
                "lang": "ts",
                "kind": "case",
                "name": name,
                "line": idx.line_of(m.start()),
                "disabled": disabled,
                "disabled_marker": (f"{fn}.{mod}" if mod else fn) if disabled else None,
                "focused": mod == "only" or fn in {"fit", "fdescribe"},
                "body": text[open_i : close_i + 1],
                "masked_body": masked[open_i : close_i + 1],
                "span": (open_i, close_i),
                "body_start_line": idx.line_of(open_i),
                "end_line": idx.line_of(close_i),
            }
        )

    # DB 接続や時刻固定の準備は beforeEach / beforeAll に置かれることが多い。
    # フックを対象外にすると、テスト本文だけを見て「外部依存なし」と読める
    for m in TS_HOOK_RE.finditer(masked):
        region = call_arg_region(masked, m.end() - 1)
        span = callback_body_span(masked, *region) if region else None
        if span is None:
            continue
        open_i, close_i = span
        tests.append(
            {
                "file": path,
                "lang": "ts",
                "kind": "hook",
                "name": f"{m.group('fn')}()",
                "line": idx.line_of(m.start()),
                "disabled": False,
                "disabled_marker": None,
                "focused": False,
                "body": text[open_i : close_i + 1],
                "masked_body": masked[open_i : close_i + 1],
                "span": (open_i, close_i),
                "body_start_line": idx.line_of(open_i),
                "end_line": idx.line_of(close_i),
            }
        )

    # 無効化されたスイート配下のテストは実行されない。個別の検証不足として報告すると
    # 「実行されているテストの問題」と読まれるため、無効化側へ寄せる。
    for t in tests:
        if t["kind"] not in ("case", "hook") or t["disabled"]:
            continue
        enclosing = next((s for s in disabled_suites if s[0] <= t["line"] <= s[1]), None)
        if enclosing:
            t["disabled"] = True
            t["disabled_marker"] = f"{enclosing[2]}（上位スイート {enclosing[0]} 行目）"
    return tests


def extract_rust_tests(text: str, masked: str, path: str) -> list[dict]:
    idx = LineIndex(text)
    tests: list[dict] = []
    for m in RUST_TEST_ATTR_RE.finditer(masked):
        tail = masked[m.end() : m.end() + 600]
        fn_m = RUST_FN_RE.search(tail)
        if fn_m is None:
            continue
        ignored = re.search(r"#\s*\[\s*ignore", tail[: fn_m.start()]) is not None
        span = block_span(masked, m.end() + fn_m.end())
        if span is None:
            continue
        open_i, close_i = span
        tests.append(
            {
                "file": path,
                "lang": "rust",
                "kind": "case",
                "name": fn_m.group("name"),
                "line": idx.line_of(m.start()),
                "disabled": ignored,
                "disabled_marker": "#[ignore]" if ignored else None,
                "focused": False,
                "body": text[open_i : close_i + 1],
                "masked_body": masked[open_i : close_i + 1],
                "span": (open_i, close_i),
                "body_start_line": idx.line_of(open_i),
                "end_line": idx.line_of(close_i),
            }
        )
    return tests


def count(pattern: str, body: str) -> int:
    return len(re.findall(pattern, body))


def collect_deps(lang: str, masked_body: str) -> list[dict]:
    deps: list[dict] = []
    for kind, pattern in DEP_PATTERNS[lang]:
        hits = re.findall(pattern, masked_body)
        if not hits:
            continue
        sample = re.search(pattern, masked_body)
        deps.append(
            {
                "kind": kind,
                "occurrences": len(hits),
                "evidence": (sample.group(0).strip() if sample else pattern)[:60],
            }
        )
    return deps


def module_scope_entry(text: str, masked: str, path: str, extracted: list[dict]) -> dict | None:
    """テスト・フックの本文を除いたモジュールスコープを 1 件の観測単位として返す。

    DB クライアントやサーバ起動はファイル先頭で 1 度だけ作られることが多く、
    テスト本文だけを見ると「外部依存なし」に見えてしまう。
    """
    remaining = list(masked)
    for t in extracted:
        span = t.get("span")
        if not span:
            continue
        for i in range(span[0], min(span[1] + 1, len(remaining))):
            if remaining[i] != "\n":
                remaining[i] = " "
    module_masked = "".join(remaining)
    lang = detect_lang(path) or "ts"
    if lang == "rust" and declared_level(path, lang) != "integration":
        # `#[cfg(test)]` のインラインテストでは、モジュールスコープに本番コードが
        # 同居する。その依存はテストの準備ではないため対象にしない
        return None
    if not collect_deps(lang, module_masked):
        return None
    return {
        "file": path,
        "lang": lang,
        "kind": "module",
        "name": "(モジュールスコープ)",
        "line": 1,
        "disabled": False,
        "disabled_marker": None,
        "focused": False,
        "body": text,
        "masked_body": module_masked,
        "span": None,
        "body_start_line": 1,
        "end_line": LineIndex(text).line_of(len(text) - 1) if text else 1,
    }


def analyze(test: dict) -> dict:
    lang = test["lang"]
    masked_body = test["masked_body"]
    total = count(ASSERT_PATTERNS[lang], masked_body)
    weak = count(WEAK_PATTERNS[lang], masked_body)
    mock = count(MOCK_ASSERT_PATTERNS[lang], masked_body)
    normalized = re.sub(r"\s+", "", masked_body)
    return {
        "assertions": {"total": total, "weak": weak, "mock": mock},
        "deps": collect_deps(lang, masked_body),
        "loc": test["end_line"] - test["body_start_line"] + 1,
        "body_hash": hashlib.sha1(normalized.encode()).hexdigest()[:12] if len(normalized) > 40 else None,
    }


def build_findings(tests: list[dict]) -> list[dict]:
    findings: list[dict] = []

    def add(kind: str, t: dict, evidence: str, detail: str) -> None:
        findings.append(
            {
                "kind": kind,
                "severity_hint": SEVERITY_HINT[kind],
                "location": f"{t['file']}:{t['line']}",
                "test": t["name"],
                "declared_level": t["declared_level"],
                "evidence": evidence,
                "detail": detail,
            }
        )

    by_hash: dict[str, list[dict]] = {}
    by_name: dict[tuple[str, str], list[dict]] = {}

    for t in tests:
        a = t["analysis"]
        if t["focused"]:
            add("focused_test", t, "focused marker (.only / fit / fdescribe)",
                "コミットされた focused マーカーは同一ファイルの他テストの実行を止める。"
                "無効化と同じ影響を、無効化として見えない形で持つ")
        if t["disabled"]:
            add("disabled_test", t, t["disabled_marker"] or "disabled",
                "無効化されているため回帰を検出しない。無効化の理由と復帰条件が必要")
        if t["kind"] == "suite":
            # スイートは検証単位ではない。配下テストの検証内容を集計すると
            # 同じ事実がスイートとケースで二重に指摘される
            continue
        if t["kind"] in ("hook", "module"):
            # フックとモジュールスコープは検証を持たないのが正常。外部依存だけを見る。
            # 無効化スイート配下のフックは実行されないため、ケースと同様に抑制する
            if a["deps"] and not t["disabled"]:
                kinds = ", ".join(f"{d['kind']}({d['evidence']})" for d in a["deps"])
                kind = "level_mismatch" if t["declared_level"] == "unit" else "external_dependency"
                where = "準備フック" if t["kind"] == "hook" else "ファイルスコープ（初期化またはヘルパー定義）"
                add(kind, t, kinds,
                    f"テスト本文ではなく{where}が外部依存を持つ。"
                    "同じファイルの全テストが実行環境の状態に依存しうる")
            continue
        # 無効化済みテストの検証内容は指摘しない（実行されていないため、
        # 検証の弱さは「今そこにあるリスク」ではなく無効化の側の問題になる）
        if not t["disabled"]:
            tot = a["assertions"]["total"]
            weak = a["assertions"]["weak"]
            mock = a["assertions"]["mock"]
            if tot == 0:
                add("no_assertion", t, f"assert/expect 0 件 (本文 {a['loc']} 行)",
                    "実行はされるが結果を検証していないため、例外が出ない限り常に通る")
            else:
                if weak == tot:
                    add("weak_assertion_only", t, f"弱い検証のみ {weak}/{tot} 件",
                        "存在確認や真偽確認だけで、値・状態の正しさを固定していない")
                if mock >= tot:
                    add("mock_only_assertion", t, f"モック呼び出し検証のみ {mock}/{tot} 件",
                        "呼び出し手順の記録に一致するだけで、出力や副作用の結果を検証していない")

        if a["deps"]:
            kinds = ", ".join(f"{d['kind']}({d['evidence']})" for d in a["deps"])
            if t["declared_level"] == "unit":
                add("level_mismatch", t, kinds,
                    "単体テストとして配置されているが外部依存またはアプリ起動を伴う。分類と実体が乖離している")
            else:
                add("external_dependency", t, kinds,
                    "外部依存があるため実行環境の状態で結果が変わりうる。固定化されているか確認が必要")

        if a["body_hash"]:
            by_hash.setdefault(a["body_hash"], []).append(t)
        by_name.setdefault((t["file"], t["name"]), []).append(t)

    for group in by_hash.values():
        if len(group) < 2:
            continue
        head = group[0]
        others = ", ".join(f"{g['file']}:{g['line']}" for g in group[1:])
        add("duplicate_test_body", head, f"同一本文: {others}",
            "同じ検証が複数存在する。片方が意図した別条件を書き損ねている可能性がある")

    for (file, name), group in by_name.items():
        if len(group) < 2 or name == "(名前未取得)":
            continue
        add("duplicate_test_name", group[0], f"同名テスト {len(group)} 件 in {file}",
            "同名テストは結果の突き合わせを困難にし、片方が意図せず上書き・見落としされる")

    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument(
        "--targets",
        help="changed_targets.py の出力。changed_test_files と candidate_tests を対象に加える",
    )
    ap.add_argument("--out")
    ap.add_argument("--exclude", action="append", default=[])
    args = ap.parse_args()

    paths = list(args.paths)
    if args.targets:
        targets = load_json(args.targets)
        paths.extend(targets.get("changed_test_files", []))
        paths.extend(
            c["file"] for t in targets.get("targets", []) for c in t.get("candidate_tests", [])
        )
    paths = [p for p in dict.fromkeys(paths) if Path(p).exists()]
    if not paths:
        raise SystemExit("対象パスがありません。paths か --targets を指定してください")

    files = iter_target_files(paths, args.exclude)
    tests: list[dict] = []
    for f in files:
        lang = detect_lang(f)
        if lang is None:
            continue
        text = read_text(f)
        masked = mask_source(text, lang)
        extracted = extract_ts_tests(text, masked, f) if lang == "ts" else extract_rust_tests(text, masked, f)
        module_entry = module_scope_entry(text, masked, f, extracted)
        for t in extracted + ([module_entry] if module_entry else []):
            t["declared_level"] = declared_level(f, lang)
            t["analysis"] = analyze(t)
            tests.append(t)

    findings = build_findings(tests)
    public_tests = [
        {
            "file": t["file"],
            "line": t["line"],
            "name": t["name"],
            "declared_level": t["declared_level"],
            "disabled": t["disabled"],
            "focused": t["focused"],
            "loc": t["analysis"]["loc"],
            "assertions": t["analysis"]["assertions"],
            "deps": [d["kind"] for d in t["analysis"]["deps"]],
        }
        for t in tests
    ]
    summary: dict[str, int] = {"files": len(files), "tests": len(tests)}
    for f in findings:
        summary[f["kind"]] = summary.get(f["kind"], 0) + 1
    dump({"summary": summary, "findings": findings, "tests": public_tests}, args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
