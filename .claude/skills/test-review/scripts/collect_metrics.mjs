#!/usr/bin/env node
// 既存のテスト実行結果・カバレッジ・ミューテーションレポートを正規化して集計する。
//
// このスクリプトはテストを実行しない。CI などが既に出力したレポートを読むだけであり、
// 本番データや外部サービスに触れない。渡されなかった種別は "not_measured" に記録し、
// レビュー側が「未計測」と「問題なし」を混同しないようにする。
//
// 使い方:
//     node collect_metrics.mjs \
//         --test-json run1.json --test-json run2.json \
//         --nextest-json nextest.jsonl \
//         --coverage-lcov lcov.info --coverage-json coverage-final.json \
//         --mutation-json stryker.json \
//         --targets .claude/test-review/targets.json \
//         --out .claude/test-review/metrics.json
//
// レポートの生成コマンドは references/report-inputs.md を参照。

import fs from "node:fs";
import path from "node:path";
import { pathToFileURL } from "node:url";

import { dump, loadJson, parseArgs, readText, sortStrings, splitLines } from "./common.mjs";

const RELATIVE_SLOW_FLOOR_MS = 100.0;

// ---------------------------------------------------------------------------
// 数値・文字列の書式ヘルパ。
//
// 集計結果は JSON の値としてだけでなく findings の evidence 文字列にも埋め込まれる。
// 文字列に入った時点で書式の差はそのまま値の差になるため、移植元（Python）の
// 書式を再現する必要がある。
// ---------------------------------------------------------------------------

/**
 * `math.fsum` 相当（Shewchuk の完全補正加算）。
 *
 * `statistics.fmean` は `math.fsum(data) / n` で平均を出す。素朴な逐次加算では
 * 最終ビットが変わることがあり、それが JSON に載る `mean_ms` の表記差になる。
 */
function fsum(values) {
  const partials = [];
  for (const value of values) {
    let x = value;
    let i = 0;
    for (const partial of partials) {
      let y = partial;
      if (Math.abs(x) < Math.abs(y)) {
        [x, y] = [y, x];
      }
      const hi = x + y;
      const lo = y - (hi - x);
      if (lo !== 0) {
        partials[i] = lo;
        i += 1;
      }
      x = hi;
    }
    partials.length = i;
    partials.push(x);
  }
  return partials.reduce((acc, v) => acc + v, 0);
}

/** `statistics.fmean` 相当。 */
function fmean(values) {
  return fsum(values) / values.length;
}

/** `statistics.pstdev` 相当（母標準偏差。標本標準偏差ではない）。 */
function pstdev(values) {
  const mean = fmean(values);
  const squares = values.map((v) => (v - mean) * (v - mean));
  return Math.sqrt(fsum(squares) / values.length);
}

/**
 * `f"{x:.0f}"` 相当。
 *
 * Python は偶数丸め（`2.5` → `"2"`、`13.5` → `"14"`）。`toFixed(0)` は 0 から遠い側へ
 * 丸めるため一致しない。負の値が 0 に丸まる場合 Python は `"-0"` を出す。
 */
function formatFixed0(x) {
  if (!Number.isFinite(x)) {
    return Number.isNaN(x) ? "nan" : x > 0 ? "inf" : "-inf";
  }
  const floor = Math.floor(x);
  const frac = x - floor;
  let rounded;
  if (frac > 0.5) {
    rounded = floor + 1;
  } else if (frac < 0.5) {
    rounded = floor;
  } else {
    rounded = floor % 2 === 0 ? floor : floor + 1;
  }
  if (rounded === 0 && (x < 0 || Object.is(x, -0))) {
    return "-0";
  }
  // `String()` は 1e21 以上を指数表記にするが `.0f` は常に全桁を出す
  return Math.abs(rounded) >= 1e21 ? BigInt(rounded).toString() : String(rounded);
}

/**
 * `repr(float)` 相当。
 *
 * 整数値でも `.0` が付く（`80` → `"80.0"`）。指数表記への切替閾値と指数部の桁数も
 * JS の `String()` とは異なる（Python は `|x| >= 1e16` / `0 < |x| < 1e-4` で指数表記、
 * 指数部は 2 桁ゼロ埋め）。
 */
