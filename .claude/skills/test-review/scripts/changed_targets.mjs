#!/usr/bin/env node
// 変更コード側の検証対象候補を列挙する（TypeScript/JavaScript, Rust）。
//
// 変更行を含む関数を特定し、その関数内の分岐・例外経路・境界値候補と、
// 対応しそうなテストファイルの有無を機械的に出力する。
// 「テストが足りない」という判断は行わず、判断材料だけを並べる。
//
// 使い方:
//     // 変更差分モード（既定）
//     node changed_targets.mjs --out targets.json [--base origin/main]
//     // パス指定モード
//     node changed_targets.mjs src/billing --out targets.json

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

import {
  LineIndex,
  blockSpan,
  detectLang,
  dump,
  fail,
  git,
  looksLikeTestPath,
  maskSource,
  parseArgs,
  pyPath,
  readText,
  reEscape,
  runMain,
  sortStrings,
  splitLines,
  walkFiles,
} from "./common.mjs";

const SKIP_DIRS = new Set(["node_modules", ".git", "target", "dist", "build", ".next", "coverage", "vendor"]);

// (パターン, 本体の探し方) の組。"signature" は引数リストの対応閉じ括弧を跨いでから本体 `{` を探す。
// 型注釈に含まれる `{`（例: `(items: { price: number }[]): { ok: boolean } {`）を本体と誤認しないため。
const TS_FN_PATTERNS = [
  [/\b(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s*\*?\s*(?<name>\w+)\s*(?=\()/g, "signature"],
  [/\b(?:export\s+)?(?:const|let|var)\s+(?<name>\w+)\s*(?::[^=;\n]+)?=\s*(?:async\s*)?(?:function\b[^(]*)?\s*(?=\()/g, "signature"],
  [/^[ \t]*(?:(?:public|private|protected|static|readonly|override|async|get|set|\*)[ \t]+)*(?<name>[A-Za-z_$][\w$]*)[ \t]*(?=\()/gm, "signature"],
];
const RUST_FN_PATTERN = /\b(?:pub(?:\([^)]*\))?\s+)?(?:async\s+)?(?:const\s+|unsafe\s+|extern\s+"[^"]*"\s+)*fn\s+(?<name>\w+)/g;

// 制御構文・呼び出しを関数定義と誤認しないための除外語
const TS_NOT_FUNCTION_NAMES = new Set([
  "if", "for", "while", "switch", "catch", "do", "else", "return", "typeof", "await",
  "function", "new", "throw", "yield", "import", "export", "case", "delete", "void",
  "describe", "it", "test", "expect", "beforeEach", "afterEach", "beforeAll", "afterAll",
]);

const BRANCH_PATTERNS = {
  ts: /\bif\s*\(|\belse\b|\bswitch\s*\(|\bcase\b|\bwhile\s*\(|\bfor\s*\(|\?\?|\?\.|&&|\|\||\?[^:]{0,80}:/g,
  rust: /\bif\s+|\belse\b|\bmatch\s+|\bwhile\s+|\bfor\s+|\bloop\b|&&|\|\||\.unwrap_or/g,
};
const ERROR_PATTERNS = {
  ts: /\btry\s*\{|\bcatch\s*\(|\bthrow\b|\.catch\s*\(|Promise\.reject|\bfinally\s*\{/g,
  rust: /\bResult<|\bErr\s*\(|\?\s*;|\bpanic!|\.unwrap\s*\(|\.expect\s*\(|\bbail!|\banyhow!/g,
};
const BOUNDARY_PATTERNS = {
  ts: /===?\s*0\b|<=|>=|<\s|>\s|\.length\b|\bnull\b|\bundefined\b|\bNaN\b|Number\.(MAX|MIN)\w*|\bslice\s*\(|\bisEmpty\b|\.trim\s*\(\s*\)\s*===/g,
  rust: /==\s*0\b|<=|>=|\.len\s*\(\s*\)|\bNone\b|\bis_empty\s*\(|\bsaturating_|\bchecked_|\b(u|i)(8|16|32|64)::MAX\b|\.first\s*\(|\.last\s*\(/g,
};

const isFile = (p) => {
  try {
    return fs.statSync(p).isFile();
  } catch {
    return false;
  }
};

const skipped = (p) => p.split("/").some((part) => SKIP_DIRS.has(part));

/** `str.count(needle)` 相当。 */
const countOf = (text, needle) => text.split(needle).length - 1;

function resolveBase(explicit) {
  if (explicit) {
    return explicit;
  }
  for (const candidate of ["origin/HEAD", "origin/main", "origin/master", "main", "master"]) {
    try {
      return git(["merge-base", "HEAD", candidate]).trim();
    } catch {
      continue;
    }
  }
  fail("変更差分の基点を特定できません。--base <ref> で明示してください（例: --base origin/main）");
}

function changedRanges(base) {
  const diff = git(["diff", "--unified=0", "--no-color", "--diff-filter=ACMR", `${base}...HEAD`]);
  const result = new Map();
  let current = null;
  for (const line of splitLines(diff)) {
    if (line.startsWith("+++ b/")) {
      current = line.slice(6);
      if (!result.has(current)) {
        result.set(current, []);
      }
    } else if (line.startsWith("@@") && current) {
      const m = /\+(\d+)(?:,(\d+))?/.exec(line);
      if (m) {
        const start = Number(m[1]);
        // `m[2]` が空文字列でも 1 に落とす（`??` では空文字列がそのまま残る）
        const length = m[2] ? Number(m[2]) : 1;
        if (length > 0) {
          result.get(current).push([start, start + length - 1]);
        }
      }
    }
  }
  return new Map([...result].filter(([, ranges]) => ranges.length > 0));
}

function enumeratePaths(paths) {
  const result = new Map();
  const missing = paths.filter((p) => !fs.existsSync(p));
  if (missing.length > 0) {
    // 存在しないパスを黙って空結果にすると、typo が「対象なし＝指摘なし」に化ける
    fail(`指定パスが存在しません: ${missing.join(", ")}`);
  }
  for (const raw of paths) {
    const p = pyPath(raw);
    const candidates = isFile(p) ? [p] : walkFiles(p);
    for (const c of candidates) {
      if (skipped(c) || detectLang(c) === null) {
        continue;
      }
      const lines = countOf(readText(c), "\n") + 1;
      result.set(c, [[1, lines]]);
    }
  }
  return result;
}

function parenClose(masked, start) {
  const openIdx = masked.indexOf("(", start);
  if (openIdx < 0) {
    return null;
  }
  let depth = 0;
  for (let i = openIdx; i < masked.length; i += 1) {
    if (masked[i] === "(") {
      depth += 1;
    } else if (masked[i] === ")") {
      depth -= 1;
      if (depth === 0) {
        return i;
      }
    }
  }
  return null;
}

/**
 * 引数リストの後ろから関数本体の `{` を探す。
 *
 * 戻り値型の位置に現れる型リテラル（`): { ok: boolean } {`）は、閉じ括弧の直後に
 * さらに `{`・`|`・`&`・`[`・`=>` が続くことで見分けられるため、その場合は次の候補へ進む。
 */
function bodySpanAfterSignature(masked, closeParen) {
  let cursor = closeParen;
  for (let attempt = 0; attempt < 4; attempt += 1) {
    const span = blockSpan(masked, cursor);
    if (span === null) {
      return null;
    }
    const [openI, closeI] = span;
    const gap = masked.slice(cursor, openI);
    if (gap.includes(";") || countOf(gap, "=") > 1 || gap.length > 120) {
      return null; // 関数定義ではない（式本体のアロー関数や、文の区切りを跨いだ）
    }
    const tail = masked.slice(closeI + 1, closeI + 8).trimStart();
    if (["{", "|", "&", "["].includes(tail.slice(0, 1)) || tail.slice(0, 2) === "=>") {
      cursor = closeI + 1;
      continue;
    }
    return span;
  }
  return null;
}

/** `#[cfg(test)] mod ... { }` の行範囲。テスト関数を検証対象として数えないために使う。 */
function rustTestModRanges(masked, idx) {
  const ranges = [];
  for (const m of masked.matchAll(/#\s*\[\s*cfg\s*\(\s*test\s*\)\s*\]/g)) {
    const span = blockSpan(masked, m.index + m[0].length);
    if (span) {
      ranges.push([idx.lineOf(span[0]), idx.lineOf(span[1])]);
    }
  }
  return ranges;
}

const spanKey = (span) => `${span.name} ${span.start_line} ${span.end_line}`;

function functionSpans(text, masked, lang) {
  const idx = new LineIndex(text);
  const excluded = lang === "rust" ? rustTestModRanges(masked, idx) : [];
  const spans = [];
  const patterns = lang === "ts" ? TS_FN_PATTERNS : [[RUST_FN_PATTERN, "signature"]];
  for (const [pattern] of patterns) {
    for (const m of masked.matchAll(pattern)) {
      if (lang === "ts" && TS_NOT_FUNCTION_NAMES.has(m.groups.name)) {
        continue;
      }
      const close = parenClose(masked, m.index + m[0].length);
      if (close === null) {
        continue;
      }
      const span = bodySpanAfterSignature(masked, close + 1);
      if (span === null) {
        continue;
      }
      const [openI, closeI] = span;
      const startLine = idx.lineOf(m.index);
      if (excluded.some(([lo, hi]) => lo <= startLine && startLine <= hi)) {
        continue;
      }
      spans.push({
        name: m.groups.name,
        start_line: startLine,
        end_line: idx.lineOf(closeI),
        masked_body: masked.slice(openI, closeI + 1),
      });
    }
  }
  // 同名・同位置の重複（複数パターンにマッチ）を排除し、内側優先で並べる
  const unique = new Map();
  for (const s of spans) {
    unique.set(spanKey(s), s);
  }
  return [...unique.values()].sort((a, b) => (a.end_line - a.start_line) - (b.end_line - b.start_line));
}

function signalTokens(pattern, body, limit = 8) {
  const seen = [];
  for (const m of body.matchAll(pattern)) {
    const token = m[0].trim().slice(0, 24);
    if (token && !seen.includes(token)) {
      seen.push(token);
    }
    // 打ち切り判定は append の後。順序を入れ替えると limit 到達時の件数が変わる
    if (seen.length >= limit) {
      break;
    }
  }
  return seen;
}

const MAX_INDEXED_BYTES = 512 * 1024;

function buildTestIndex() {
  const index = [];
  for (const p of walkFiles(".")) {
    if (skipped(p)) {
      continue;
    }
    if (detectLang(p) === null || !looksLikeTestPath(p)) {
      continue;
    }
    if (fs.statSync(p).size > MAX_INDEXED_BYTES) {
      // 生成物・スナップショット同梱の巨大テストは対応テストの推定に寄与しない
      continue;
    }
    index.push([p, readText(p)]);
  }
  return index;
}

/** `Path(p).stem` 相当（`"billing.test.ts"` → `"billing.test"`）。 */
const stemOf = (p) => path.basename(p, path.extname(p));

/** `Path(p).parent.name` 相当。親がルートや `.` のときは空文字列。 */
function parentName(p) {
  const parent = path.dirname(p);
  return parent === "." || parent === "/" ? "" : path.basename(parent);
}

function findCandidateTests(src, lang, fnNames, index) {
  const stem = stemOf(src);
  // mod.rs のモジュール名は親ディレクトリ名。部分一致で "mod" を除くと models → els になる
  const module = lang === "rust" ? (stem === "mod" ? parentName(src) : stem) : stem;
  const candidates = [];
  if (lang === "rust" && /#\s*\[\s*cfg\s*\(\s*test\s*\)/.test(readText(src))) {
    candidates.push({ file: src, reason: "同一ファイル内の #[cfg(test)] mod" });
  }
  for (const [p, content] of index) {
    if (p === src) {
      continue;
    }
    let reason = null;
    if (stem && stemOf(p).includes(stem)) {
      reason = "ファイル名の対応";
    } else if (new RegExp(`from\\s+['"][^'"]*${reEscape(stem)}['"]|require\\s*\\(\\s*['"][^'"]*${reEscape(stem)}`).test(content)) {
      reason = "import で参照";
    } else if (lang === "rust" && module && new RegExp(`\\b${reEscape(module)}::`).test(content)) {
      reason = "モジュールパスで参照";
    } else if (fnNames.length > 0 && fnNames.some((n) => new RegExp(`\\b${reEscape(n)}\\s*\\(`).test(content))) {
      reason = "対象関数名を呼び出し";
    }
    if (reason) {
      candidates.push({ file: p, reason });
    }
  }
  return candidates.slice(0, 6);
}

function main() {
  const args = parseArgs(process.argv.slice(2), { base: {}, out: {} });
  const paths = args.positionals;

  const mode = paths.length > 0 ? "path" : "diff";
  let base = null;
  let changed;
  if (mode === "diff") {
    base = resolveBase(args.base);
    changed = changedRanges(base);
  } else {
    changed = enumeratePaths(paths);
  }

  const testFiles = sortStrings([...changed.keys()].filter((p) => looksLikeTestPath(p)));
  const testFileSet = new Set(testFiles);
  const sourceFiles = [...changed.keys()].filter((p) => !testFileSet.has(p) && detectLang(p));

  const index = buildTestIndex();
  const targets = [];
  for (const src of sortStrings(sourceFiles)) {
    if (!fs.existsSync(src)) {
      continue;
    }
    const lang = detectLang(src);
    const text = readText(src);
    const masked = maskSource(text, lang);
    const spans = functionSpans(text, masked, lang);
    const ranges = changed.get(src);
    // 変更行 1 行ごとに、それを含む最小の関数（= 最も内側）へ帰属させる。
    // 範囲単位で帰属させると、ファイル全体が 1 範囲になるパス指定モードで
    // 最内側の 1 関数しか対象にならない。外側の関数も併記すると同じ変更が
    // 重複して並び、重要度順の並べ替えを歪めるため、最内側のみを採る。
    const attributed = new Map();
    for (const [lo, hi] of ranges) {
      for (let line = lo; line <= hi; line += 1) {
        const enclosing = spans.find((s) => s.start_line <= line && line <= s.end_line);
        if (enclosing === undefined) {
          continue;
        }
        const key = spanKey(enclosing);
        let bucket = attributed.get(key);
        if (bucket === undefined) {
          bucket = [];
          attributed.set(key, bucket);
        }
        const last = bucket[bucket.length - 1];
        if (last && last[1] === line - 1) {
          last[1] = line;
        } else {
          bucket.push([line, line]);
        }
      }
    }
    const matchedSpans = spans.filter((s) => attributed.has(spanKey(s)));
    const fnNames = matchedSpans.map((s) => s.name);
    const candidates = findCandidateTests(src, lang, fnNames, index);
    const coveredLines = new Set();
    for (const s of matchedSpans) {
      const body = s.masked_body;
      const ownRanges = attributed.get(spanKey(s));
      for (const [lo, hi] of ownRanges) {
        for (let line = lo; line <= hi; line += 1) {
          coveredLines.add(line);
        }
      }
      targets.push({
        file: src,
        function: s.name,
        start_line: s.start_line,
        end_line: s.end_line,
        changed_lines: ownRanges.map(([lo, hi]) => [lo, hi]),
        branches: [...body.matchAll(BRANCH_PATTERNS[lang])].length,
        error_paths: signalTokens(ERROR_PATTERNS[lang], body),
        boundary_candidates: signalTokens(BOUNDARY_PATTERNS[lang], body),
        candidate_tests: candidates,
        has_candidate_test: candidates.length > 0,
      });
    }
    const orphan = ranges.filter(([lo, hi]) => {
      for (let line = lo; line <= hi; line += 1) {
        if (coveredLines.has(line)) {
          return false;
        }
      }
      return true;
    }).map(([lo, hi]) => [lo, hi]);
    if (orphan.length > 0) {
      targets.push({
        file: src,
        function: null,
        start_line: orphan[0][0],
        end_line: orphan[orphan.length - 1][1],
        changed_lines: orphan,
        branches: 0,
        error_paths: [],
        boundary_candidates: [],
        candidate_tests: candidates,
        has_candidate_test: candidates.length > 0,
        note: "関数外の変更（宣言・設定・型・トップレベル）",
      });
    }
  }

  dump(
    {
      mode,
      base,
      changed_source_files: sortStrings(sourceFiles),
      changed_test_files: testFiles,
      targets,
      summary: {
        source_files: sourceFiles.length,
        test_files: testFiles.length,
        targets: targets.length,
        targets_without_candidate_test: targets.filter((t) => !t.has_candidate_test).length,
      },
    },
    args.out,
  );
  return 0;
}

// Python 版の `if __name__ == "__main__":` 相当。二点、素朴な書き方では壊れる。
// - argv[1] を realpath へ通す: 起動パスがシンボリックリンク経由でも、ESM の
//   import.meta.url は実体パスに解決されるため、揃えないとガードが常に偽になる
// - 終了は runMain() 経由: process.exit() は stdout のバッファを破棄するため、
//   --out 省略時のパイプ出力が途中で切り捨てられる（理由は common.mjs の runMain 参照）
if (process.argv[1] && pathToFileURL(fs.realpathSync(process.argv[1])).href === import.meta.url) {
  runMain(main);
}
