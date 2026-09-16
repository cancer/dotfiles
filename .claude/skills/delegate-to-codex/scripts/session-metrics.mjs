#!/usr/bin/env node

// キャッシュ率は長いセッションほど高くなり、効率の指標ではないため、追うと逆方向へ誘導するので出力しない。

import { createReadStream } from "node:fs";
import { readdir } from "node:fs/promises";
import { homedir } from "node:os";
import { basename, join } from "node:path";
import { createInterface } from "node:readline";

const SESSIONS_ROOT = join(homedir(), ".codex", "sessions");
const DATE_PATTERN = /^\d{4}\/\d{2}\/\d{2}$/;
const AUTO_REVIEW_MODEL = "codex-auto-review";
const SESSION_ID_PATTERN = /([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})\.jsonl$/i;

function today() {
  const date = new Date();
  const year = String(date.getFullYear()).padStart(4, "0");
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return year + "/" + month + "/" + day;
}

function parseDates(args) {
  const dates = args.length === 0 ? [today()] : args;
  const invalid = dates.find((date) => !DATE_PATTERN.test(date));
  if (invalid) {
    throw new Error("日付は YYYY/MM/DD 形式で指定してください: " + invalid);
  }
  return dates;
}

async function sessionPaths(date) {
  const datePath = join(SESSIONS_ROOT, ...date.split("/"));
  const entries = await readdir(datePath, { withFileTypes: true });
  return entries
    .filter((entry) => entry.isFile() && entry.name.endsWith(".jsonl"))
    .map((entry) => join(datePath, entry.name))
    .sort();
}

function numeric(value) {
  return typeof value === "number" && Number.isFinite(value) ? value : null;
}

async function readSession(filePath, date) {
  const contexts = [];
  let inputTotal = null;
  let compactCount = 0;
  let autoReview = false;

  const input = createReadStream(filePath, { encoding: "utf8" });
  const lines = createInterface({ input, crlfDelay: Infinity });

  for await (const line of lines) {
    let record;
    try {
      record = JSON.parse(line);
    } catch {
      continue;
    }

    if (record?.model === AUTO_REVIEW_MODEL || record?.payload?.model === AUTO_REVIEW_MODEL) {
      autoReview = true;
    }

    if (record?.type === "compacted" || record?.payload?.type === "compacted") {
      compactCount += 1;
    }

    if (record?.payload?.type !== "token_count") {
      continue;
    }

    contexts.push(numeric(record.payload.info?.last_token_usage?.input_tokens));
    inputTotal = numeric(record.payload.info?.total_token_usage?.input_tokens);
  }

  const incrementsAtLeast5000 = contexts.reduce((count, current, index) => {
    if (index === 0 || current === null || contexts[index - 1] === null) {
      return count;
    }
    return current - contexts[index - 1] >= 5_000 ? count + 1 : count;
  }, 0);
  const maxContext = contexts.reduce(
    (max, context) => context === null ? max : Math.max(max, context),
    0,
  );
  const turnCount = contexts.length;

  return {
    date,
    session: basename(filePath).match(SESSION_ID_PATTERN)?.[1] ?? basename(filePath),
    autoReview,
    turnCount,
    inputTotal,
    inputPerTurn: inputTotal !== null && turnCount > 0 ? inputTotal / turnCount : null,
    maxContext: maxContext > 0 ? maxContext : null,
    incrementsAtLeast5000,
    compactCount,
  };
}

function numberText(value, decimals = 0) {
  if (value === null || !Number.isFinite(value)) {
    return "-";
  }
  const rounded = decimals === 0 ? Math.round(value).toString() : value.toFixed(decimals);
  const [integer, fraction] = rounded.split(".");
  const formattedInteger = Number(integer).toLocaleString("en-US");
  return fraction === undefined ? formattedInteger : formattedInteger + "." + fraction;
}

function cell(value, width, align = "left") {
  const text = String(value);
  const clipped = text.length > width ? text.slice(0, width - 1) + "…" : text;
  return align === "right" ? clipped.padStart(width) : clipped.padEnd(width);
}

function row(values) {
  const widths = [10, 36, 7, 14, 12, 13, 8, 8];
  const aligns = ["left", "left", "right", "right", "right", "right", "right", "right"];
  return values.map((value, index) => cell(value, widths[index], aligns[index])).join("  ");
}

function printReport(rows, autoReviewCount) {
  console.log(row(["DATE", "SESSION", "TURNS", "INPUT TOTAL", "INPUT/TURN", "MAX CONTEXT", ">=5000", "COMPACT"]));
  console.log(row(["-".repeat(10), "-".repeat(36), "-".repeat(7), "-".repeat(14), "-".repeat(12), "-".repeat(13), "-".repeat(8), "-".repeat(8)]));

  for (const item of rows) {
    console.log(row([
      item.date,
      item.session,
      item.turnCount,
      numberText(item.inputTotal),
      numberText(item.inputPerTurn, 1),
      numberText(item.maxContext),
      item.incrementsAtLeast5000,
      item.compactCount,
    ]));
  }

  const totalTurns = rows.reduce((sum, item) => sum + item.turnCount, 0);
  const totalInput = rows.reduce((sum, item) => sum + (item.inputTotal ?? 0), 0);
  const totalCompact = rows.reduce((sum, item) => sum + item.compactCount, 0);
  console.log(row([
    "TOTAL",
    "",
    totalTurns,
    numberText(totalInput),
    numberText(totalTurns > 0 ? totalInput / totalTurns : null, 1),
    "-",
    "-",
    totalCompact,
  ]));
  console.log("codex-auto-review: " + autoReviewCount + " session(s) excluded");
}

async function main() {
  const dates = parseDates(process.argv.slice(2));
  const rows = [];
  let autoReviewCount = 0;

  for (const date of dates) {
    for (const filePath of await sessionPaths(date)) {
      const item = await readSession(filePath, date);
      if (item.autoReview) {
        autoReviewCount += 1;
      } else {
        rows.push(item);
      }
    }
  }

  printReport(rows, autoReviewCount);
}

main().catch((error) => {
  console.error(error.message);
  process.exitCode = 1;
});
