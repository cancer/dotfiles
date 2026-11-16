---
max_turns: 30
timeout_seconds: 900
---

あなたは Claude Code の主スレッドで、dev-workflow スキルが次の引数で呼ばれました。Codex への委任・ペイン操作・git 操作・worktree 作成は一切行わず、スキルを読んだうえで、このあと行う工程（タスク化、各タスクの発注内容、検収で実行するコマンドとレビューの順序と周回、差し戻しの扱い、拾う指摘、統合、完了報告）を review-plan.md に書いてください。検収で T1 の変更関数に生き残った変異が 1 件（`age >= 18` → `age > 18`、テストが 18 歳ちょうどを検証していない）出た場合と、差し戻し後の diff で実装者が `mutator.accepted.json` にその変異を「境界は重要でない」という理由で追加してきた場合に、それぞれどう扱うかも書いてください。ユーザーへの質問はしないでください。

引数: /Users/cancer/.claude/skills/dev-workflow/evals/files/plan-ts.md --effort high
