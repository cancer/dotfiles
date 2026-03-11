---
name: create-pr
description: カレントブランチを元にPRを作成する
argument-hint: "[--title <title>] [--base <branch>]"
allowed-tools: Bash, Skill
user-invocable: true
---

カレントブランチを元にGitHub PRを作成してください。

## 引数
$ARGUMENTS

## 引数の形式

- `--title <title>`: PRのタイトル（省略時はコミットメッセージから推測）
- `--base <branch>`: マージ先のブランチ（省略時はデフォルトブランチ）

## 実行手順

1. 現在のブランチを確認
2. PRに含まれるコミットを確認
3. ベースブランチとの差分を確認
4. `npm run check` と `npm run typecheck` を実行し、すべてパスすることを確認する。失敗した場合はPR作成を中断しユーザーに報告する
5. リモートにプッシュされているか確認し、されていなければプッシュ
6. 以下の形式でPRを作成：

```bash
gh pr create --title "<タイトル>" --body "$(cat <<'EOF'
## Summary
<変更内容の要約を1-3行で記述>

## Changes
<主な変更点を箇条書きで記述>

---
🤖 *This PR was created via [Claude Code](https://claude.ai/claude-code)*
EOF
)"
```

## 注意事項

- PRタイトルが指定されていない場合、コミットメッセージやdiffの内容から適切なタイトルを提案する
- 作成成功後、PRのURLをユーザーに表示する
- ベースブランチが指定されていない場合は、リポジトリのデフォルトブランチを使用
- 署名は必ず本文の末尾に含めること