function pyReprFloat(x) {
  if (Number.isNaN(x)) {
    return "nan";
  }
  if (!Number.isFinite(x)) {
    return x > 0 ? "inf" : "-inf";
  }
  if (x === 0) {
    return Object.is(x, -0) ? "-0.0" : "0.0";
  }
  const sign = x < 0 ? "-" : "";
  const abs = Math.abs(x);
  // 引数なしの toExponential は往復可能な最短桁数を使う
  const [mantissa, exponent] = abs.toExponential().split("e");
  const exp = Number(exponent);
  if (exp <= -5 || exp >= 16) {
    const expSign = exp < 0 ? "-" : "+";
    return `${sign}${mantissa}e${expSign}${String(Math.abs(exp)).padStart(2, "0")}`;
  }
  const fixed = String(abs);
  return sign + (fixed.includes(".") ? fixed : `${fixed}.0`);
}

/**
 * `repr(str)` 相当。
 *
 * 既定はシングルクォート。値が `'` を含み `"` を含まない場合だけダブルクォートへ切り替わる。
 * 非 ASCII の非表示文字（Python の `str.isprintable()` が偽になる文字）のエスケープは
 * Unicode カテゴリ表を要するため再現しない。レポートの status 文字列が対象であり届かない。
 */
function pyReprStr(text) {
  const quote = text.includes("'") && !text.includes('"') ? '"' : "'";
  let body = "";
  for (const ch of text) {
    if (ch === "\\" || ch === quote) {
      body += `\\${ch}`;
    } else if (ch === "\n") {
      body += "\\n";
    } else if (ch === "\r") {
      body += "\\r";
    } else if (ch === "\t") {
      body += "\\t";
    } else if (ch < " " || ch === "\x7f") {
      body += `\\x${ch.codePointAt(0).toString(16).padStart(2, "0")}`;
    } else {
      body += ch;
    }
  }
  return quote + body + quote;
}

/** `repr(list[float])` 相当。 */
function pyReprFloatList(values) {
  return `[${values.map(pyReprFloat).join(", ")}]`;
}

/** `repr(list[str])` 相当。 */
function pyReprStrList(values) {
  return `[${values.map(pyReprStr).join(", ")}]`;
}

/** `dict.get(key, default)` 相当。キーが存在すれば `null` でもその値を返す。 */
function get(obj, key, fallback = null) {
  return key in obj ? obj[key] : fallback;
}

