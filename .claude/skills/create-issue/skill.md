---
name: create-issue
description: 指定された内容でGitHub issueを作成する
disable-model-invocation: false
allowed-tools: Bash
argument-hint: "<title> [--body <body>] [--repo <owner/repo>]"
---

GitHub issueを作成してください。

## 引数
$ARGUMENTS

## 実行手順
1. 引数からタイトル、本文、リポジトリを解析
2. issueを作成（署名を本文末尾に必ず含めること）：

   ```bash
   gh issue create --title "<タイトル>" --body "$(cat <<'EOF'
   <本文>

   ---
   🤖 Created with [Claude Code](https://claude.ai/claude-code)
   EOF
   )"
   ```

   `--repo` が指定された場合は `--repo <owner/repo>` を付与する。

3. 作成されたissueのURLをユーザーに報告
