---
name: watch-ci
description: GitHub PR の CI を監視し、完了結果と失敗時のログに基づく情報を報告する
argument-hint: <PR URL または番号> [--interval <seconds>]
model: sonnet
allowed-tools: Bash, Read
user-invocable: true
---

指定された PR の CI 完了を待ち、結果を報告する。

## 引数

$ARGUMENTS

## 引数の形式

- **PR 指定**（必須）: GitHub URL（`https://github.com/owner/repo/pull/123`）または PR 番号（現在のリポジトリの PR として扱う）
- `--interval <seconds>`: CI の待機時に使う間隔（デフォルト: 30 秒）

## 実行手順

1. 引数から PR 番号、`owner/repo`、`--interval` を確定する。URL の場合は URL から番号とリポジトリを得る。番号だけの場合は `gh repo view --json nameWithOwner --jq .nameWithOwner` で現在のリポジトリを得る。`--interval` が省略された場合は 30 を使う。
2. `gh pr view <番号> --repo <owner/repo> --json number,url,headRefName,headRefOid` で PR の URL、head ブランチ、head commit を得る。
3. 次の 1 コマンドで CI の完了を待つ。コマンドがチェックの完了まで待機するため、自前のポーリングは行わない。GitHub REST API を直接呼び出さない。

   ```bash
   gh pr checks <番号> --repo <owner/repo> --watch --fail-fast --interval <interval>
   ```

4. すべてのチェックが成功した場合は、下記「報告形式」の成功時の形式で報告して終了する。
5. 失敗したチェックがある場合は、失敗した run と job step のログを調べ、下記「報告形式」の失敗時の形式で報告して終了する。コードや PR に手を加える手順は行わない。

## 失敗時のログ調査

1. `gh pr checks` の結果から失敗したチェック名を特定する。
2. PR の head commit に対応する run を次のコマンドで確認する。

   ```bash
   gh run list --commit <head-sha> --repo <owner/repo> --json databaseId,status,conclusion,name
   ```

3. 失敗した run の job と step を確認し、失敗ログを読む。

   ```bash
   gh run view <run-id> --repo <owner/repo> --json jobs --jq '.jobs[] | select(.conclusion == "failure") | {name, steps: [.steps[] | select(.conclusion == "failure")]}'
   gh run view <run-id> --repo <owner/repo> --log-failed
   ```

4. 失敗種別は、チェック名と run・job・step の情報に基づいて `lint` / `typecheck` / `test` / `build` / `E2E` / `other` のいずれかに分類する。分類を特定できない場合は `other` とする。
5. 原因欄にはログに記載された事実だけを書く。ログから原因を特定できない場合やログを取得できない場合は、その状態を明記し、推測で補わない。ログ抜粋は原因の根拠となる行をそのまま示す。該当するログが無い場合はその旨を記す。

## 報告形式

成功時:

```text
結果: 成功
PR: <PR URL>
```

失敗時:

```text
結果: 失敗
PR: <PR URL>
失敗したチェック:
- チェック名: <名前>
  種別: lint | typecheck | test | build | E2E | other
  原因: <ログから読み取れた事実、または特定できない旨>
  ログ抜粋: <該当行、または取得できない旨>
```

失敗したチェックが複数ある場合は、チェックごとに項目を記す。この報告を出して終了する。
