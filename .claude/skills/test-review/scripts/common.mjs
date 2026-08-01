#!/usr/bin/env node
// test-review スクリプト群の共通処理。
//
// 方針: 文字列リテラルとコメントを同じ長さの空白へ置換した「マスク済みテキスト」に対して
// パターン検索・波括弧対応を行う。これにより文字列内の "fetch" やコメント内の "it.skip" を
// 検出結果に混入させない。オフセットは元テキストと一致するため行番号はそのまま逆算できる。
//
// オフセットの単位は UTF-16 コード単位（JS の文字列インデックス）で統一する。maskSource /
// LineIndex / 各 span は互いのオフセットを共有するため、単位が一貫していれば行番号は正しい。

import { spawnSync } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { parseArgs as nodeParseArgs } from "node:util";

export const TS_EXT = new Set([".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs", ".mts", ".cts"]);
export const RUST_EXT = new Set([".rs"]);

export function detectLang(filePath) {
  const suffix = path.extname(filePath);
  if (TS_EXT.has(suffix)) {
    return "ts";
  }
  if (RUST_EXT.has(suffix)) {
    return "rust";
  }
  return null;
}

const QUOTE_STATE = { "'": "sq", '"': "dq", "`": "tpl" };
const STATE_QUOTE = { sq: "'", dq: '"', tpl: "`" };

/** コメントと文字列リテラルを空白へ置換する（長さと改行位置は保持）。 */
export function maskSource(text, lang) {
  const out = text.split("");
  let i = 0;
  const n = text.length;
  let state = "code";
  let rawHashes = 0;
  let blockDepth = 0;

  const blank = (idx) => {
    if (out[idx] !== "\n") {
      out[idx] = " ";
    }
  };

  while (i < n) {
    const ch = text[i];
    const nxt = i + 1 < n ? text[i + 1] : "";
    if (state === "code") {
      if (ch === "/" && nxt === "/") {
        state = "line";
        i += 2;
        blank(i - 2);
        blank(i - 1);
        continue;
      }
      if (ch === "/" && nxt === "*") {
        state = "block";
        blockDepth = 1;
        i += 2;
        blank(i - 2);
        blank(i - 1);
        continue;
      }
      if (lang === "rust" && ch === "r" && (nxt === '"' || nxt === "#")) {
        let j = i + 1;
        let hashes = 0;
        while (j < n && text[j] === "#") {
          hashes += 1;
          j += 1;
        }
        if (j < n && text[j] === '"') {
          rawHashes = hashes;
          for (let k = i; k <= j; k += 1) {
            blank(k);
          }
          state = "raw";
          i = j + 1;
          continue;
        }
      }
      if (lang === "rust" && ch === "'") {
        // Rust の `'a` はライフタイムで閉じ引用符を持たない。char リテラル
        // （`'x'` `'\n'`）だけを文字列として扱わないと、以降のコード全体が
        // 空白化されて検出が崩壊する。
        if (text.slice(i + 1, i + 2) === "\\") {
          const end = text.indexOf("'", i + 2);
          // `'\u{10FFFF}'` までを char リテラルとして許容する
          if (end >= 0 && end <= i + 12) {
            for (let k = i; k <= end; k += 1) {
              blank(k);
            }
            i = end + 1;
            continue;
          }
        } else if (text.slice(i + 2, i + 3) === "'") {
          for (let k = i; k < i + 3; k += 1) {
            blank(k);
          }
          i += 3;
          continue;
        }
        i += 1;
        continue;
      }
      if (ch === "'" || ch === '"' || (lang === "ts" && ch === "`")) {
        state = QUOTE_STATE[ch];
        blank(i);
        i += 1;
        continue;
      }
      i += 1;
      continue;
    }

    if (state === "line") {
      if (ch === "\n") {
        state = "code";
      } else {
        blank(i);
      }
      i += 1;
      continue;
    }

    if (state === "block") {
      blank(i);
      // Rust のブロックコメントは入れ子が合法なので深さを数える。
      // 最初の `*/` で復帰すると、コメント内のコードがマスクされずに残る
      if (lang === "rust" && ch === "/" && nxt === "*") {
        blank(i + 1);
        blockDepth += 1;
        i += 2;
        continue;
      }
      if (ch === "*" && nxt === "/") {
        blank(i + 1);
        blockDepth -= 1;
        i += 2;
        if (blockDepth === 0) {
          state = "code";
        }
        continue;
      }
      i += 1;
      continue;
    }

    if (state === "raw") {
      if (ch === '"') {
        let j = i + 1;
        let hashes = 0;
        while (j < n && text[j] === "#" && hashes < rawHashes) {
          hashes += 1;
          j += 1;
        }
        if (hashes === rawHashes) {
          for (let k = i; k < j; k += 1) {
            blank(k);
          }
          state = "code";
          i = j;
          continue;
        }
      }
      blank(i);
      i += 1;
      continue;
    }

    // sq / dq / tpl
    const quote = STATE_QUOTE[state];
    if (ch === "\\") {
      blank(i);
      if (i + 1 < n) {
        blank(i + 1);
      }
      i += 2;
      continue;
    }
    if (ch === quote) {
      blank(i);
      state = "code";
      i += 1;
      continue;
    }
    blank(i);
    i += 1;
  }

  return out.join("");
}

