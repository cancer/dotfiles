---
name: create-general-issue
model: haiku
description: 指定された内容でGitHub issueを作成する。「別issueで対応」「issueを切る」「issue化する」「後で対応が必要」等、会話中にissue起票が必要になった場面で使用
disable-model-invocation: false
allowed-tools: Bash
argument-hint: "<title> [--body <body>] [--repo <owner/repo>]"
---

GitHub issueを作成する。

## 引数
$ARGUMENTS

- `<title>`: issueタイトル
- `--body <body>`（任意）: issue本文
- `--repo <owner/repo>`（任意）: 作成先リポジトリ。未指定なら現在のリポジトリ

**このスキルはどのモデルで実行するかを判断しない。** 実行エンジンと推論量の選択は呼び出し側の責務である（`dev-workflow` は `delegate-to-codex` 経由でこのスキルを Codex に実行させる）。ここに書くのは手順だけとする。

## 実行プロンプト（委譲先 / 自身で実行する場合の共通プロンプト）

```
GitHub issueを作成せよ。

指定内容: $ARGUMENTS

手順:
1. 指定内容からタイトル・本文・リポジトリを解析
2. gh issue create でissue作成。--repo指定があれば付与。本文末尾に署名を含める:
   ---
   🤖 Created with [Claude Code](https://claude.ai/claude-code)
3. issueのURLを出力
```

## 実行方針

- 委譲する場合も自身で実行する場合も、**1回の実行で完了させる**こと
