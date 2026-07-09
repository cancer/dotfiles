---
name: watch-ci
description: GitHub PR の CI を監視し、失敗があれば原因を調べて修正する。「CI を見といて」「CI 通して」「PRのチェックが落ちてる」と頼まれた場面で使う
argument-hint: <pr-url or number> [--interval <seconds>] [--max-retries <count>] [--model <name>]
model: sonnet
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Skill, Agent
user-invocable: true
---

指定されたPRのCI監視・修正タスクを実行する。

## 引数
$ARGUMENTS

## 引数の形式

- **PR指定**（必須）: 以下のいずれか
  1. GitHub URL: `https://github.com/owner/repo/pull/123`
  2. 番号のみ: `123`（現在のリポジトリのPRとして扱う）
- `--interval <seconds>`: CIのポーリング間隔（デフォルト: 30秒）
- `--max-retries <count>`: 修正→再チェックの最大試行回数（デフォルト: 無制限）
- `--model <name>`: CI監視・修正を実行するモデル。未指定なら `sonnet`

## モデルルーティング

`--model` の値に応じて、CI監視・修正処理を以下の委譲先に振り分ける。

| `--model` 値 | 委譲先 | 備考 |
|---|---|---|
| `sonnet` （デフォルト） | このskill自身で実行 | フロントマターの `model: sonnet` で動作 |
| `haiku` / `opus` | `Agent` ツール（`subagent_type: "general-purpose"`、`model: <指定>`） | Claudeの別モデルに委譲 |
| `gpt` / `gpt-*` | `Skill("codex:rescue", args: ...)` | argsに「下記プロンプト＋（明示モデルなら）`--model <name>`」を含める |
| `co-opus` | Bashで `copilot --model claude-opus-4.6 -p "<プロンプト>" --yolo` | |
| `co-gpt-*` | Bashで `copilot --model gpt-* -p "<プロンプト>" --yolo`（`co-` を除いたモデル名を渡す） | |

未知のモデル名が指定された場合は実行せず、サポート対象を提示して終了する。

## 実行プロンプト（委譲先 / 自身で実行する場合の共通プロンプト）

下記の指示に沿ってCI監視・修正を完了させ、最終レポートを日本語で出力する。

```
You are responsible for watching and fixing CI for a GitHub PR until it is green or clearly unfixable.

Input:
- Raw arguments: $ARGUMENTS
- PR target: extract from the raw arguments
- Poll interval seconds: extract from --interval, default to 30 if omitted
- Max retries: extract from --max-retries, default to unlimited if omitted

Complete the entire monitoring and fix cycle in this single execution.
Do not ask the user for confirmation. Write the final user-facing report in Japanese.

Requirements:
- Parse the raw arguments first and determine the normalized input values before taking action.
- Support a PR URL or a PR number for the current repository.
- Use the extracted --interval value, or default to 30.
- Use the extracted --max-retries value, or default to unlimited.
- Fetch PR metadata with gh.
- Check out the PR branch.
- Poll CI status using gh pr checks.
- If checks are pending or in progress, sleep for the configured interval and check again.
- If checks fail, inspect failed runs and failed job steps.
- Classify the failure type: lint, typecheck, test, build, E2E, or other.
- Identify the concrete root cause from logs.
- Make only the minimal code change needed to address the CI failure.
- Preserve the intent of the PR.
- Do not refactor or make unrelated improvements.
- Validate locally when possible before committing.
- Commit with a message like: fix: CI failure - <short summary>
- Push the change.
- Continue the loop until all checks pass, the retry limit is reached, or the issue is clearly unfixable.
- If rerunning CI is needed, use gh run rerun.
- Never apply the same kind of fix twice for the same recurring error.

Use these commands as needed:
- gh pr view <number> --repo <owner/repo> --json number,title,headRefName,baseRefName,state,url
- gh pr checks <number> --repo <owner/repo>
- gh run view <run-id> --repo <owner/repo> --log-failed
- gh run list --branch <head-branch> --repo <owner/repo> --limit 5 --json databaseId,status,conclusion,name
- gh run view <run-id> --repo <owner/repo> --json jobs --jq '.jobs[] | select(.conclusion == "failure") | {name, steps: [.steps[] | select(.conclusion == "failure")]}'
- gh run rerun <run-id> --repo <owner/repo>

Treat the following as unfixable and stop with a clear report:
- Environment or infrastructure failures
- Likely flaky tests unrelated to the PR changes
- Failures whose root cause cannot be determined from logs
- Fixes that would significantly exceed the PR scope
- The same error recurring after an attempted fix

At the start of the report, include the normalized values used for PR target, poll interval seconds, max retries, and the selected `--model`.

If successful, include PR URL, final CI status, summary of fixes made, and number of fix attempts.
If unfixable, include PR URL, failed checks, short error summary, why it is unfixable, and recommended next action.
```

## 実行方針

- 委譲する場合も自身で実行する場合も、**1回の実行で監視ループを完結させる**こと
- 監視・修正・commit / push・再確認をすべてその1回の中で完結させる

## 注意

- 現在の作業ディレクトリが対象リポジトリであることを前提とする
