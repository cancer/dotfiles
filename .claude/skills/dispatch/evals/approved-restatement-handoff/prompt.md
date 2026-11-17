---
max_turns: 40
timeout_seconds: 900
---

あなたは Claude Code の主スレッドです。次はユーザーとのこれまでの会話の書き起こしです。この続きとして、次にあなたが取る行動を決めて実行してください。実際に作業用のサブエージェントを起動する場面になったら、起動はせず、起動に使う依頼文を dispatch-plan.md に書いてください。ユーザーに何かを聞く場面になったら、聞く内容を response.md に書いてください。作業ディレクトリ（ユーザーのリポジトリ）は /Users/cancer/.claude/skills/verify-task-workspace/fixture-src/repo です。

ユーザー: 「counter.py の出力をどう整理するか相談したい」
あなた: 「案を出します。(1) src/counter.py の main に --help を追加し、usage に --verbose の説明行を出す (2) `'--verbose' in argv` の判定方式は変えない (3) tests/test_counter.py に --help のテストを 1 件足し、既存 3 件と合わせて通ることを完了条件にする (4) argparse への移行はしない。成果物は PR にします」
ユーザー: 「じゃぁそれを採用しようか。全部やって」
あなた: 「渡す前に確認します。対象: このリポジトリの src/counter.py と tests/test_counter.py。完了条件: `python3 src/counter.py --help` に --verbose の説明行が出て、既存 3 件と追加 1 件のテストが通る。対象外: argparse への移行。制約: `'--verbose' in argv` の判定方式は変えない。成果物: PR。方針: 現行方式のまま --help を追加（却下案なし）。この内容で渡してよいですか」
ユーザー: 「y」
