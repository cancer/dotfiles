---
name: comment-issue
description: GitHub issueやPRにコメントを投稿・追加・残す。結果やサマリーをissueに書き込む際に使用
argument-hint: <issue/pr-url or owner/repo#number> [comment-body] [--model <name>]
model: haiku
allowed-tools: Bash, Agent, Skill
user-invocable: true
---

GitHub issueまたはPRへのコメント投稿を行う。

## 引数
$ARGUMENTS

## 引数の形式

以下のいずれかの形式でissue/PRを指定できます：

1. **GitHub URL**:
   - issue: `https://github.com/owner/repo/issues/123`
   - PR: `https://github.com/owner/repo/pull/123`
2. **owner/repo#番号**: `anthropics/claude-code#456`
3. **番号のみ**: `123`（現在のリポジトリのissue/PRとして扱う）

残りの引数はコメント本文として使用します。`--model <name>` は委譲先のモデル指定として解釈し、コメント本文には含めません。

## モデルルーティング

`--model` の値に応じて、コメント投稿処理を以下の委譲先に振り分ける。

| `--model` 値 | 委譲先 | 備考 |
|---|---|---|
| `haiku` （デフォルト） | このskill自身で実行 | フロントマターの `model: haiku` で動作 |
| `sonnet` / `opus` | `Agent` ツール（`subagent_type: "general-purpose"`、`model: <指定>`） | Claudeの別モデルに委譲 |
| `gpt` / `gpt-*` | `Skill("codex:rescue", args: ...)` | 素の `gpt` ならモデル指定なし、`gpt-*` ならargsに `--model <name>` を含める |
| `co-opus` | Bashで `copilot --model claude-opus-4.6 -p "<プロンプト>" --yolo` | |
| `co-gpt-*` | Bashで `copilot --model gpt-* -p "<プロンプト>" --yolo`（`co-` を除いたモデル名を渡す） | |

未知のモデル名が指定された場合は実行せず、サポート対象を提示して終了する。

## 実行プロンプト（委譲先 / 自身で実行する場合の共通プロンプト）

下記の指示に沿ってコメント投稿を完了させ、最終レポートを日本語で出力する。

```
You are responsible for posting a comment to a GitHub issue or pull request.

Input:
- Raw arguments: $ARGUMENTS
- Target reference: extract the issue or PR target from the raw arguments
- Comment body: extract the remaining text (excluding --model flag) as the comment body

Complete this task in a single execution. Do not ask the user for confirmation
unless the target or comment body is genuinely impossible to determine.
Write the final user-facing report in Japanese.

Requirements:
- Parse the raw arguments first and determine the normalized input values before taking action.
- Support GitHub issue URLs, PR URLs, owner/repo#number references, and plain numbers for the current repository.
- If the target is a PR, use gh pr comment.
- If the target is an issue, use gh issue comment.
- If the target is owner/repo#number, use the correct repo explicitly.
- Always append the required signature to the end of the comment body.
- Post the comment.
- Report the final target and success status.

Use these commands as needed:
- gh pr comment <url> --body "<comment>"
- gh issue comment <url> --body "<comment>"
- gh issue comment <number> --repo <owner/repo> --body "<comment>"
- gh issue comment <number> --body "<comment>"

Always append this signature to the comment body:

---
🤖 *This comment was posted via [Claude Code](https://claude.ai/claude-code)*

At the start of the report, include the normalized values used for target reference, comment body presence, and the selected `--model`.

If successful, report posted target, whether it was an issue or PR, the target URL, and success confirmation.
If unsuccessful, report why posting failed and whether the target or comment body was ambiguous.
```

## 実行方針

- 委譲する場合も自身で実行する場合も、**1回の実行で投稿を完了させる**こと
- 投稿ループや複数回の呼び出しは禁止

## 注意事項

- 現在の作業ディレクトリが対象リポジトリであることを前提とする
