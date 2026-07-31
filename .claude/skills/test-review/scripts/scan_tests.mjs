#!/usr/bin/env node
// テストコードの静的スキャン（TypeScript/JavaScript, Rust）。
//
// 検出する事実だけを出力し、重要度の確定や是非の判断は行わない。
// 各 finding は必ず file:line と evidence（観測したトークン）を持つ。
//
// 使い方:
//     node scan_tests.mjs [<path>...] [--targets targets.json] [--out out.json] [--exclude PATTERN]...
//
// path はファイルでもディレクトリでもよい。--targets には changed_targets.mjs の出力を渡し、
// 変更されたテストファイルと対応テスト候補を対象に加える。ディレクトリは再帰的に走査し、
// テストファイルらしいパス（*.test.*, *.spec.*, tests/, __tests__/）と、
// `#[test]` を含む .rs を対象にする。

import fs from "node:fs";
import { pathToFileURL } from "node:url";

import {
  LineIndex,
  blockSpan,
  declaredLevel,
  detectLang,
  dump,
  fail,
  loadJson,
  looksLikeTestPath,
  maskSource,
  parseArgs,
  pyPath,
  readText,
  reEscape,
  runMain,
  sortStrings,
  walkFiles,
} from "./common.mjs";

const SKIP_DIRS = new Set(["node_modules", ".git", "target", "dist", "build", ".next", "coverage", "vendor"]);

