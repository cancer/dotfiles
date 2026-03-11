---
name: verify-task
description: ワーカーの成果物が指示通りに完了しているかを検証する（完了チェック特化）
argument-hint: <指示内容> <worktreeパスまたはブランチ名>
allowed-tools: Bash, Read, Glob, Grep
user-invocable: false
---

ワーカーの成果物が指示通りにできているかを検証する。品質レビューではなく、指示の完了チェックに特化。

## 引数
$ARGUMENTS

引数から以下を特定する：
- **指示内容**: ワーカーに何を依頼したか
- **worktreeパスまたはブランチ名**: ワーカーの作業場所

## 検証手順

### 1. 指示突合

1. ワーカーのworktreeで `git diff HEAD~..HEAD` を実行し、コミット済みの変更内容を取得する（コミット数が複数の場合はベースブランチからの差分 `git diff <base>..HEAD` を使う）
2. 変更内容と指示を照合し、以下を確認する：
   - 指示された変更がすべて実施されているか（漏れがないか）
   - 指示にない変更が含まれていないか（過剰な変更がないか）
   - 指示の意図と異なる解釈で実装されていないか

### 2. check/typecheck

worktreeディレクトリで以下を実行する：

1. プロジェクトの lint/check コマンドを実行する（`package.json` や CLAUDE.md の指示を参照）
2. プロジェクトの typecheck コマンドを実行する（存在する場合）
3. エラーがあれば記録する

### 3. 結果レポート

以下の形式で結果を出力する：

```
## 検証結果

### 指示突合
- [ ] 指示された変更がすべて実施されている
- [ ] 指示にない変更が含まれていない

過不足がある場合は具体的に列挙する。

### check/typecheck
- [ ] npm run check: pass/fail
- [ ] npm run typecheck: pass/fail

エラーがある場合は内容を記載する。

### 判定
PASS / FAIL（理由）
```
