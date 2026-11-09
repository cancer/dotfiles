---
max_turns: 30
timeout_seconds: 900
---

あなたは Claude Code の主スレッドで、dev-workflow スキルが次の引数で呼ばれました。Codex への委任・ペイン操作・git 操作は一切行わず、スキルを読んだうえで、このタスクの検収（品質の評価・改善）の工程で何を・どの順で・何周行うか、統合後レビューを行うか、完了報告に何を書くかを review-plan.md に書いてください。ユーザーに確認すべき場面なら、確認内容を response.md に書いて終えてください。

引数: owner/repo#12（src/counter.py に --help を追加する issue。タスクは 2 つに分かれ、依存あり） --effort mid