function isDict(value) {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

const byNumber = (a, b) => a - b;

// ---------------------------------------------------------------------------

/** Vitest / Jest の JSON reporter 出力（--reporter=json, --json）を読む。 */
function parseJestLike(filePath) {
  const data = loadJson(filePath);
  const records = [];
  for (const fileResult of get(data, "testResults", [])) {
    const fileName = fileResult.name || fileResult.testFilePath || "(unknown)";
    const cases = get(fileResult, "assertionResults", get(fileResult, "testResults", []));
    for (const testCase of cases) {
      const duration = get(testCase, "duration");
      // 空の failureMessages は Python では偽（`or [None]` に落ちる）が JS の [] は真
      const messages = get(testCase, "failureMessages");
      records.push({
        id: testCase.fullName || testCase.title || "(unnamed)",
        file: fileName,
        status: get(testCase, "status", "unknown"),
        duration_ms: duration === null || duration === undefined ? null : Number(duration),
        failure: Array.isArray(messages) && messages.length > 0 ? (messages[0] ?? null) : null,
        source: filePath,
      });
    }
  }
  return records;
}

/** cargo nextest --message-format libtest-json / cargo test --format json を読む。 */
function parseLibtestJsonl(filePath) {
  const STATUS = new Map([
    ["ok", "passed"],
    ["failed", "failed"],
    ["ignored", "skipped"],
  ]);
  const records = [];
  for (const raw of splitLines(readText(filePath))) {
    const line = raw.trim();
    if (!line.startsWith("{")) {
      continue;
    }
    let event;
    try {
      event = JSON.parse(line);
    } catch {
      continue;
    }
    if (get(event, "type") !== "test") {
      continue;
    }
    const kind = get(event, "event");
    if (kind === null || kind === undefined || kind === "started") {
      continue;
    }
    const execTime = get(event, "exec_time");
    records.push({
      id: get(event, "name", "(unnamed)"),
      file: get(event, "name", "").split("::")[0],
      status: STATUS.has(kind) ? STATUS.get(kind) : kind,
      duration_ms: execTime === null || execTime === undefined ? null : Number(execTime) * 1000,
      failure: get(event, "stdout"),
      source: filePath,
    });
  }
  return records;
}

function aggregateTests(records, slowThresholdMs) {
  // テスト ID は任意の文字列。プレーンオブジェクトは整数風のキーを数値昇順へ
  // 並べ替えてしまい、出力の並びが移植元と変わる
  const grouped = new Map();
  for (const r of records) {
    if (!grouped.has(r.id)) {
      grouped.set(r.id, []);
    }
    grouped.get(r.id).push(r);
  }

  const durationsAll = records.filter((r) => r.duration_ms !== null).map((r) => r.duration_ms);
  let p95 = null;
  if (durationsAll.length >= 20) {
    const ordered = [...durationsAll].sort(byNumber);
    p95 = ordered[Math.trunc(ordered.length * 0.95) - 1];
  }

  const tests = [];
  const findings = [];
  for (const [testId, group] of grouped) {
    const durations = group.filter((g) => g.duration_ms !== null).map((g) => g.duration_ms);
    const statuses = group.map((g) => g.status);
    const mean = durations.length > 0 ? fmean(durations) : null;
    const stdev = durations.length > 1 ? pstdev(durations) : 0.0;
    const entry = {
      id: testId,
      file: group[0].file,
      runs: group.length,
      statuses,
      durations_ms: durations,
      mean_ms: mean,
      stddev_ms: stdev,
      sources: sortStrings(new Set(group.map((g) => g.source))),
    };
    tests.push(entry);

    // 同一レポート内に同名テストが複数ある場合（重複テスト）は反復実行ではないため、
    // 結果や実行時間の差を不安定さの根拠にできない
    const repeatedAcrossReports = entry.sources.length >= 2;
    if (repeatedAcrossReports && new Set(statuses).size > 1) {
      findings.push({
        kind: "unstable_status",
        severity_hint: "high",
        location: `${entry.file}`,
        test: testId,
        evidence: `複数レポート間で結果が不一致: ${pyReprStrList(statuses)}（${entry.sources.join(", ")}）`,
        detail: "同一テストが実行条件によって結果を変えている。不安定なテストは回帰検出を無効化する",
      });
    }
    if (statuses.includes("failed")) {
      findings.push({
        kind: "failing_test",
        severity_hint: "high",
        location: `${entry.file}`,
        test: testId,
        evidence: (get(group[0], "failure") || "failed").slice(0, 200),
        detail: "レポート時点で失敗している",
      });
    }
    // p95 は相対順位でしかないため、単独で使うと全テストが十分速い場合でも
    // 常に上位 5% を「遅い」と報告してしまう。相対的に重いテストは絶対下限を
    // 満たすものだけを別 kind として出す。
    if (mean !== null && mean >= slowThresholdMs) {
      findings.push({
        kind: "slow_test",
        severity_hint: "low",
        location: `${entry.file}`,
        test: testId,
        evidence: `平均 ${formatFixed0(mean)}ms / 閾値 ${formatFixed0(slowThresholdMs)}ms`,
        detail: "実行時間が長いテストは実行頻度を下げ、フィードバックを遅らせる",
      });
    } else if (mean !== null && p95 !== null && mean >= p95 && mean >= RELATIVE_SLOW_FLOOR_MS) {
      findings.push({
        kind: "relatively_slow_test",
        severity_hint: "low",
        location: `${entry.file}`,
        test: testId,
        evidence: `平均 ${formatFixed0(mean)}ms（同一レポート内 p95 ${formatFixed0(p95)}ms、下限 ${formatFixed0(RELATIVE_SLOW_FLOOR_MS)}ms）`,
        detail: "絶対値は閾値未満だが、このテスト群の中では上位の実行時間を占める",
      });
    }
    if (repeatedAcrossReports && mean && mean > 50 && stdev > mean * 0.5 && durations.length > 1) {
      findings.push({
        kind: "duration_variance",
        severity_hint: "medium",
        location: `${entry.file}`,
        test: testId,
        evidence: `実行時間 ${pyReprFloatList(durations)} ms（平均 ${formatFixed0(mean)} / 標準偏差 ${formatFixed0(stdev)}）`,
        detail: "実行時間のばらつきが大きい。待機・外部依存・共有状態の影響が疑われる",
      });
    }
  }
  return [tests, findings];
}

/** LCOV を {file: {uncovered_lines: [...], uncovered_branches: [[line, branch]]}} に正規化。 */
function parseLcov(filePath) {
  const result = new Map();
  let current = null;
  for (const line of splitLines(readText(filePath))) {
    if (line.startsWith("SF:")) {
      const key = line.slice(3).trim();
      if (!result.has(key)) {
        result.set(key, { uncovered_lines: [], uncovered_branches: [] });
      }
      current = result.get(key);
    } else if (current === null) {
      continue;
    } else if (line.startsWith("DA:")) {
      const parts = line.slice(3).split(",");
      if (parts.length >= 2 && ["0", "-"].includes(parts[1].trim())) {
        current.uncovered_lines.push(Number.parseInt(parts[0].trim(), 10));
      }
    } else if (line.startsWith("BRDA:")) {
      const parts = line.slice(5).split(",");
      if (parts.length >= 4 && ["0", "-"].includes(parts[3].trim())) {
        current.uncovered_branches.push([Number.parseInt(parts[0].trim(), 10), parts[2].trim()]);
      }
    }
  }
  return result;
}

/** istanbul coverage-final.json を正規化。json-summary 形式は行情報が無いため空で返す。 */
function parseIstanbul(filePath) {
  const data = loadJson(filePath);
  const result = new Map();
  for (const [filePathKey, entry] of Object.entries(data)) {
    if (!isDict(entry) || !("statementMap" in entry)) {
      continue;
    }
    const lines = new Set();
    for (const [key, hits] of Object.entries(get(entry, "s", {}))) {
      if (hits === 0 && key in entry.statementMap) {
        lines.add(entry.statementMap[key].start.line);
      }
    }
    const uncoveredLines = [...lines].sort(byNumber);
    const uncoveredBranches = [];
    for (const [key, counts] of Object.entries(get(entry, "b", {}))) {
      const meta = get(get(entry, "branchMap", {}), key);
      if (!meta) {
        continue;
      }
      counts.forEach((count, i) => {
        if (count === 0) {
          uncoveredBranches.push([meta.loc.start.line, `${get(meta, "type", "branch")}#${i}`]);
        }
      });
    }
    result.set(filePathKey, { uncovered_lines: uncoveredLines, uncovered_branches: uncoveredBranches });
  }
  return result;
}

/** Stryker の report JSON と cargo-mutants の outcomes.json に対応。 */
function parseMutation(filePath) {
  const data = loadJson(filePath);
  const survived = [];
  if (isDict(data) && "files" in data) {
    // Stryker
    for (const [file, entry] of Object.entries(data.files)) {
      for (const mutant of get(entry, "mutants", [])) {
        if (["Survived", "NoCoverage"].includes(get(mutant, "status"))) {
          survived.push({
            file,
            line: get(get(get(mutant, "location", {}), "start", {}), "line"),
            mutator: get(mutant, "mutatorName"),
            status: get(mutant, "status"),
            description: get(mutant, "description") || get(mutant, "replacement"),
          });
        }
      }
    }
  } else if (isDict(data) && "outcomes" in data) {
    // cargo-mutants
    for (const outcome of data.outcomes) {
      if (get(outcome, "summary") !== "MissedMutant") {
        continue;
      }
      const mutant = get(get(outcome, "scenario") || {}, "Mutant") || {};
      // cargo-mutants は行番号を span.start.line に持つ。バージョン差で
      // トップレベル line を持つ形も許容する（無い側を None にしない）
      const spanLine = get(get(get(mutant, "span") || {}, "start") || {}, "line");
      survived.push({
        file: get(mutant, "file"),
        line: get(mutant, "line") || spanLine,
        mutator: get(mutant, "genre") || get(mutant, "replacement"),
        status: "MissedMutant",
        description: isDict(get(mutant, "function"))
          ? get(mutant.function, "function_name")
          : get(mutant, "replacement"),
      });
    }
  }
  return survived;
}

/** `Path(p).resolve()` 相当。シンボリックリンクを解決する（`/tmp` → `/private/tmp`）。 */
function resolvePath(p) {
  try {
    return fs.realpathSync(p);
  } catch {
    return path.resolve(p);
  }
}

/**
 * `Path.relative_to` 相当。パス要素単位の前方一致で、下位でなければ null を返す。
 *
 * 文字列の startsWith で判定してはいけない（`/a/bc` は `/a/b` の下ではない）。
 */
function relativeTo(target, root) {
  const targetParts = target.split("/");
  const rootParts = root.split("/");
  if (rootParts.some((part, i) => targetParts[i] !== part)) {
    return null;
  }
  const rest = targetParts.slice(rootParts.length);
  return rest.length > 0 ? rest.join("/") : ".";
}

function normalizePath(p, repoRoot) {
  const rel = relativeTo(resolvePath(p), repoRoot);
  // フォールバックの `lstrip("./")` は先頭の `.` と `/` を任意個・任意順で剥がす
  return rel === null ? p.replace(/^[./]+/, "") : rel;
}

function intersectWithTargets(coverage, survived, targets) {
  const repoRoot = resolvePath(process.cwd());
  const covByRel = new Map();
  for (const [key, value] of coverage) {
    covByRel.set(normalizePath(key, repoRoot), value);
  }
  if (targets === null) {
    return {
      uncovered_changed_lines: [],
      uncovered_changed_branches: [],
      survived_mutants_in_changed: [],
      note: "targets 未指定のため変更範囲との突き合わせは未実施",
    };
  }

  const uncoveredLines = [];
  const uncoveredBranches = [];
  const survivedInChanged = [];
  for (const target of get(targets, "targets", [])) {
    const fileRel = normalizePath(target.file, repoRoot);
    const changed = new Set();
    for (const [lo, hi] of target.changed_lines) {
      for (let line = lo; line <= hi; line += 1) {
        changed.add(line);
      }
    }
    const entry = covByRel.get(fileRel);
    if (entry) {
      const hitLines = [...new Set(entry.uncovered_lines)].filter((l) => changed.has(l)).sort(byNumber);
      if (hitLines.length > 0) {
        uncoveredLines.push({ file: fileRel, function: target.function, lines: hitLines });
      }
      const hitBranches = entry.uncovered_branches.filter((b) => changed.has(b[0]));
      if (hitBranches.length > 0) {
        uncoveredBranches.push({ file: fileRel, function: target.function, branches: hitBranches });
      }
    }
    for (const mutant of survived) {
      if (get(mutant, "file") === null || get(mutant, "line") === null) {
        continue;
      }
      if (normalizePath(mutant.file, repoRoot) === fileRel && changed.has(mutant.line)) {
        survivedInChanged.push({ ...mutant, file: fileRel, function: target.function });
      }
    }
  }
  return {
    uncovered_changed_lines: uncoveredLines,
    uncovered_changed_branches: uncoveredBranches,
    survived_mutants_in_changed: survivedInChanged,
  };
}

function main() {
  const args = parseArgs(process.argv.slice(2), {
    testJson: { append: true },
    nextestJson: { append: true },
    coverageLcov: { append: true },
    coverageJson: { append: true },
    mutationJson: { append: true },
    targets: {},
    slowThresholdMs: { type: "float", default: 1000.0 },
    out: {},
  });

  const records = [];
  for (const p of args.testJson) {
    records.push(...parseJestLike(p));
  }
  for (const p of args.nextestJson) {
    records.push(...parseLibtestJsonl(p));
  }

  const coverage = new Map();
  for (const p of args.coverageLcov) {
    for (const [key, value] of parseLcov(p)) {
      coverage.set(key, value);
    }
  }
  for (const p of args.coverageJson) {
    for (const [key, value] of parseIstanbul(p)) {
      coverage.set(key, value);
    }
  }

  const survived = [];
  for (const p of args.mutationJson) {
    survived.push(...parseMutation(p));
  }

  const targets = args.targets ? loadJson(args.targets) : null;
  const [tests, findings] = aggregateTests(records, args.slowThresholdMs);
  const crossed = intersectWithTargets(coverage, survived, targets);

  const notMeasured = [];
  if (records.length === 0) {
    notMeasured.push("実行結果・実行時間");
  }
  // レポート件数ではなく、同一テストが「別のレポートに」2 回以上現れたかで判定する。
  // TypeScript 1 件 + Rust 1 件は合計 2 件でも比較対象が無く、
  // 1 レポート内の同名テスト 2 件（重複テスト）も反復実行ではない。
  if (!tests.some((t) => t.sources.length >= 2)) {
    notMeasured.push("複数実行間のばらつき・不安定さ（同一テストを含むレポートが2件以上必要）");
  }
  if (coverage.size === 0) {
    notMeasured.push("カバレッジ");
  }
  if (survived.length === 0) {
    // --mutation-json を渡したのに生存変異が 0 件なのは「未計測」ではない
    if (args.mutationJson.length === 0) {
      notMeasured.push("ミューテーションテスト");
    }
  }

  const summary = {
    reports: args.testJson.length + args.nextestJson.length,
    tests: tests.length,
    coverage_files: coverage.size,
    survived_mutants_total: survived.length,
  };
  for (const f of findings) {
    summary[f.kind] = get(summary, f.kind, 0) + 1;
  }

  dump(
    {
      summary,
      not_measured: notMeasured,
      findings,
      changed_scope: crossed,
      tests,
      survived_mutants: survived,
    },
    args.out,
  );
  return 0;
}

// Python 版の `if __name__ == "__main__":` 相当。二点、素朴な書き方では壊れる。
// - argv[1] を realpath へ通す: 起動パスがシンボリックリンク経由でも、ESM の
//   import.meta.url は実体パスに解決されるため、揃えないとガードが常に偽になる
// - process.exit() ではなく exitCode: exit() は stdout のバッファを破棄するので、
//   --out 省略時のパイプ出力が途中で切り捨てられる
if (process.argv[1] && pathToFileURL(fs.realpathSync(process.argv[1])).href === import.meta.url) {
  process.exitCode = main();
}