// 外部依存シグナル。kind は指摘の分類に、pattern は evidence にそのまま載せる。
const DEP_PATTERNS = {
  ts: [
    ["network", /\bfetch\s*\(|\baxios\b|\bgot\s*\(|\bsupertest\b|\brequest\s*\(\s*app|https?\.request\s*\(|new\s+WebSocket\b|\bnock\b|\bmsw\b/g],
    ["db", /\bprisma\b|PrismaClient|@prisma\/client|\$(executeRaw|queryRaw)|\bknex\b|\bmongoose\b|\bTypeORM\b|\bdrizzle\b|\bnew\s+(Pool|Client)\s*\(|(create|get)Connection\s*\(|\bredis\b|\bDynamoDB\b/g],
    ["filesystem", /\bfs\.[a-zA-Z]|\bfs\/promises\b|readFileSync\s*\(|writeFileSync\s*\(|\bmkdtemp|os\.tmpdir\s*\(/g],
    ["time", /Date\.now\s*\(|new\s+Date\s*\(\s*\)|performance\.now\s*\(|setTimeout\s*\(|setInterval\s*\(|\bdayjs\s*\(\s*\)|\bmoment\s*\(\s*\)/g],
    ["random", /Math\.random\s*\(|crypto\.randomUUID\s*\(|randomBytes\s*\(|\buuidv4\s*\(|\bfaker\./g],
    ["app_boot", /\bapp\.listen\s*\(|createServer\s*\(|NestFactory\.|createApp\s*\(|\btestcontainers\b|startServer\s*\(|\bbuildServer\s*\(/g],
    ["browser", /\bpage\.(goto|click|fill)\s*\(|\bbrowser\.(newPage|launch)\s*\(|\bcy\.\w+\s*\(/g],
    ["process", /child_process|execSync\s*\(|\bspawn\s*\(/g],
    ["env", /process\.env\.[A-Z_]+/g],
  ],
  rust: [
    ["network", /\breqwest::|\bhyper::|TcpStream::|TcpListener::|UdpSocket::|\bwiremock\b/g],
    ["db", /\bsqlx::|\bdiesel::|tokio_postgres|\bredis::|PgPool|SqlitePool|\bmongodb::/g],
    ["filesystem", /\bstd::fs::|\bfs::(read|write|create|remove)|\btempfile::|\btempdir\s*\(|File::(open|create)\s*\(/g],
    ["time", /SystemTime::now\s*\(|Instant::now\s*\(|Utc::now\s*\(|Local::now\s*\(|thread::sleep\s*\(|tokio::time::sleep\s*\(/g],
    ["random", /\brand::|thread_rng\s*\(|\brandom\s*\(\s*\)|Uuid::new_v4\s*\(/g],
    ["app_boot", /\btestcontainers\b|\baxum::serve\b|\bactix_web::test\b|Server::bind\s*\(|\brocket::local\b/g],
    ["process", /Command::new\s*\(/g],
    ["env", /\benv::var\s*\(|\bstd::env::var\s*\(/g],
  ],
};

const ASSERT_PATTERNS = {
  ts: /\bexpect\s*\(|\bassert(?:\.\w+)?\s*\(|\.should\b|\btoMatchSnapshot\s*\(|\btoMatchInlineSnapshot\s*\(/g,
  rust: /\bassert(?:_eq|_ne|_matches)?!\s*[\(\[]|\bclaim::assert|\binsta::assert/g,
};
const WEAK_PATTERNS = {
  ts: /\.(toBeDefined|toBeUndefined|toBeTruthy|toBeFalsy|toBeNull|toBeInstanceOf|toBeTypeOf)\s*\(|expect\s*\(\s*(true|false)\s*\)\s*\.toBe\s*\(\s*(true|false)\s*\)|\.not\.toThrow\s*\(\s*\)/g,
  rust: /assert!\s*\(\s*(true|[^)]*\.is_ok\s*\(\s*\)|[^)]*\.is_some\s*\(\s*\))\s*[,)]/g,
};
const MOCK_ASSERT_PATTERNS = {
  ts: /\.(toHaveBeenCalled|toHaveBeenCalledTimes|toHaveBeenCalledWith|toHaveBeenNthCalledWith|toHaveBeenLastCalledWith|toHaveReturnedWith)\s*\(|\.mock\.(calls|results)\b|\bverify\s*\(/g,
  rust: /\.times\s*\(|\.checkpoint\s*\(|expect_\w+\s*\(\s*\)\s*\.\s*(times|returning)/g,
};

const TS_TEST_RE =
  /\b(?<fn>it|test|describe|xit|xtest|xdescribe|fit|fdescribe)\s*(?:\.\s*(?<mod>skip|only|todo|failing|concurrent|sequential|skipIf|runIf|each)\b[^(]*)?\s*\(/g;
const TS_HOOK_RE = /\b(?<fn>beforeEach|beforeAll|afterEach|afterAll)\s*\(/g;
const RUST_TEST_ATTR_RE = /#\s*\[\s*(?:tokio::|async_std::|actix_web::|rstest\b)?[\w:]*test[\w:]*\b/g;
const RUST_FN_RE = /\bfn\s+(?<name>\w+)\s*\(/;

const SEVERITY_HINT = {
  disabled_test: "high",
  focused_test: "high",
  no_assertion: "high",
  weak_assertion_only: "medium",
  mock_only_assertion: "medium",
  level_mismatch: "medium",
  duplicate_test_body: "low",
  duplicate_test_name: "medium",
  external_dependency: "low",
};

/**
 * `fnmatch.fnmatchcase` 相当のパターン照合。
 *
 * macOS では `os.path.normcase` が恒等関数なので大文字小文字を区別する。
 * glob と違い `*` は `/` にもマッチする。対応する `]` を持たない `[` はリテラル。
 */
function fnmatch(name, pattern) {
  let body = "";
  let i = 0;
  while (i < pattern.length) {
    const ch = pattern[i];
    i += 1;
    if (ch === "*") {
      body += ".*";
      continue;
    }
    if (ch === "?") {
      body += ".";
      continue;
    }
    if (ch === "[") {
      const close = pattern.indexOf("]", pattern[i] === "!" ? i + 2 : i + 1);
      if (close < 0) {
        body += "\\[";
        continue;
      }
      const seq = pattern.slice(i, close).replace(/\\/g, "\\\\");
      i = close + 1;
      body += `[${seq[0] === "!" ? `^${seq.slice(1)}` : seq}]`;
      continue;
    }
    body += reEscape(ch);
  }
  return new RegExp(`^(?:${body})$`, "s").test(name);
}

function iterTargetFiles(paths, excludes) {
  const found = [];
  for (const raw of paths) {
    const p = pyPath(raw);
    if (fs.statSync(p, { throwIfNoEntry: false })?.isFile()) {
      found.push(p);
      continue;
    }
    for (const child of walkFiles(p)) {
      if (child.split("/").some((part) => SKIP_DIRS.has(part))) {
        continue;
      }
      const lang = detectLang(child);
      if (lang === null) {
        continue;
      }
      if (looksLikeTestPath(child)) {
        found.push(child);
      } else if (lang === "rust" && readText(child).includes("#[test")) {
        found.push(child);
      }
    }
  }
  const result = [];
  for (const f of sortStrings(new Set(found))) {
    if (excludes.some((pat) => fnmatch(f, pat))) {
      continue;
    }
    if (detectLang(f)) {
      result.push(f);
    }
  }
  return result;
}

function firstStringLiteral(text, start, window = 300) {
  const m = /['"`]([^'"`\n]{0,200})['"`]/.exec(text.slice(start, start + window));
  return m ? m[1] : null;
}

function callClose(masked, openParen) {
  let depth = 0;
  for (let i = openParen; i < masked.length; i += 1) {
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
 * テスト呼び出しの引数リストの範囲 [開始, 終了] を返す。
 *
 * `it.each(table)("name", cb)` のような 2 段呼び出しでは、コールバックは 2 段目に
 * あるため範囲を 2 段目へ進める。1 段目に留まると、テーブルデータ内のアロー関数
 * （`cases.map(c => …)`）を本体と誤認する。
 */
function callArgRegion(masked, openParen) {
  const close = callClose(masked, openParen);
  if (close === null) {
    return null;
  }
  const chained = /^[ \t]*\(/.exec(masked.slice(close + 1));
  if (chained) {
    const secondOpen = close + chained[0].length;
    const secondClose = callClose(masked, secondOpen);
    if (secondClose !== null) {
      return [secondOpen + 1, secondClose];
    }
  }
  return [openParen + 1, close];
}

/**
 * 引数リスト内のコールバック本体を返す。本体を持たない呼び出しでは null。
 *
 * 探索範囲を引数リストに限るのは、`it.todo("later")` のように本体の無い呼び出しが
 * 後続テストの本体を取り込むのを、セミコロンの有無に依存せず防ぐため。
 * `{` を伴う `=>` を優先するのは、引数の分割代入（Playwright の fixture、
 * Vitest の context）が先に `{` を出す形と、データ側のアロー関数を区別するため。
 */
function callbackBodySpan(masked, argStart, argEnd) {
  const window = masked.slice(argStart, argEnd);
  const arrows = [...window.matchAll(/=>/g)].map((m) => argStart + m.index + m[0].length);
  for (const after of arrows) {
    if (masked.slice(after, argEnd).trimStart().slice(0, 1) === "{") {
      return blockSpan(masked, after);
    }
  }
  if (arrows.length > 0) {
    // 式本体のアロー関数（`it("n", (done) => done())`）。ブロックは無いが
    // テストではあるため引数リストの残りを本文として扱う。対象外にすると
    // 検証を持たないテストが集計から消える
    return [arrows[arrows.length - 1], argEnd];
  }
  const fnKw = /\bfunction\b/.exec(window);
  if (fnKw !== null) {
    const close = masked.indexOf(")", argStart + fnKw.index + fnKw[0].length);
    if (close >= 0 && close < argEnd) {
      return blockSpan(masked, close);
    }
  }
  return null;
}

function extractTsTests(text, masked, filePath) {
  const idx = new LineIndex(text);
  const tests = [];
  const disabledSuites = [];
  for (const m of masked.matchAll(TS_TEST_RE)) {
    const { fn, mod } = m.groups;
    const disabled = ["xit", "xtest", "xdescribe"].includes(fn) || ["skip", "todo"].includes(mod);
    const isContainer = ["describe", "xdescribe", "fdescribe"].includes(fn);
    const region = callArgRegion(masked, m.index + m[0].length - 1);
    if (region === null) {
      continue;
    }
    // テスト名は引数リストの先頭にある。2 段呼び出しでは 2 段目が名前を持つ
    const name = firstStringLiteral(text, region[0]) || "(名前未取得)";
    const span = callbackBodySpan(masked, region[0], region[1]);
    if (span === null) {
      // 本体が無い呼び出し。it.todo は無効化として残し、それ以外は対象外
      if (disabled && !isContainer) {
        tests.push({
          file: filePath,
          lang: "ts",
          kind: "case",
          name,
          line: idx.lineOf(m.index),
          disabled: true,
          disabled_marker: mod ? `${fn}.${mod}` : fn,
          focused: false,
          body: "",
          masked_body: "",
          span: null,
          body_start_line: idx.lineOf(m.index),
          end_line: idx.lineOf(m.index),
        });
      }
      continue;
    }
    const [openI, closeI] = span;
    if (isContainer) {
      const focusedSuite = mod === "only" || fn === "fdescribe";
      if (disabled || focusedSuite) {
        const marker = mod ? `${fn}.${mod}` : fn;
        if (disabled) {
          disabledSuites.push([idx.lineOf(m.index), idx.lineOf(closeI), marker]);
        }
        tests.push({
          file: filePath,
          lang: "ts",
          kind: "suite",
          name,
          line: idx.lineOf(m.index),
          disabled,
          disabled_marker: disabled ? marker : null,
          focused: focusedSuite,
          body: text.slice(openI, closeI + 1),
          masked_body: masked.slice(openI, closeI + 1),
          span: [openI, closeI],
          body_start_line: idx.lineOf(openI),
          end_line: idx.lineOf(closeI),
        });
      }
      continue; // 有効な describe 自体は検証単位ではない
    }
    tests.push({
      file: filePath,
      lang: "ts",
      kind: "case",
      name,
      line: idx.lineOf(m.index),
      disabled,
      disabled_marker: disabled ? (mod ? `${fn}.${mod}` : fn) : null,
      focused: mod === "only" || ["fit", "fdescribe"].includes(fn),
      body: text.slice(openI, closeI + 1),
      masked_body: masked.slice(openI, closeI + 1),
      span: [openI, closeI],
      body_start_line: idx.lineOf(openI),
      end_line: idx.lineOf(closeI),
    });
  }

  // DB 接続や時刻固定の準備は beforeEach / beforeAll に置かれることが多い。
  // フックを対象外にすると、テスト本文だけを見て「外部依存なし」と読める
  for (const m of masked.matchAll(TS_HOOK_RE)) {
    const region = callArgRegion(masked, m.index + m[0].length - 1);
    const span = region ? callbackBodySpan(masked, region[0], region[1]) : null;
    if (span === null) {
      continue;
    }
    const [openI, closeI] = span;
    tests.push({
      file: filePath,
      lang: "ts",
      kind: "hook",
      name: `${m.groups.fn}()`,
      line: idx.lineOf(m.index),
      disabled: false,
      disabled_marker: null,
      focused: false,
      body: text.slice(openI, closeI + 1),
      masked_body: masked.slice(openI, closeI + 1),
      span: [openI, closeI],
      body_start_line: idx.lineOf(openI),
      end_line: idx.lineOf(closeI),
    });
  }

  // 無効化されたスイート配下のテストは実行されない。個別の検証不足として報告すると
  // 「実行されているテストの問題」と読まれるため、無効化側へ寄せる。
  for (const t of tests) {
    if (!["case", "hook"].includes(t.kind) || t.disabled) {
      continue;
    }
    const enclosing = disabledSuites.find((s) => s[0] <= t.line && t.line <= s[1]);
    if (enclosing) {
      t.disabled = true;
      t.disabled_marker = `${enclosing[2]}（上位スイート ${enclosing[0]} 行目）`;
    }
  }
  return tests;
}

function extractRustTests(text, masked, filePath) {
  const idx = new LineIndex(text);
  const tests = [];
  for (const m of masked.matchAll(RUST_TEST_ATTR_RE)) {
    const attrEnd = m.index + m[0].length;
    const tail = masked.slice(attrEnd, attrEnd + 600);
    const fnM = RUST_FN_RE.exec(tail);
    if (fnM === null) {
      continue;
    }
    const ignored = /#\s*\[\s*ignore/.test(tail.slice(0, fnM.index));
    const span = blockSpan(masked, attrEnd + fnM.index + fnM[0].length);
    if (span === null) {
      continue;
    }
    const [openI, closeI] = span;
    tests.push({
      file: filePath,
      lang: "rust",
      kind: "case",
      name: fnM.groups.name,
      line: idx.lineOf(m.index),
      disabled: ignored,
      disabled_marker: ignored ? "#[ignore]" : null,
      focused: false,
      body: text.slice(openI, closeI + 1),
      masked_body: masked.slice(openI, closeI + 1),
      span: [openI, closeI],
      body_start_line: idx.lineOf(openI),
      end_line: idx.lineOf(closeI),
    });
  }
  return tests;
}

function count(pattern, body) {
  return [...body.matchAll(pattern)].length;
}

function collectDeps(lang, maskedBody) {
  const deps = [];
  for (const [kind, pattern] of DEP_PATTERNS[lang]) {
    // 先頭の一致が re.search の結果と同じなので、matchAll 1 回で件数と evidence が揃う
    const hits = [...maskedBody.matchAll(pattern)];
    if (hits.length === 0) {
      continue;
    }
    deps.push({
      kind,
      occurrences: hits.length,
      evidence: hits[0][0].trim().slice(0, 60),
    });
  }
  return deps;
}

/**
 * テスト・フックの本文を除いたモジュールスコープを 1 件の観測単位として返す。
 *
 * DB クライアントやサーバ起動はファイル先頭で 1 度だけ作られることが多く、
 * テスト本文だけを見ると「外部依存なし」に見えてしまう。
 */
function moduleScopeEntry(text, masked, filePath, extracted) {
  const remaining = masked.split("");
  for (const t of extracted) {
    if (!t.span) {
      continue;
    }
    for (let i = t.span[0]; i < Math.min(t.span[1] + 1, remaining.length); i += 1) {
      if (remaining[i] !== "\n") {
        remaining[i] = " ";
      }
    }
  }
  const moduleMasked = remaining.join("");
  const lang = detectLang(filePath) || "ts";
  if (lang === "rust" && declaredLevel(filePath, lang) !== "integration") {
    // `#[cfg(test)]` のインラインテストでは、モジュールスコープに本番コードが
    // 同居する。その依存はテストの準備ではないため対象にしない
    return null;
  }
  if (collectDeps(lang, moduleMasked).length === 0) {
    return null;
  }
  return {
    file: filePath,
    lang,
    kind: "module",
    name: "(モジュールスコープ)",
    line: 1,
    disabled: false,
    disabled_marker: null,
    focused: false,
    body: text,
    masked_body: moduleMasked,
    span: null,
    body_start_line: 1,
    end_line: text ? new LineIndex(text).lineOf(text.length - 1) : 1,
  };
}

function analyze(test) {
  const lang = test.lang;
  const maskedBody = test.masked_body;
  const total = count(ASSERT_PATTERNS[lang], maskedBody);
  const weak = count(WEAK_PATTERNS[lang], maskedBody);
  const mock = count(MOCK_ASSERT_PATTERNS[lang], maskedBody);
  const normalized = maskedBody.replace(/\s+/g, "");
  return {
    assertions: { total, weak, mock },
    deps: collectDeps(lang, maskedBody),
    loc: test.end_line - test.body_start_line + 1,
    // 移植元は sha1 の先頭 12 桁。グループ化キーにしか使わず公開出力に現れないため、
    // 正規化済み本文そのものをキーにしてハッシュ計算を省く
    body_key: normalized.length > 40 ? normalized : null,
  };
}

function buildFindings(tests) {
  const findings = [];

  const add = (kind, t, evidence, detail) => {
    findings.push({
      kind,
      severity_hint: SEVERITY_HINT[kind],
      location: `${t.file}:${t.line}`,
      test: t.name,
      declared_level: t.declared_level,
      evidence,
      detail,
    });
  };

  // 挿入順が出力の並び順になるため Map を使う（プレーンオブジェクトは
  // 整数風のキーを数値昇順へ並べ替えてしまう）
  const byHash = new Map();
  const byName = new Map();

  for (const t of tests) {
    const a = t.analysis;
    if (t.focused) {
      add("focused_test", t, "focused marker (.only / fit / fdescribe)",
        "コミットされた focused マーカーは同一ファイルの他テストの実行を止める。" +
        "無効化と同じ影響を、無効化として見えない形で持つ");
    }
    if (t.disabled) {
      add("disabled_test", t, t.disabled_marker || "disabled",
        "無効化されているため回帰を検出しない。無効化の理由と復帰条件が必要");
    }
    if (t.kind === "suite") {
      // スイートは検証単位ではない。配下テストの検証内容を集計すると
      // 同じ事実がスイートとケースで二重に指摘される
      continue;
    }
    if (t.kind === "hook" || t.kind === "module") {
      // フックとモジュールスコープは検証を持たないのが正常。外部依存だけを見る。
      // 無効化スイート配下のフックは実行されないため、ケースと同様に抑制する
      if (a.deps.length > 0 && !t.disabled) {
        const kinds = a.deps.map((d) => `${d.kind}(${d.evidence})`).join(", ");
        const kind = t.declared_level === "unit" ? "level_mismatch" : "external_dependency";
        const where = t.kind === "hook" ? "準備フック" : "ファイルスコープ（初期化またはヘルパー定義）";
        add(kind, t, kinds,
          `テスト本文ではなく${where}が外部依存を持つ。` +
          "同じファイルの全テストが実行環境の状態に依存しうる");
      }
      continue;
    }
    // 無効化済みテストの検証内容は指摘しない（実行されていないため、
    // 検証の弱さは「今そこにあるリスク」ではなく無効化の側の問題になる）
    if (!t.disabled) {
      const tot = a.assertions.total;
      const weak = a.assertions.weak;
      const mock = a.assertions.mock;
      if (tot === 0) {
        add("no_assertion", t, `assert/expect 0 件 (本文 ${a.loc} 行)`,
          "実行はされるが結果を検証していないため、例外が出ない限り常に通る");
      } else {
        if (weak === tot) {
          add("weak_assertion_only", t, `弱い検証のみ ${weak}/${tot} 件`,
            "存在確認や真偽確認だけで、値・状態の正しさを固定していない");
        }
        if (mock >= tot) {
          add("mock_only_assertion", t, `モック呼び出し検証のみ ${mock}/${tot} 件`,
            "呼び出し手順の記録に一致するだけで、出力や副作用の結果を検証していない");
        }
      }
    }

    if (a.deps.length > 0) {
      const kinds = a.deps.map((d) => `${d.kind}(${d.evidence})`).join(", ");
      if (t.declared_level === "unit") {
        add("level_mismatch", t, kinds,
          "単体テストとして配置されているが外部依存またはアプリ起動を伴う。分類と実体が乖離している");
      } else {
        add("external_dependency", t, kinds,
          "外部依存があるため実行環境の状態で結果が変わりうる。固定化されているか確認が必要");
      }
    }

    if (a.body_key) {
      if (!byHash.has(a.body_key)) {
        byHash.set(a.body_key, []);
      }
      byHash.get(a.body_key).push(t);
    }
    // 移植元のキーはタプル `(file, name)`。パスもテスト名も含みえない NUL を区切りにして、
    // `"a b" + "c"` と `"a" + "b c"` が同じキーへ潰れるのを防ぐ
    const nameKey = `${t.file}\u0000${t.name}`;
    if (!byName.has(nameKey)) {
      byName.set(nameKey, []);
    }
    byName.get(nameKey).push(t);
  }

  for (const group of byHash.values()) {
    if (group.length < 2) {
      continue;
    }
    const head = group[0];
    const others = group.slice(1).map((g) => `${g.file}:${g.line}`).join(", ");
    add("duplicate_test_body", head, `同一本文: ${others}`,
      "同じ検証が複数存在する。片方が意図した別条件を書き損ねている可能性がある");
  }

  for (const group of byName.values()) {
    const { file, name } = group[0];
    if (group.length < 2 || name === "(名前未取得)") {
      continue;
    }
    add("duplicate_test_name", group[0], `同名テスト ${group.length} 件 in ${file}`,
      "同名テストは結果の突き合わせを困難にし、片方が意図せず上書き・見落としされる");
  }

  return findings;
}

function main() {
  const args = parseArgs(process.argv.slice(2), {
    targets: {},
    out: {},
    exclude: { append: true },
  });

  let paths = [...args.positionals];
  if (args.targets) {
    const targets = loadJson(args.targets);
    paths.push(...(targets.changed_test_files ?? []));
    for (const t of targets.targets ?? []) {
      for (const c of t.candidate_tests ?? []) {
        paths.push(c.file);
      }
    }
  }
  paths = [...new Set(paths)].filter((p) => fs.existsSync(p));
  if (paths.length === 0) {
    fail("対象パスがありません。paths か --targets を指定してください");
  }

  const files = iterTargetFiles(paths, args.exclude);
  const tests = [];
  for (const f of files) {
    const lang = detectLang(f);
    if (lang === null) {
      continue;
    }
    const text = readText(f);
    const masked = maskSource(text, lang);
    const extracted = lang === "ts" ? extractTsTests(text, masked, f) : extractRustTests(text, masked, f);
    const moduleEntry = moduleScopeEntry(text, masked, f, extracted);
    for (const t of [...extracted, ...(moduleEntry ? [moduleEntry] : [])]) {
      t.declared_level = declaredLevel(f, lang);
      t.analysis = analyze(t);
      tests.push(t);
    }
  }

  const findings = buildFindings(tests);
  const publicTests = tests.map((t) => ({
    file: t.file,
    line: t.line,
    name: t.name,
    declared_level: t.declared_level,
    disabled: t.disabled,
    focused: t.focused,
    loc: t.analysis.loc,
    assertions: t.analysis.assertions,
    deps: t.analysis.deps.map((d) => d.kind),
  }));
  const summary = { files: files.length, tests: tests.length };
  for (const f of findings) {
    summary[f.kind] = (summary[f.kind] ?? 0) + 1;
  }
  dump({ summary, findings, tests: publicTests }, args.out);
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
