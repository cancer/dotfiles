---
name: run-implement
description: implement の依頼をタスク分割・並列作業・マージの順に作業係へ渡す companion 用手順
argument-hint: <judge-request の verdict.json のパス> <state.txt のパス>
allowed-tools: Read, Write, Agent, SendMessage, TaskCreate, TaskUpdate, TaskList
user-invocable: false
---

引数の `verdict.json` を読み、judge-request が `implement` の `ready` を返したことを確認してから読む。2 番目の引数は `state.txt` のパスである。作業係を起動する順序と分岐だけを指示する。**run-implement 自身はコードの変更・検収・マージを行わない。**

1. `/Users/cancer/.claude/skills/define-tasks/SKILL.md` と `/Users/cancer/.claude/skills/run-implement/references/task-format.md` を読ませる Plan サブエージェントを起動し、`state.txt` のパスを渡す。
2. タスク定義が返ったら、companion は会話から effort を判断する。各タスクについて `/Users/cancer/.claude/skills/dev-workflow/SKILL.md` を読ませ、`<タスク定義ファイルのパス> --task T<n> --effort <effort>` で作業する作業係をバックグラウンドで並列に起動する。完了通知は judge-request の `worker-report.txt` と同じ State に積む。effort の意味は `dev-workflow` の effort 表に従う。
3. 全タスクの完了後、タスク定義ファイルのパス、各タスクの成果物（PR URL またはブランチ名）、effort を渡し、`/Users/cancer/.claude/skills/merge-prs/SKILL.md` を読む作業係を起動する。

## 差し戻しと離脱

- **define-tasks の差し戻し**: 不明点は State 等から解決できるものを補い、judge-request からやり直す。ユーザーでないと確定できない不明点だけをユーザーに聞き、回答を State に積んで judge-request からやり直す。実測が要る仮定は、仮定ごとに成果物の命題を持たない PoC 用タスク定義を作り、`<PoC タスク定義ファイルのパス> --task T<n> --effort low` で `dev-workflow` に渡す。生の出力で合否を判定し、成立で決着したら手順 1 のタスク分割へ戻る。不成立ならユーザーと方針を決め直す。
- **dev-workflow の離脱**: タスク定義を直せば進められる理由なら、define-tasks からやり直す。companion が解決できる入力・環境の問題は解消し、同じ引数（タスク定義ファイルのパス、`--task T<n>`、`--effort <effort>`）で `dev-workflow` を再起動する。ユーザーの判断・操作だけで解決できる場合に限ってユーザーに聞き、回答を State に積んで judge-request からやり直す。それ以外は再起動せず、離脱理由と残した worktree・ブランチを State に記録して状況を報告する。
- **merge-prs の失敗**: CI 失敗または競合なら、原因タスクの `dev-workflow` を同じ引数（タスク定義ファイルのパス、原因タスク ID の `--task T<n>`、選択済みの `--effort <effort>`）で回し直し、全て完了した後に更新後の成果物で `merge-prs` を回し直す。結合レビューの指摘なら、原因タスク ID と根拠を `dev-workflow` の作業依頼に添え、同じ引数（タスク定義ファイルのパス、原因タスク ID の `--task T<n>`、選択済みの `--effort <effort>`）で差し戻し、完了後に更新後の成果物で `merge-prs` を回し直す。

ユーザーに聞くのは、ユーザーでないと解決できないときだけである。承認は求めない。
