#!/usr/bin/env python3
"""変更コード側の検証対象候補を列挙する（TypeScript/JavaScript, Rust）。

変更行を含む関数を特定し、その関数内の分岐・例外経路・境界値候補と、
対応しそうなテストファイルの有無を機械的に出力する。
「テストが足りない」という判断は行わず、判断材料だけを並べる。

使い方:
    # 変更差分モード（既定）
    python3 changed_targets.py --out targets.json [--base origin/main]
    # パス指定モード
    python3 changed_targets.py src/billing --out targets.json
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import (  # noqa: E402
    LineIndex,
    block_span,
    detect_lang,
    dump,
    git,
    looks_like_test_path,
    mask_source,
    read_text,
)

SKIP_DIRS = {"node_modules", ".git", "target", "dist", "build", ".next", "coverage", "vendor"}

# (パターン, 本体の探し方) の組。"signature" は引数リストの対応閉じ括弧を跨いでから本体 `{` を探す。
# 型注釈に含まれる `{`（例: `(items: { price: number }[]): { ok: boolean } {`）を本体と誤認しないため。
TS_FN_PATTERNS = [
    (re.compile(r"\b(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(?P<name>\w+)\s*(?=\()"), "signature"),
    (re.compile(r"\b(?:export\s+)?(?:const|let|var)\s+(?P<name>\w+)\s*(?::[^=;\n]+)?=\s*(?:async\s*)?(?:function\b[^(]*)?\s*(?=\()"), "signature"),
    (re.compile(r"^[ \t]*(?:(?:public|private|protected|static|readonly|override|async|get|set|\*)[ \t]+)*(?P<name>[A-Za-z_$][\w$]*)[ \t]*(?=\()", re.MULTILINE), "signature"),
]
RUST_FN_PATTERN = re.compile(r"\b(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:const\s+|unsafe\s+|extern\s+\"[^\"]*\"\s+)*fn\s+(?P<name>\w+)")

# 制御構文・呼び出しを関数定義と誤認しないための除外語
TS_NOT_FUNCTION_NAMES = {
    "if", "for", "while", "switch", "catch", "do", "else", "return", "typeof", "await",
    "function", "new", "throw", "yield", "import", "export", "case", "delete", "void",
    "describe", "it", "test", "expect", "beforeEach", "afterEach", "beforeAll", "afterAll",
}

BRANCH_PATTERNS = {
    "ts": r"\bif\s*\(|\belse\b|\bswitch\s*\(|\bcase\b|\bwhile\s*\(|\bfor\s*\(|\?\?|\?\.|&&|\|\||\?[^:]{0,80}:",
    "rust": r"\bif\s+|\belse\b|\bmatch\s+|\bwhile\s+|\bfor\s+|\bloop\b|&&|\|\||\.unwrap_or",
}
ERROR_PATTERNS = {
    "ts": r"\btry\s*\{|\bcatch\s*\(|\bthrow\b|\.catch\s*\(|Promise\.reject|\bfinally\s*\{",
    "rust": r"\bResult<|\bErr\s*\(|\?\s*;|\bpanic!|\.unwrap\s*\(|\.expect\s*\(|\bbail!|\banyhow!",
}
BOUNDARY_PATTERNS = {
    "ts": r"===?\s*0\b|<=|>=|<\s|>\s|\.length\b|\bnull\b|\bundefined\b|\bNaN\b|Number\.(MAX|MIN)\w*|\bslice\s*\(|\bisEmpty\b|\.trim\s*\(\s*\)\s*===",
    "rust": r"==\s*0\b|<=|>=|\.len\s*\(\s*\)|\bNone\b|\bis_empty\s*\(|\bsaturating_|\bchecked_|\b(u|i)(8|16|32|64)::MAX\b|\.first\s*\(|\.last\s*\(",
}


def resolve_base(explicit: str | None) -> str:
    if explicit:
        return explicit
    for candidate in ("origin/HEAD", "origin/main", "origin/master", "main", "master"):
        try:
            return git("merge-base", "HEAD", candidate).strip()
        except RuntimeError:
            continue
    raise SystemExit(
        "変更差分の基点を特定できません。--base <ref> で明示してください（例: --base origin/main）"
    )


def changed_ranges(base: str) -> dict[str, list[tuple[int, int]]]:
    diff = git("diff", "--unified=0", "--no-color", "--diff-filter=ACMR", f"{base}...HEAD")
    result: dict[str, list[tuple[int, int]]] = {}
    current: str | None = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            current = line[6:]
            result.setdefault(current, [])
        elif line.startswith("@@") and current:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if m:
                start = int(m.group(1))
                length = int(m.group(2) or 1)
                if length > 0:
                    result[current].append((start, start + length - 1))
    return {k: v for k, v in result.items() if v}


def enumerate_paths(paths: list[str]) -> dict[str, list[tuple[int, int]]]:
    result: dict[str, list[tuple[int, int]]] = {}
    missing = [p for p in paths if not Path(p).exists()]
    if missing:
        # 存在しないパスを黙って空結果にすると、typo が「対象なし＝指摘なし」に化ける
        raise SystemExit(f"指定パスが存在しません: {', '.join(missing)}")
    for raw in paths:
        p = Path(raw)
        candidates = [p] if p.is_file() else [c for c in p.rglob("*") if c.is_file()]
        for c in candidates:
            if SKIP_DIRS & set(c.parts) or detect_lang(str(c)) is None:
                continue
            lines = read_text(str(c)).count("\n") + 1
            result[str(c)] = [(1, lines)]
    return result


def paren_close(masked: str, start: int) -> int | None:
    open_idx = masked.find("(", start)
    if open_idx < 0:
        return None
    depth = 0
    for i in range(open_idx, len(masked)):
        if masked[i] == "(":
            depth += 1
        elif masked[i] == ")":
            depth -= 1
            if depth == 0:
                return i
    return None


def body_span_after_signature(masked: str, close_paren: int) -> tuple[int, int] | None:
    """引数リストの後ろから関数本体の `{` を探す。

    戻り値型の位置に現れる型リテラル（`): { ok: boolean } {`）は、閉じ括弧の直後に
    さらに `{`・`|`・`&`・`[`・`=>` が続くことで見分けられるため、その場合は次の候補へ進む。
    """
    cursor = close_paren
    for _ in range(4):
        span = block_span(masked, cursor)
        if span is None:
            return None
        open_i, close_i = span
        gap = masked[cursor:open_i]
        if ";" in gap or gap.count("=") > 1 or len(gap) > 120:
            return None  # 関数定義ではない（式本体のアロー関数や、文の区切りを跨いだ）
        tail = masked[close_i + 1 : close_i + 8].lstrip()
        if tail[:1] in ("{", "|", "&", "[") or tail[:2] == "=>":
            cursor = close_i + 1
            continue
        return span
    return None


def rust_test_mod_ranges(masked: str, idx: LineIndex) -> list[tuple[int, int]]:
    """`#[cfg(test)] mod ... { }` の行範囲。テスト関数を検証対象として数えないために使う。"""
    ranges: list[tuple[int, int]] = []
    for m in re.finditer(r"#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]", masked):
        span = block_span(masked, m.end())
        if span:
            ranges.append((idx.line_of(span[0]), idx.line_of(span[1])))
    return ranges


def function_spans(text: str, masked: str, lang: str) -> list[dict]:
    idx = LineIndex(text)
    excluded = rust_test_mod_ranges(masked, idx) if lang == "rust" else []
    spans: list[dict] = []
    patterns = TS_FN_PATTERNS if lang == "ts" else [(RUST_FN_PATTERN, "signature")]
    for pattern, _strategy in patterns:
        for m in pattern.finditer(masked):
            if lang == "ts" and m.group("name") in TS_NOT_FUNCTION_NAMES:
                continue
            close = paren_close(masked, m.end())
            if close is None:
                continue
            span = body_span_after_signature(masked, close + 1)
            if span is None:
                continue
            open_i, close_i = span
            start_line = idx.line_of(m.start())
            if any(lo <= start_line <= hi for lo, hi in excluded):
                continue
            spans.append(
                {
                    "name": m.group("name"),
                    "start_line": start_line,
                    "end_line": idx.line_of(close_i),
                    "masked_body": masked[open_i : close_i + 1],
                }
            )
    # 同名・同位置の重複（複数パターンにマッチ）を排除し、内側優先で並べる
    unique = {(s["name"], s["start_line"], s["end_line"]): s for s in spans}
    return sorted(unique.values(), key=lambda s: (s["end_line"] - s["start_line"]))


def signal_tokens(pattern: str, body: str, limit: int = 8) -> list[str]:
    seen: list[str] = []
    for m in re.finditer(pattern, body):
        token = m.group(0).strip()[:24]
        if token and token not in seen:
            seen.append(token)
        if len(seen) >= limit:
            break
    return seen


MAX_INDEXED_BYTES = 512 * 1024


def build_test_index() -> list[tuple[str, str]]:
    index: list[tuple[str, str]] = []
    for c in Path(".").rglob("*"):
        if not c.is_file() or SKIP_DIRS & set(c.parts):
            continue
        path = str(c)
        if detect_lang(path) is None or not looks_like_test_path(path):
            continue
        if c.stat().st_size > MAX_INDEXED_BYTES:
            # 生成物・スナップショット同梱の巨大テストは対応テストの推定に寄与しない
            continue
        index.append((path, read_text(path)))
    return index


def find_candidate_tests(src: str, lang: str, fn_names: list[str], index: list[tuple[str, str]]) -> list[dict]:
    stem = Path(src).stem
    # mod.rs のモジュール名は親ディレクトリ名。部分一致で "mod" を除くと models → els になる
    module = (Path(src).parent.name if stem == "mod" else stem) if lang == "rust" else stem
    candidates: list[dict] = []
    if lang == "rust" and re.search(r"#\s*\[\s*cfg\s*\(\s*test\s*\)", read_text(src)):
        candidates.append({"file": src, "reason": "同一ファイル内の #[cfg(test)] mod"})
    for path, content in index:
        if path == src:
            continue
        reason = None
        if stem and stem in Path(path).stem:
            reason = "ファイル名の対応"
        elif re.search(rf"from\s+['\"][^'\"]*{re.escape(stem)}['\"]|require\s*\(\s*['\"][^'\"]*{re.escape(stem)}", content):
            reason = "import で参照"
        elif lang == "rust" and module and re.search(rf"\b{re.escape(module)}::", content):
            reason = "モジュールパスで参照"
        elif fn_names and any(re.search(rf"\b{re.escape(n)}\s*\(", content) for n in fn_names):
            reason = "対象関数名を呼び出し"
        if reason:
            candidates.append({"file": path, "reason": reason})
    return candidates[:6]


def overlaps(span: dict, ranges: list[tuple[int, int]]) -> list[list[int]]:
    hit = []
    for start, end in ranges:
        if start <= span["end_line"] and end >= span["start_line"]:
            hit.append([max(start, span["start_line"]), min(end, span["end_line"])])
    return hit


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="*")
    ap.add_argument("--base")
    ap.add_argument("--out")
    args = ap.parse_args()

    mode = "path" if args.paths else "diff"
    base = None
    if mode == "diff":
        base = resolve_base(args.base)
        changed = changed_ranges(base)
    else:
        changed = enumerate_paths(args.paths)

    test_files = sorted(p for p in changed if looks_like_test_path(p))
    source_files = [p for p in changed if p not in set(test_files) and detect_lang(p)]

    index = build_test_index()
    targets: list[dict] = []
    for src in sorted(source_files):
        if not Path(src).exists():
            continue
        lang = detect_lang(src)
        text = read_text(src)
        masked = mask_source(text, lang)
        spans = function_spans(text, masked, lang)
        ranges = changed[src]
        # 変更行 1 行ごとに、それを含む最小の関数（= 最も内側）へ帰属させる。
        # 範囲単位で帰属させると、ファイル全体が 1 範囲になるパス指定モードで
        # 最内側の 1 関数しか対象にならない。外側の関数も併記すると同じ変更が
        # 重複して並び、重要度順の並べ替えを歪めるため、最内側のみを採る。
        attributed: dict[tuple[str, int, int], list[tuple[int, int]]] = {}
        for lo, hi in ranges:
            for line in range(lo, hi + 1):
                enclosing = next(
                    (s for s in spans if s["start_line"] <= line <= s["end_line"]), None
                )
                if enclosing is None:
                    continue
                key = (enclosing["name"], enclosing["start_line"], enclosing["end_line"])
                bucket = attributed.setdefault(key, [])
                if bucket and bucket[-1][1] == line - 1:
                    bucket[-1] = (bucket[-1][0], line)
                else:
                    bucket.append((line, line))
        matched_spans = [
            s for s in spans if (s["name"], s["start_line"], s["end_line"]) in attributed
        ]
        fn_names = [s["name"] for s in matched_spans]
        candidates = find_candidate_tests(src, lang, fn_names, index)
        covered_lines = set()
        for s in matched_spans:
            body = s["masked_body"]
            own_ranges = attributed[(s["name"], s["start_line"], s["end_line"])]
            for lo, hi in own_ranges:
                covered_lines.update(range(lo, hi + 1))
            targets.append(
                {
                    "file": src,
                    "function": s["name"],
                    "start_line": s["start_line"],
                    "end_line": s["end_line"],
                    "changed_lines": [[lo, hi] for lo, hi in own_ranges],
                    "branches": len(re.findall(BRANCH_PATTERNS[lang], body)),
                    "error_paths": signal_tokens(ERROR_PATTERNS[lang], body),
                    "boundary_candidates": signal_tokens(BOUNDARY_PATTERNS[lang], body),
                    "candidate_tests": candidates,
                    "has_candidate_test": bool(candidates),
                }
            )
        orphan = [
            [lo, hi]
            for lo, hi in ranges
            if not any(line in covered_lines for line in range(lo, hi + 1))
        ]
        if orphan:
            targets.append(
                {
                    "file": src,
                    "function": None,
                    "start_line": orphan[0][0],
                    "end_line": orphan[-1][1],
                    "changed_lines": orphan,
                    "branches": 0,
                    "error_paths": [],
                    "boundary_candidates": [],
                    "candidate_tests": candidates,
                    "has_candidate_test": bool(candidates),
                    "note": "関数外の変更（宣言・設定・型・トップレベル）",
                }
            )

    dump(
        {
            "mode": mode,
            "base": base,
            "changed_source_files": sorted(source_files),
            "changed_test_files": test_files,
            "targets": targets,
            "summary": {
                "source_files": len(source_files),
                "test_files": len(test_files),
                "targets": len(targets),
                "targets_without_candidate_test": sum(1 for t in targets if not t["has_candidate_test"]),
            },
        },
        args.out,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
