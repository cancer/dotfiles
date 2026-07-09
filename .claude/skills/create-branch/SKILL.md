---
name: create-branch
description: プロジェクトのブランチ戦略に従って作業ブランチを作成する。実装やissue対応の着手時、「ブランチを切って」と頼まれた場面で使う
model: haiku
allowed-tools: Bash, Read, Glob, Grep
user-invocable: true
---

## 実行手順

1. プロジェクトのブランチ戦略を探す
   - CLAUDE.md、CONTRIBUTING.md、docs/ 等にブランチ命名規則の記載がないか確認する
2. ブランチ戦略が見つかればそれに従い、見つからなければフォールバック規則で作業ブランチを作成する

## フォールバック命名規則

プロジェクトにブランチ戦略の定義がない場合に使用する。

- 形式: `topic/<issue-number>/<短い説明>`（例: `topic/42/add-dark-mode`）
- issue番号が不明な場合: `topic/<短い説明>`（例: `topic/fix-login-redirect`）
- `<短い説明>` は英語・ケバブケースで簡潔に
