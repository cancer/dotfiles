---
max_turns: 30
timeout_seconds: 900
---

あなたは Claude Code の主スレッドで、dev-workflow スキルが次の引数で呼ばれました。Codex への委任・ペイン操作・git 操作・worktree 作成は一切行わず、スキルを読んだうえで、このあと行う工程（発注内容、検収で回すレビューと周回、拾う指摘、成果物の確定、完了報告）を run-plan.md に書いてください。ループを抜けて呼び出し側へ返す場面なら、返す内容を return.md に書いて終えてください。ユーザーへの質問はしないでください。

引数: /Users/cancer/.claude/skills/dev-workflow/evals/files/plan-help.md --task T2 --effort mid

状況:
- feature/counter-json ブランチと、そのブランチから main への PR #42 がすでにある。PR URL は https://github.com/example/counter/pull/42 である。
- main との競合はない。
- p1_json_output はすでに満たされている。feature/counter-json 上で実行した python3 src/counter.py --json の標準出力は、count が 7 の JSON オブジェクト 1 行だった。
- PR の CI は失敗している。watch-ci の報告は、チェック名 lint、種別 lint、原因 src/counter.py の未使用 import os、ログ抜粋 src/counter.py:4:1 F401 'os' imported but unused である。他の CI チェックは失敗していない。
