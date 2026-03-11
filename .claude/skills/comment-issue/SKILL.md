---
name: comment-issue
description: GitHub issueやPRにコメントを投稿・追加・残す。結果やサマリーをissueに書き込む際に使用
argument-hint: <issue/pr-url or owner/repo#number> [comment-body]
allowed-tools: Bash
user-invocable: true
---

GitHub issueまたはPRにコメントを投稿してください。

## 引数
$ARGUMENTS

## 引数の形式

以下のいずれかの形式でissue/PRを指定できます：

1. **GitHub URL**:
   - issue: `https://github.com/owner/repo/issues/123`
   - PR: `https://github.com/owner/repo/pull/123`
2. **owner/repo#番号**: `anthropics/claude-code#456`
3. **番号のみ**: `123`（現在のリポジトリのissue/PRとして扱う）

残りの引数はコメント本文として使用します。

## 実行手順

1. 引数からissue/PR指定とコメント本文を解析する
2. URLに `/pull/` が含まれる場合は `gh pr comment` を使用、それ以外は `gh issue comment` を使用
3. 以下のコマンドを使用してコメントを投稿：
   - PR URL指定の場合: `gh pr comment <url> --body "<コメント>"`
   - issue URL指定の場合: `gh issue comment <url> --body "<コメント>"`
   - owner/repo#番号の場合: `gh issue comment <番号> --repo <owner/repo> --body "<コメント>"`
   - 番号のみの場合: `gh issue comment <番号> --body "<コメント>"`

4. コメント本文の末尾に以下の署名を必ず追加すること：

```
---
🤖 *This comment was posted via [Claude Code](https://claude.ai/claude-code)*
```

## 注意事項

- issue/PR指定が不明確な場合はユーザーに確認する
- コメント本文が空の場合はユーザーに確認する
- 投稿成功後、投稿したissue/PRへのリンクを表示する