/** start 以降で最初の `{` からの対応閉じ括弧までの [open, close] を返す。 */
export function blockSpan(masked, start) {
  const openIdx = masked.indexOf("{", start);
  if (openIdx < 0) {
    return null;
  }
  let depth = 0;
  for (let i = openIdx; i < masked.length; i += 1) {
    if (masked[i] === "{") {
      depth += 1;
    } else if (masked[i] === "}") {
      depth -= 1;
      if (depth === 0) {
        return [openIdx, i];
      }
    }
  }
  return null;
}

/** 文字オフセット → 行番号（1始まり）の変換。 */
export class LineIndex {
  constructor(text) {
    this.starts = [0];
    for (let i = text.indexOf("\n"); i >= 0; i = text.indexOf("\n", i + 1)) {
      this.starts.push(i + 1);
    }
  }

  lineOf(offset) {
    let lo = 0;
    let hi = this.starts.length - 1;
    while (lo < hi) {
      const mid = Math.floor((lo + hi + 1) / 2);
      if (this.starts[mid] <= offset) {
        lo = mid;
      } else {
        hi = mid - 1;
      }
    }
    return lo + 1;
  }
}

export function git(args, cwd = undefined) {
  const proc = spawnSync("git", args, { cwd, encoding: "utf8" });
  if (proc.status !== 0) {
    throw new Error(`git ${args.join(" ")} failed: ${(proc.stderr ?? "").trim()}`);
  }
  return proc.stdout;
}

export function readText(filePath) {
  // `Path.read_text()` は universal newlines で `\r\n` `\r` を `\n` へ潰す。潰さないと
  // CRLF / CR のファイルで行番号とオフセットが移植元とずれる
  return fs.readFileSync(filePath, "utf8").replace(/\r\n|\r/g, "\n");
}

export function dump(obj, outPath) {
  const text = JSON.stringify(obj, null, 2);
  if (outPath) {
    fs.mkdirSync(path.dirname(outPath), { recursive: true });
    fs.writeFileSync(outPath, `${text}\n`);
    process.stderr.write(`${outPath}\n`);
  } else {
    console.log(text);
  }
}

export function loadJson(filePath) {
  return JSON.parse(readText(filePath));
}

// 単発検索専用。g フラグを付けると lastIndex が持ち越されて結果が変わる
const TEST_PATH_RE = /(\.test\.|\.spec\.|(^|\/)tests?\/|(^|\/)__tests__\/|(^|\/)spec\/|_test\.)/i;

