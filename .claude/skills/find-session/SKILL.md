---
name: find-session
description: キーワードで過去のセッションを検索し内容を要約する。「前にやった○○のセッションを探して」「あの作業どこだっけ?」と頼まれた場面で使う
argument-hint: <検索キーワード(issue番号, PR番号, ブランチ名, 機能名等)>
model: sonnet
allowed-tools: Bash, Read, Glob, Grep
user-invocable: true
---

# セッション検索

## 引数
$ARGUMENTS

引数は必須。検索キーワードを指定する（例: `#55`, `PR #50`, `toLegacySchema`, `db-gateway`）。

## 実行手順

### Step 1: セッションログファイルの収集

1. 現在のプロジェクトのパスを特定する（`pwd` の結果を使用）
2. プロジェクトパスから対応するディレクトリ名を推定する（先頭の `/` を除去し、残りの `/` を `-` に置換）
3. `~/.claude/projects/` 配下で、そのディレクトリ名に前方一致するディレクトリを列挙する（worktree用の派生パスを含めるため）
4. 対象ディレクトリ内の `.jsonl` ファイルを列挙する（`subagents/` 配下は除外）

```bash
find "$PROJECT_DIR" -name "*.jsonl" -not -path "*/subagents/*" -type f
```

### Step 2: キーワードでファイルを絞り込む

`grep -l` でキーワードを含むセッションファイルを特定する。

```bash
grep -l "$KEYWORD" "$PROJECT_DIR"/**/*.jsonl 2>/dev/null | grep -v subagents
```

キーワードがissue番号（例: `#55`）の場合、`#55` と `55` の両方で検索する。

### Step 3: マッチしたセッションの要約

各マッチファイルについて以下を抽出・表示する:

1. **セッションID**: ファイル名（.jsonl除去）
2. **最終更新日時**: ファイルのmtime
3. **メッセージ数**: `jq -r 'select(.type == "user")' | jq -s 'length'`
4. **目的**: 最初のユーザーメッセージから推定（先頭のユーザーメッセージを1件抽出）
5. **最後のやり取り**: 末尾のユーザーメッセージを1件抽出

```bash
# 最初のユーザーメッセージ
jq -r 'select(.type == "user") | .message.content | if type == "string" then . elif type == "array" then .[0].text // "" else "" end' "$FILE" | head -1

# 最後のユーザーメッセージ
jq -r 'select(.type == "user") | .message.content | if type == "string" then . elif type == "array" then .[0].text // "" else "" end' "$FILE" | tail -1
```

大きいファイル（5MB超）はサンプリングする:
- 最初のメッセージ: `head -c 500000 "$FILE" | jq ...`
- 最後のメッセージ: `tail -c 500000 "$FILE" | jq ...`

### Step 4: 結果の出力

マッチしたセッションを更新日時の降順で一覧表示する:

```
| 日付 | セッションID | msgs | 目的 |
```

各セッションについて:
- 目的（最初のユーザーメッセージから要約）
- 最後のやり取り内容
- フルセッションID（resume用）

マッチが0件の場合は「該当セッションなし」と報告する。

## 注意事項

- セッションログはユーザーのプライベートデータ。外部送信は絶対に行わない
- 結果は簡潔に。各セッションの要約は2-3行以内
- ファイルの作成・編集は行わない（検索・表示のみ）
