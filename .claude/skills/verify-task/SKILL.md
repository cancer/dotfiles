---
name: verify-task
description: ワーカーの成果物が指示どおり完了しているかを検証する。完了チェックに特化し、品質レビューはしない。サブエージェントの作業を受け取った場面で使う。原則ベースの品質レビューは code-review の領分
argument-hint: <指示内容> <worktreeパスまたはブランチ名> [issue参照] [--model <name>]
model: sonnet
allowed-tools: Bash, Read, Glob, Grep, Agent, Skill
user-invocable: false
---

ワーカーの成果物が指示通りにできているかの検証を行う。品質レビューではなく、指示の完了チェックに特化。

## 引数
$ARGUMENTS

引数から以下を特定する：
- **指示内容**: ワーカーに何を依頼したか
- **worktreeパスまたはブランチ名**: ワーカーの作業場所
- **issue参照**（任意）: GitHub issueのURL、`owner/repo#番号`、または `#番号`
- **`--model <name>`**（任意）: 検証を実行するモデル。未指定なら `sonnet`

## モデルルーティング

`--model` の値に応じて、検証実行を以下の委譲先に振り分ける。

| `--model` 値 | 委譲先 | 備考 |
|---|---|---|
| `sonnet` （デフォルト） | このskill自身で実行 | フロントマターの `model: sonnet` で動作 |
| `haiku` | `Agent` ツール（`subagent_type: "general-purpose"`、`model: haiku`） | 単純なチェックリスト照合で足りる軽案件向けの opt-down |
| `opus` | `Agent` ツール（`subagent_type: "general-purpose"`、`model: opus`） | 意図判定が難しい案件向けのエスカレーション |
| `gpt` / `gpt-*` | `Skill("codex:rescue", args: ...)` | argsに「下記のプロンプト＋（明示モデルなら）`--model <name>`」を含める。素の `gpt` ならモデル指定なし |
| `co-opus` | Bashで `copilot --model claude-opus-4.6 -p "<プロンプト>" --yolo` | |
| `co-gpt-*` | Bashで `copilot --model gpt-* -p "<プロンプト>" --yolo`（`co-` を除いたモデル名を渡す） | |

未知のモデル名が指定された場合は実行せず、サポート対象を提示して終了する。

## 検証プロンプト（委譲先 / 自身で実行する場合の共通プロンプト）

下記の指示に沿って検証を完了させ、最終レポートを日本語で出力する。

```
You are responsible for verifying whether a worker's output fully matches the requested task.

Input:
- Raw arguments: $ARGUMENTS
- Instruction content: extract from the raw arguments
- Worktree path or branch name: extract from the raw arguments
- Issue reference: extract if provided, otherwise none

Complete this task in a single execution. Do not ask the user for confirmation.
Write the final user-facing report in Japanese.

Requirements:
- Parse the raw arguments first and determine the normalized input values before taking action.
- If an issue reference is provided, fetch the issue and inspect both the body and comments for additional requirements, clarifications, or scope changes.
- Inspect the worker changes in the specified worktree path or branch.
- Use git diff to understand what was actually changed.
- If there are multiple commits, compare against the appropriate base instead of assuming only HEAD~..HEAD.
- Verify whether all requested changes were implemented.
- Verify whether any unrequested changes were included.
- Verify whether the implementation matches the intended meaning of the instruction, not just superficial keywords.
- If an issue is provided, treat the issue as the source of truth and verify the changes against the issue requirements as well.
- Determine the appropriate project check/lint command and typecheck command from project files such as package.json and CLAUDE.md when available.
- Run relevant check/lint and typecheck commands when they exist.
- Capture any failures clearly.
- Do not modify files.
- Do not fix problems.
- Produce only a verification report.

Use these commands as needed:
- gh issue view <number> --repo <owner/repo> --json number,title,body,labels,comments
- git diff HEAD~..HEAD
- git diff <base>..HEAD
- git status
- git branch --show-current

Output format:

## 検証結果

### issueとの突合
(記載可能な場合のみ)
- issue: <owner/repo#番号> <issueタイトル>
- [ ] issueの要件がすべて満たされている
- [ ] 指示内容とissueの間に齟齬がない

### 指示突合
- [ ] 指示された変更がすべて実施されている
- [ ] 指示にない変更が含まれていない
- [ ] 指示の意図と異なる実装になっていない

### check/typecheck
- [ ] <check or lint command>: pass/fail/not found
- [ ] <typecheck command>: pass/fail/not found

### 判定
PASS / FAIL（理由）

At the start of the report, include the normalized values used for instruction content, worktree path or branch name, issue reference, and the selected `--model`.
```

## 実行方針

- 委譲する場合（外部CLI / Agent）も、自身で実行する場合も、**1回の実行で検証を完了させる**こと
- 検証ループや複数回の呼び出しは禁止
- 委譲先には上記プロンプトをそのまま渡す（`$ARGUMENTS` は展開済みの値を埋め込む）

## 注意

- 現在の作業ディレクトリや対象worktreeで検証可能な範囲を前提とする
- ファイルの修正や問題の修正は行わない。検証レポートのみを出力する