export function looksLikeTestPath(filePath) {
  return TEST_PATH_RE.test(filePath);
}

/**
 * パスから宣言上のテストレベルを推定する（unit / integration / e2e / unknown）。
 *
 * 推定であり宣言そのものではない。TypeScript では `tests/` `__tests__/` に単体と統合が
 * 混在する規約が一般的で、拡張子だけで unit と断定すると正当な統合テストを
 * 「分類乖離」と誤って報告する。判別材料が無い場合は unknown を返す。
 */
export function declaredLevel(filePath, lang) {
  const low = filePath.toLowerCase();
  if (/(e2e|end-to-end|endtoend|playwright|cypress)/.test(low)) {
    return "e2e";
  }
  if (/(integration|functional|acceptance)/.test(low)) {
    return "integration";
  }
  if (lang === "rust") {
    // Cargo の tests/ は結合テスト用ディレクトリ、それ以外（#[cfg(test)]）は単体
    return /(^|\/)tests\//.test(low) ? "integration" : "unit";
  }
  if (/(^|\/)unit(s)?(\/|\.)/.test(low)) {
    return "unit";
  }
  if (/(^|\/)(tests?|__tests__|spec)\//.test(low)) {
    return "unknown";
  }
  if (/\.(test|spec)\./.test(low)) {
    return "unit";
  }
  return "unknown";
}

// ---------------------------------------------------------------------------
// Python 互換ヘルパ。移植元が標準ライブラリで済ませていた処理を、
// 挙動を合わせた形で用意する（下記の各コメントが「なぜ素朴な実装では駄目か」を示す）
// ---------------------------------------------------------------------------

/** エラー終了の要求。`runMain()` だけが捕捉し、stderr 出力と終了コードへ翻訳する。 */
class ExitError extends Error {
  constructor(message, code) {
    super(message);
    this.code = code;
  }
}

/** `raise SystemExit("...")` 相当。呼び出し元へは戻らず、`runMain()` が stderr 1 行 + 終了コード 1 にする。 */
export function fail(message) {
  throw new ExitError(message, 1);
}

/**
 * `raise SystemExit(main())` 相当。`main()` の戻り値を終了コードとし、`fail()` /
 * 引数解析エラーによる中断を stderr 1 行 + 終了コードへ翻訳する。
 *
 * `process.exit()` を使ってはいけない。stdout がパイプ・ファイル宛のとき `console.log` の
 * 書き込みは非同期に流れるため、`exit()` はキューに残った分を捨てる。例外で `main()` を
 * 抜けてから `process.exitCode` を立てれば、出力済みのバイト列は Node の通常終了時に
 * 必ず flush される。エラー検出が stdout への出力より前か後かに関係なく成り立つので、
 * 呼び出し順序についての不変条件を要求しない。
 *
 * `ExitError` 以外は握らずに投げ直す。Python 版が想定外の例外でトレースバックを出して
 * 終了コード 1 になるのに合わせる。
 */
export function runMain(main) {
  try {
    process.exitCode = main();
  } catch (err) {
    if (!(err instanceof ExitError)) {
      throw err;
    }
    process.stderr.write(`${err.message}\n`);
    process.exitCode = err.code;
  }
}

/** `re.escape` 相当。動的に組む正規表現へ埋める識別子・パスを無害化する。 */
export function reEscape(text) {
  return text.replace(/[.*+?^${}()|[\]\\/-]/g, "\\$&");
}

/**
 * `sorted()` 相当。コードポイント順で新しい配列を返す。
 *
 * localeCompare を使ってはいけない（大文字小文字や記号の順序がロケール依存になり、
 * Python の比較と食い違う）。
 */
export function sortStrings(values) {
  return [...values].sort((a, b) => (a < b ? -1 : a > b ? 1 : 0));
}

const LINE_BOUNDARY_RE = /\r\n|[\n\r\v\f\x1c-\x1e\x85\u2028\u2029]/;

