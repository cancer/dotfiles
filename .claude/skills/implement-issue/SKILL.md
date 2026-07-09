---
name: implement-issue
model: opus
description: GitHub issue を起点にコード実装からPR作成まで行う。issue番号やURLを添えて「このissueを実装して/対応して」と頼まれた場面で使う。計画だけなら plan、issue を伴わない実装は write-code の領分
argument-hint: <issue-url or owner/repo#number or number>
allowed-tools: Bash, Read, Edit, Write, Glob, Grep, Skill
user-invocable: true
---

指定されたGitHub issueの内容に基づいてコードを実装してください。

## 引数
$ARGUMENTS

## 引数の形式

以下のいずれかの形式でissueを指定できます：

1. **GitHub URL**: `https://github.com/owner/repo/issues/123`
2. **owner/repo#番号**: `anthropics/claude-code#456`
3. **番号のみ**: `123`（現在のリポジトリのissueとして扱う）

## 実行手順

### 1. issueの情報収集

```bash
gh issue view <number> --repo <owner/repo> --json number,title,body,labels,assignees,comments
```

issue本文に加え、コメント欄にも要件や補足がないか確認する。

### 2. 要件の整理

issueの内容を分析し、以下を整理する：

- **何を実装するか**: 具体的な機能・修正内容
- **受け入れ条件**: issue内に記載があればそれを採用、なければ推測して明示
- **影響範囲**: 変更が必要なファイル・モジュールの特定

issueの内容が曖昧または不十分な場合は、ユーザーに確認する。

### 3. タスク規模の判定

要件整理の結果から、タスクの規模を判定する。

**大規模タスク**（以下のいずれかに該当）：
- 変更対象のファイルが多く、独立した複数のサブタスクに分解できる
- 複数の機能領域にまたがる変更が必要
- 実装とは別にレビューや調査など異なる種類の作業が並行して必要

→ `team-manager` スキルを呼び出し、issueの情報を引数として渡して委任する。以降のステップは実行しない。

**小〜中規模タスク**（上記に該当しない）：
→ そのまま次のステップに進む。

### 4. 実装方針の決定

コードベースを探索し、実装方針を決定する。

**方針確認が必要な場合**（以下のいずれかに該当）：
- 複数の実装アプローチが考えられる
- 既存のアーキテクチャに影響する変更
- issueの記載が曖昧で解釈の余地がある

→ ユーザーに実装方針を提示し、承認を得てから次に進む。

**方針確認が不要な場合**（以下のすべてに該当）：
- issueの要件が明確で一意に定まる
- 実装アプローチが自明
- 影響範囲が限定的

→ そのまま実装に進む。

### 5. ブランチ作成

`create-branch` スキルに従って作業ブランチを作成する。

### 6. コード実装

- issueの要件に基づいてコードを実装する
- `write-code` スキルの方針に従って実装する

#### 追加の厳守事項

- **issueの要件に記載された変更のみ実装すること**

### 7. 実装の検証

`write-code` スキルの検証手順を実行する。

### 8. コミット・プッシュ

変更をコミットしてプッシュする。

コミットメッセージに `Closes #<issue番号>` または `Fixes #<issue番号>` を含める。

### 9. PR作成

`create-pr` スキルを使用してPRを作成する。

PR本文にissueへの参照（`Closes #<issue番号>`）を含める。

### 10. issueへのコメント

`comment-issue` スキルを使用して、対象issueにPR作成の報告コメントを投稿する。

```markdown
PRを作成しました: <PR URL>
```

## 注意事項

- issueの要件が不明確な場合はユーザーに確認すること
- issueの要件にない変更を追加しないこと
- 既存のコードスタイル・アーキテクチャに従うこと
