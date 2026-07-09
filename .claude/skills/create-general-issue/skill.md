---
name: create-general-issue
model: haiku
description: 指定された内容でGitHub issueを作成する。「別issueで対応」「issueを切る」「issue化する」「後で対応が必要」等、会話中にissue起票が必要になった場面で使用
disable-model-invocation: false
allowed-tools: Bash, Agent, Skill
argument-hint: "<title> [--body <body>] [--repo <owner/repo>] [--model <name>]"
---

GitHub issueを作成する。

## 引数
$ARGUMENTS

- `<title>`: issueタイトル
- `--body <body>`（任意）: issue本文
- `--repo <owner/repo>`（任意）: 作成先リポジトリ。未指定なら現在のリポジトリ
- `--model <name>`（任意）: issue作成を実行するモデル。未指定なら `haiku`

## モデルルーティング

`--model` の値に応じて、issue作成処理を以下の委譲先に振り分ける。

| `--model` 値 | 委譲先 | 備考 |
|---|---|---|
| `haiku` （デフォルト） | このskill自身で実行 | フロントマターの `model: haiku` で動作 |
| `sonnet` / `opus` | `Agent` ツール（`subagent_type: "general-purpose"`、`model: <指定>`） | Claudeの別モデルに委譲 |
| `gpt` / `gpt-*` | `Skill("codex:rescue", args: ...)` | 素の `gpt` ならモデル指定なし、`gpt-*` なら argsに `--model <name>` を含める |
| `co-opus` | Bashで `copilot --model claude-opus-4.6 -p "<プロンプト>" --yolo` | |
| `co-gpt-*` | Bashで `copilot --model gpt-* -p "<プロンプト>" --yolo`（`co-` を除いたモデル名を渡す） | |

未知のモデル名が指定された場合は実行せず、サポート対象を提示して終了する。

## 実行プロンプト（委譲先 / 自身で実行する場合の共通プロンプト）

```
GitHub issueを作成せよ。

指定内容: $ARGUMENTS （--model フラグは除外する）

手順:
1. 指定内容からタイトル・本文・リポジトリを解析
2. gh issue create でissue作成。--repo指定があれば付与。本文末尾に署名を含める:
   ---
   🤖 Created with [Claude Code](https://claude.ai/claude-code)
3. issueのURLを出力
```

## 実行方針

- 委譲する場合も自身で実行する場合も、**1回の実行で完了させる**こと
