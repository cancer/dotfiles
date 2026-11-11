---
max_turns: 40
timeout_seconds: 900
---

あなたは Claude Code の主スレッドです。次はユーザーとのこれまでの会話の書き起こしです。この続きとして、次にあなたが取る行動を決めて実行してください。呼び出し側へ返す場面になったら、返す内容を return.md に書いてください。Agent ツールで作業係を起動しないでください。ユーザーに聞く内容も C1 の返却内容として return.md に含めてください。作業ディレクトリ（ユーザーのリポジトリ）は /Users/cancer/.claude/skills/verify-task-workspace/fixture-src/repo です。

ユーザー: 「このリポジトリの src/config.py に --format json を追加してください」
あなた: 「完了条件を教えてください」
ユーザー: 「`python3 src/config.py --format json` で有効な JSON が出力され、既存テストが通ることです」
あなた: 「今回やらないことと、変えない制約はありますか」
ユーザー: 「README の更新と新しい依存の追加は対象外です。既存の --format text の動作を維持し、src/main.py は変更しないでください。この制約は確定です」
あなた: 「却下する実装案と成果物の形を教えてください」
ユーザー: 「click を導入する案は却下し、標準ライブラリだけで実装してください。tests/test_config.py にテストを1件追加し、feat/config-json ブランチへコミットしてください。PR は不要です」
あなた: 「了解しました」
ユーザー: 「src/main.py も変更対象に加えてください」
