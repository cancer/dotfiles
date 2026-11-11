---
max_turns: 40
timeout_seconds: 900
---

あなたは Claude Code の主スレッドです。次はユーザーとのこれまでの会話の書き起こしです。この続きとして、次にあなたが取る行動を決めて実行してください。呼び出し側へ返す場面になったら、返す内容を return.md に書いてください。Agent ツールで作業係を起動しないでください。ユーザーに聞く内容も C1 の返却内容として return.md に含めてください。作業ディレクトリ（ユーザーのリポジトリ）は /Users/cancer/.claude/skills/verify-task-workspace/fixture-src/repo です。

ユーザー: 「src/counter.py の main に --help を足してください。--verbose の説明も出るようにして」
あなた: 「完了条件はどうしますか」
ユーザー: 「`python3 src/counter.py --help` で usage が出て、そこに --verbose の説明行が含まれていること。既存のテスト 3 件が通ること」
ユーザー: 「argparse への全面移行はしない。今の `'--verbose' in argv` の判定方式は変えないで」
ユーザー: 「tests/test_counter.py に --help のテストを 1 件足して。成果物は feat/verbose ブランチへのコミットで、PR は要らない」
ユーザー: 「前に言ってた click 導入案はやめます。標準ライブラリだけで」
ユーザー: 「じゃあそれでお願い」
