---
name: package-research
description: プロジェクトの依存パッケージ更新を調査し、変更点・破壊的変更・影響度をレポートする。「パッケージを更新できる?」「このライブラリ上げて大丈夫?」「依存を調べて」と頼まれた場面で使う。一般的な技術調査は research の領分
model: sonnet
allowed-tools: Bash, Read, Glob, Grep, Agent, WebFetch, WebSearch, mcp__context7__resolve-library-id, mcp__context7__get-library-docs
user-invocable: true
argument-hint: "[パッケージ名...]"
---

# パッケージアップデート調査スキル

プロジェクトのパッケージのアップデート状況を調査し、レポートする。

## 引数
$ARGUMENTS

- 引数なし → アップデート可能な全パッケージを調査
- パッケージ名指定 → 指定されたパッケージのみ調査

## 手順

### 1. パッケージマネージャの検出

プロジェクトルートのファイルから自動検出する：

| ファイル | パッケージマネージャ |
|---|---|
| `package-lock.json` | npm |
| `pnpm-lock.yaml` | pnpm |
| `yarn.lock` | yarn |
| `bun.lockb` / `bun.lock` | bun |
| `Cargo.toml` / `Cargo.lock` | cargo |
| `go.mod` / `go.sum` | go |
| `requirements.txt` / `pyproject.toml` / `Pipfile` | pip/poetry/pipenv |
| `Gemfile` / `Gemfile.lock` | bundler |
| `composer.json` / `composer.lock` | composer |

複数検出された場合はすべて対象とする。

### 2. アップデート可能なパッケージの一覧取得

各パッケージマネージャのコマンドで一覧を取得する：

- **npm**: `npm outdated --json`
- **pnpm**: `pnpm outdated --format json`
- **yarn**: `yarn outdated --json`
- **bun**: `bun outdated`
- **cargo**: `cargo outdated`（要 cargo-outdated）
- **go**: `go list -m -u all`
- **pip**: `pip list --outdated --format json`
- **poetry**: `poetry show --outdated`
- **bundler**: `bundle outdated`
- **composer**: `composer outdated --format json`

コマンドが失敗した場合（ツール未インストール等）はユーザーに報告して続行する。

引数でパッケージが指定されている場合は、一覧から該当パッケージのみをフィルタする。

### 3. 各パッケージの変更内容を調査

アップデート可能なパッケージごとに以下を調査する（Agentで並列実行すること）：

- **CHANGELOG / リリースノート**: GitHubリポジトリのリリースページやCHANGELOGファイル
- **破壊的変更（Breaking Changes）**: メジャーバージョンアップの場合は特に重点的に
- **マイグレーションガイド**: 公式に提供されている場合

調査にはWeb検索やGitHub API（`gh` コマンド）を活用する。

### 4. レポート出力

以下の形式でレポートする：

```
## パッケージアップデート調査結果

### [パッケージ名] current → latest
- **種別**: major / minor / patch
- **破壊的変更**: あり / なし
- **主な変更点**:
  - ...
- **マイグレーション作業**: 必要 / 不要
  - （必要な場合、具体的な手順）
- **影響度**: 高 / 中 / 低
- **参考リンク**: ...
```

影響度の基準：
- **高**: 破壊的変更あり、マイグレーション作業が必要
- **中**: 非推奨APIの削除予告、動作変更の可能性あり
- **低**: バグ修正・パッチのみ

### 5. サマリー

最後に全体のサマリーを出力する：
- アップデート可能なパッケージ総数
- 影響度別の内訳（高/中/低）
- 推奨アクション（優先的にアップデートすべきもの等）
