---
name: review-respond
description: PRのレビューコメントを確認し、コード修正とレビュー対応コメントの投稿を行う
argument-hint: <pr-url or number>
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Skill
user-invocable: true
---

指定されたPRのレビューコメントを確認し、対応してください。

## 引数
$ARGUMENTS

## 引数の形式

以下のいずれかの形式でPRを指定できます：

1. **GitHub URL**: `https://github.com/owner/repo/pull/123`
2. **番号のみ**: `123`（現在のリポジトリのPRとして扱う）

## 実行手順

### 1. PRの情報収集

#### 1-1. PR基本情報の取得
```bash
gh pr view <number> --repo <owner/repo> --json number,title,headRefName,baseRefName,state,body
```

#### 1-2. レビューコメントの取得

**必須要件: 各コメントスレッドの `isOutdated`（古いコードへのコメントか）と `isResolved`（解決済みか）を取得すること。** これらの情報がないと、対応すべきコメントの判別ができない。

現状、`isOutdated` / `isResolved` を取得できるのはGraphQL APIのみ（REST APIの `pulls/{number}/comments` では取得不可）。`gh` コマンドで直接取得できるようになればそちらを使ってよい。

```bash
gh api graphql -f query='{
  repository(owner: "<owner>", name: "<repo>") {
    pullRequest(number: <number>) {
      reviewThreads(first: 100) {
        nodes {
          id
          isResolved
          isOutdated
          comments(first: 20) {
            nodes {
              body
              path
              line
              author { login }
              createdAt
            }
          }
        }
      }
    }
  }
}' --jq '.data.repository.pullRequest.reviewThreads.nodes[]
  | select(.isOutdated == false and .isResolved == false)
  | {id: .id, path: .comments.nodes[0].path, line: .comments.nodes[0].line, comments: [.comments.nodes[] | {author: .author.login, body}]}'
```

このフィルタにより **未解決かつ最新のコメントのみ** を取得する。

#### 1-3. PRに含まれるファイル一覧
```bash
gh pr diff <number> --repo <owner/repo> --name-only
```

### 2. レビューコメントの分析

各レビューコメントについて以下を判断する：

- **対象ファイルが現在のPRに含まれているか**（`--name-only` の結果と照合）
  - PRに含まれないファイルへのコメントは**対応不要**
- **コメントの意図を正確に読み取る**
  - コメント全体を読み、提案されているすべての変更点を把握する
  - 「AよりBの方がいい」のような提案では、A→B の変更だけでなく、それに付随して必要になる変更も考慮する
  - 具体的なコード例やAPI名が示されている場合は、それを尊重する
- 対応方針：
  - **修正する**: バグ、明確な改善（コードを修正）
  - **質問する**: 設計判断が必要、意図が不明確（ユーザーに確認）
  - **対応しない**: 設計上の意図、スコープ外、既存仕様の移植（理由を明記）

**報告**: 分析結果を `comment-issue` スキルを使ってPRにコメントとして投稿する（署名付き）。「質問する」に分類したものはコメント内で質問を明記し、ユーザーの判断を仰ぐ。

### 3. コード修正

- PRのブランチに切り替える
- 対応するファイルを読み込み、レビュー指摘に従って修正
- `write-code` スキルの方針に従って実装する

#### 追加の厳守事項

- **PRに含まれるファイルのみ修正すること**
- **レビューで指摘された箇所のみ修正すること**（ただし以下の「類似実装の確認」は例外）

#### 類似実装の確認

人間のレビュアーは怠惰なので、似たような実装が複数箇所にあっても、コメントは1箇所にしか残さない。各レビューコメントに対応する際、以下を行うこと：

1. コメントが付いた箇所と**類似の実装パターン**がPR内の他の箇所にないか確認する（同一ファイル内・他の変更ファイル内の両方）
2. 類似箇所が見つかった場合、同じレビュー指摘が**適用すべきかどうか**をコンテキストを踏まえて判断する
3. 適用すべきと判断した場合は同様の修正を行い、レビュー対応サマリーにもその旨を記載する

### 4. 修正の検証

`write-code` スキルの検証手順を実行する。

### 5. ユーザーへの修正内容確認

**コメント投稿前に、必ずユーザーに修正内容を確認してもらう。** 修正内容の差分を示し、問題がないか確認を取る。

### 6. インラインレビューコメントへの返信

各レビュースレッドに対して、対応結果をインラインで直接返信する。**`comment-issue` スキルは使用しない。**

以下のGraphQL mutationを使用して、各スレッドに返信を投稿する：

```bash
gh api graphql -f query='mutation {
  addPullRequestReviewThreadReply(input: {
    pullRequestReviewThreadId: "<thread_id>",
    body: "<reply_body>"
  }) {
    comment { id body }
  }
}'
```

`<thread_id>` にはステップ1-2で取得したスレッドの `id` を使用する。

#### 返信内容

対応方針に応じて以下の形式で返信する：

- **修正した場合**: 修正内容を簡潔に記載
- **対応しない場合**: 理由を明記
- **質問した場合**: ユーザーとの確認結果を記載

#### 署名

各返信の末尾に以下の署名を必ず追加すること：

```
---
🤖 *This comment was posted via [Claude Code](https://claude.ai/claude-code)*
```

### 7. レビュー対応サマリーコメントの投稿

ユーザーの確認が取れた後、`comment-issue` スキルの形式に従いPRにサマリーコメントを投稿する：

```markdown
## レビュー対応

### 対応済み

| # | コメント | 対応内容 |
|---|---------|---------|
| ... | ... | ... |

### 対応しない（理由あり）

| # | コメント | 理由 |
|---|---------|------|
| ... | ... | ... |

---
🤖 *This comment was posted via [Claude Code](https://claude.ai/claude-code)*
```

### 8. コミット・プッシュ

変更をコミットしてプッシュする。

## 注意事項

- PRに含まれないファイルへのレビューコメントは修正しないこと
- 対応しない判断をする場合は必ず理由を明記すること
- コメント投稿時は必ず末尾に署名を含めること
- **`isOutdated` / `isResolved` を必ず取得すること**（取得手段は問わないが、現状はGraphQL APIのみ対応）
- **レビュー対応コメントの投稿はすべての修正がユーザーに承認された後に行うこと**
- **指示にない変更を追加しないこと**