/**
 * `str.splitlines()` 相当。
 *
 * `split("\n")` では一致しない。Python は `\r` `\r\n` などでも分割し、
 * 末尾の改行で空要素を作らない（`"a\n".splitlines() == ["a"]`）。
 */
export function splitLines(text) {
  const lines = text.split(LINE_BOUNDARY_RE);
  if (lines[lines.length - 1] === "") {
    lines.pop();
  }
  return lines;
}

/** `str(Path(raw))` 相当。空要素と `.` を落とす（`"src/"` → `"src"`、`""` → `"."`）。 */
export function pyPath(raw) {
  const parts = raw.split("/").filter((part) => part !== "" && part !== ".");
  if (raw.startsWith("/")) {
    return `/${parts.join("/")}`;
  }
  return parts.length > 0 ? parts.join("/") : ".";
}

/**
 * `Path(root).rglob("*")` のうちファイルだけを返す（`str()` 済み・名前昇順）。
 *
 * `readdirSync(recursive: true)` を使わない理由は 2 つ。`Dirent.isFile()` は
 * シンボリックリンクを追わないため `Path.is_file()` と判定が食い違う。また走査順が
 * 呼び出し側の件数打ち切りに効くため、名前昇順に固定して決定的にする。
 */
export function walkFiles(root) {
  const found = [];
  const visit = (dir) => {
    let entries;
    try {
      entries = fs.readdirSync(dir, { withFileTypes: true });
    } catch {
      return;
    }
    entries.sort((a, b) => (a.name < b.name ? -1 : a.name > b.name ? 1 : 0));
    for (const entry of entries) {
      const child = dir === "." ? entry.name : `${dir}/${entry.name}`;
      if (entry.isDirectory()) {
        visit(child);
        continue;
      }
      // リンク先を追って判定する（`Path.is_file()` に合わせる）。
      // ディレクトリへのリンクは rglob が辿らないので、ここでも降りない
      try {
        if (fs.statSync(child).isFile()) {
          found.push(child);
        }
      } catch {
        // 壊れたリンクや権限不足は rglob 同様に無視する
      }
    }
  };
  visit(pyPath(root));
  return found;
}

const optionNameOf = (key) => key.replace(/[A-Z]/g, (c) => `-${c.toLowerCase()}`);

/**
 * `argparse` 相当。spec は `{ キー名: { append?, type? , default? } }`。
 * キー名の camelCase はオプション名へ変換する（`slowThresholdMs` → `--slow-threshold-ms`）。
 *
 * 戻り値は spec の各キーと `positionals`。未指定の単一値オプションは Python の
 * `None` に合わせて `null`、`append` は空配列になる。
 * 解析失敗は argparse と同じ終了コード 2（usage 文面は再現しない）。中断の方法は
 * `fail()` と同じく例外で、`runMain()` が終了コードへ翻訳する。
 */
export function parseArgs(argv, spec) {
  const entries = Object.entries(spec).map(([key, opt]) => [key, optionNameOf(key), opt]);
  const options = {};
  for (const [, name, opt] of entries) {
    options[name] = { type: "string", multiple: Boolean(opt.append) };
  }

  let parsed;
  try {
    parsed = nodeParseArgs({ args: argv, options, allowPositionals: true, strict: true });
  } catch (err) {
    throw new ExitError(err.message, 2);
  }

  const result = { positionals: parsed.positionals };
  for (const [key, name, opt] of entries) {
    const raw = parsed.values[name];
    if (raw === undefined) {
      result[key] = opt.append ? [] : (opt.default ?? null);
      continue;
    }
    if (opt.type !== "float") {
      result[key] = raw;
      continue;
    }
    const value = Number(raw);
    if (!Number.isFinite(value)) {
      throw new ExitError(`argument --${name}: invalid float value: '${raw}'`, 2);
    }
    result[key] = value;
  }
  return result;
}
