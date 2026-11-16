// collect_metrics.mjs のミューテーション集計（殺された変異と生き残った変異を関数ごとに数える）を検証する。
// 実行: node --test ~/.claude/skills/test-review/scripts/tests/collect_metrics.test.mjs
import { test } from "node:test";
import assert from "node:assert/strict";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { fileURLToPath } from "node:url";

const SCRIPT = path.join(path.dirname(fileURLToPath(import.meta.url)), "..", "collect_metrics.mjs");

const TARGETS = {
  targets: [
    { file: "src/age.ts", function: "canVote", changed_lines: [[7, 10]] },
    { file: "src/age.ts", function: "noMutants", changed_lines: [[20, 22]] },
  ],
};

function strykerMutant(line, status) {
  return { id: `${line}-${status}`, mutatorName: "EqualityOperator", replacement: "x", location: { start: { line, column: 1 } }, status };
}

function cargoOutcome(line, summary) {
  return { summary, scenario: { Mutant: { file: "src/age.ts", span: { start: { line } }, genre: "BinaryOperator" } } };
}

function collect(mutationReport) {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), "collect-metrics-"));
  fs.writeFileSync(path.join(dir, "targets.json"), JSON.stringify(TARGETS));
  fs.writeFileSync(path.join(dir, "mutation.json"), JSON.stringify(mutationReport));
  execFileSync("node", [SCRIPT, "--mutation-json", "mutation.json", "--targets", "targets.json", "--out", "metrics.json"], { cwd: dir, stdio: "pipe" });
  return JSON.parse(fs.readFileSync(path.join(dir, "metrics.json"), "utf8"));
}

test("Stryker / mutator 形式: 変更関数ごとに殺された・生き残った変異を数え、対象外の状態は数えない", () => {
  const metrics = collect({
    files: {
      "src/age.ts": {
        mutants: [
          strykerMutant(8, "Killed"),
          strykerMutant(9, "Timeout"),
          strykerMutant(9, "Survived"),
          strykerMutant(9, "Pending"),
          strykerMutant(9, "CompileError"),
          strykerMutant(9, "Ignored"),
          strykerMutant(2, "Survived"), // 変更範囲外
        ],
      },
    },
  });
  assert.deepEqual(metrics.changed_scope.mutants_by_function, [
    { file: "src/age.ts", function: "canVote", total: 3, killed: 2, survived: 1, all_killed: false },
  ]);
  assert.equal(metrics.changed_scope.survived_mutants_in_changed.length, 1);
  assert.equal(metrics.changed_scope.survived_mutants_in_changed[0].line, 9);
  assert.equal(metrics.summary.survived_mutants_total, 2);
  assert.equal(metrics.summary.killed_mutants_total, 2);
});

test("cargo-mutants 形式: CaughtMutant と Timeout を殺された変異として数える", () => {
  const metrics = collect({
    outcomes: [
      { summary: "Success", scenario: "Baseline" },
      cargoOutcome(8, "CaughtMutant"),
      cargoOutcome(9, "Timeout"),
      cargoOutcome(9, "Unviable"),
    ],
  });
  assert.deepEqual(metrics.changed_scope.mutants_by_function, [
    { file: "src/age.ts", function: "canVote", total: 2, killed: 2, survived: 0, all_killed: true },
  ]);
});

test("変異が突き合わない関数は mutants_by_function に載せない（全て殺されたと混同させない）", () => {
  const metrics = collect({ files: { "src/age.ts": { mutants: [strykerMutant(8, "Killed")] } } });
  const functions = metrics.changed_scope.mutants_by_function.map((f) => f.function);
  assert.deepEqual(functions, ["canVote"]);
});

test("--mutation-json を渡せば、生き残りが 0 件でも未計測にしない", () => {
  const metrics = collect({ files: { "src/age.ts": { mutants: [strykerMutant(8, "Killed")] } } });
  assert.ok(!metrics.not_measured.includes("ミューテーションテスト"));
});
