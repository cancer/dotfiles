---
max_turns: 30
timeout_seconds: 900
---

あなたは Claude Code の主スレッドで、dev-workflow スキルが次の引数で呼ばれました。Codex への委任・ペイン操作・git 操作・worktree 作成は一切行わず、スキルを読んだうえで、このあと行う工程（タスク化、各タスクの発注内容、検収で回すレビューと周回、拾う指摘、統合、完了報告）を review-plan.md に書いてください。ループを抜けて呼び出し側へ返す場面なら、返す内容を return.md に書いて終えてください。ユーザーへの質問はしないでください。

引数: owner/repo#12（src/counter.py に --help を追加する issue）--effort mid
