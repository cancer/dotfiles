"""test-review スクリプト群の共通処理。

方針: 文字列リテラルとコメントを同じ長さの空白へ置換した「マスク済みテキスト」に対して
パターン検索・波括弧対応を行う。これにより文字列内の "fetch" やコメント内の "it.skip" を
検出結果に混入させない。オフセットは元テキストと一致するため行番号はそのまま逆算できる。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

TS_EXT = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"}
RUST_EXT = {".rs"}


def detect_lang(path: str) -> str | None:
    suffix = Path(path).suffix
    if suffix in TS_EXT:
        return "ts"
    if suffix in RUST_EXT:
        return "rust"
    return None


def mask_source(text: str, lang: str) -> str:
    """コメントと文字列リテラルを空白へ置換する（長さと改行位置は保持）。"""
    out = list(text)
    i = 0
    n = len(text)
    state = "code"
    raw_hashes = 0
    block_depth = 0

    def blank(idx: int) -> None:
        if out[idx] != "\n":
            out[idx] = " "

    while i < n:
        ch = text[i]
        nxt = text[i + 1] if i + 1 < n else ""
        if state == "code":
            if ch == "/" and nxt == "/":
                state, i = "line", i + 2
                blank(i - 2)
                blank(i - 1)
                continue
            if ch == "/" and nxt == "*":
                state, block_depth, i = "block", 1, i + 2
                blank(i - 2)
                blank(i - 1)
                continue
            if lang == "rust" and ch == "r" and nxt in ('"', "#"):
                j = i + 1
                hashes = 0
                while j < n and text[j] == "#":
                    hashes += 1
                    j += 1
                if j < n and text[j] == '"':
                    raw_hashes = hashes
                    for k in range(i, j + 1):
                        blank(k)
                    state, i = "raw", j + 1
                    continue
            if lang == "rust" and ch == "'":
                # Rust の `'a` はライフタイムで閉じ引用符を持たない。char リテラル
                # （`'x'` `'\n'`）だけを文字列として扱わないと、以降のコード全体が
                # 空白化されて検出が崩壊する。
                if text[i + 1 : i + 2] == "\\":
                    end = text.find("'", i + 2)
                    # `'\u{10FFFF}'` までを char リテラルとして許容する
                    if 0 <= end <= i + 12:
                        for k in range(i, end + 1):
                            blank(k)
                        i = end + 1
                        continue
                elif text[i + 2 : i + 3] == "'":
                    for k in range(i, i + 3):
                        blank(k)
                    i += 3
                    continue
                i += 1
                continue
            if ch in ("'", '"') or (lang == "ts" and ch == "`"):
                state = {"'": "sq", '"': "dq", "`": "tpl"}[ch]
                blank(i)
                i += 1
                continue
            i += 1
            continue

        if state == "line":
            if ch == "\n":
                state = "code"
            else:
                blank(i)
            i += 1
            continue

        if state == "block":
            blank(i)
            # Rust のブロックコメントは入れ子が合法なので深さを数える。
            # 最初の `*/` で復帰すると、コメント内のコードがマスクされずに残る
            if lang == "rust" and ch == "/" and nxt == "*":
                blank(i + 1)
                block_depth += 1
                i += 2
                continue
            if ch == "*" and nxt == "/":
                blank(i + 1)
                block_depth -= 1
                i += 2
                if block_depth == 0:
                    state = "code"
                continue
            i += 1
            continue

        if state == "raw":
            if ch == '"':
                j = i + 1
                hashes = 0
                while j < n and text[j] == "#" and hashes < raw_hashes:
                    hashes += 1
                    j += 1
                if hashes == raw_hashes:
                    for k in range(i, j):
                        blank(k)
                    state, i = "code", j
                    continue
            blank(i)
            i += 1
            continue

        # sq / dq / tpl
        quote = {"sq": "'", "dq": '"', "tpl": "`"}[state]
        if ch == "\\":
            blank(i)
            if i + 1 < n:
                blank(i + 1)
            i += 2
            continue
        if ch == quote:
            blank(i)
            state = "code"
            i += 1
            continue
        blank(i)
        i += 1

    return "".join(out)


def block_span(masked: str, start: int) -> tuple[int, int] | None:
    """start 以降で最初の `{` からの対応閉じ括弧までの (open, close) を返す。"""
    open_idx = masked.find("{", start)
    if open_idx < 0:
        return None
    depth = 0
    for i in range(open_idx, len(masked)):
        if masked[i] == "{":
            depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0:
                return open_idx, i
    return None


class LineIndex:
    """文字オフセット → 行番号（1始まり）の変換。"""

    def __init__(self, text: str) -> None:
        self.starts = [0]
        for m in re.finditer("\n", text):
            self.starts.append(m.end())

    def line_of(self, offset: int) -> int:
        lo, hi = 0, len(self.starts) - 1
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if self.starts[mid] <= offset:
                lo = mid
            else:
                hi = mid - 1
        return lo + 1


def git(*args: str, cwd: str | None = None) -> str:
    proc = subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)} failed: {proc.stderr.strip()}")
    return proc.stdout


def read_text(path: str) -> str:
    return Path(path).read_text(encoding="utf-8", errors="replace")


def dump(obj: object, out_path: str | None) -> None:
    text = json.dumps(obj, ensure_ascii=False, indent=2)
    if out_path:
        Path(out_path).parent.mkdir(parents=True, exist_ok=True)
        Path(out_path).write_text(text + "\n", encoding="utf-8")
        print(out_path, file=sys.stderr)
    else:
        print(text)


def load_json(path: str) -> object:
    return json.loads(read_text(path))


TEST_PATH_RE = re.compile(
    r"(\.test\.|\.spec\.|(^|/)tests?/|(^|/)__tests__/|(^|/)spec/|_test\.)", re.IGNORECASE
)
def looks_like_test_path(path: str) -> bool:
    return bool(TEST_PATH_RE.search(path))


def declared_level(path: str, lang: str) -> str:
    """パスから宣言上のテストレベルを推定する（unit / integration / e2e / unknown）。

    推定であり宣言そのものではない。TypeScript では `tests/` `__tests__/` に単体と統合が
    混在する規約が一般的で、拡張子だけで unit と断定すると正当な統合テストを
    「分類乖離」と誤って報告する。判別材料が無い場合は unknown を返す。
    """
    low = path.lower()
    if re.search(r"(e2e|end-to-end|endtoend|playwright|cypress)", low):
        return "e2e"
    if re.search(r"(integration|functional|acceptance)", low):
        return "integration"
    if lang == "rust":
        # Cargo の tests/ は結合テスト用ディレクトリ、それ以外（#[cfg(test)]）は単体
        return "integration" if re.search(r"(^|/)tests/", low) else "unit"
    if re.search(r"(^|/)unit(s)?(/|\.)", low):
        return "unit"
    if re.search(r"(^|/)(tests?|__tests__|spec)/", low):
        return "unknown"
    if re.search(r"\.(test|spec)\.", low):
        return "unit"
    return "unknown"
