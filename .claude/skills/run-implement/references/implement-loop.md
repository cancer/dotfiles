# implement の流れ（合意版、2026-11-11）

implement の作業は、companion が順序を指示し、作業係が作業・検収・マージを担う。単一タスクの実装と検収は `dev-workflow`、タスクのマージは `merge-prs` が担う。

## 流れ

1. `judge-request` が `implement` の `ready` を返したら、companion は `run-implement` を読み、記載された順序で作業係を起動する。
2. `define-tasks` が State からタスク定義を作る。不明点または実測が要る仮定があれば定義を作らず companion に差し戻す。
3. companion はタスク定義の各タスクについて `dev-workflow` をバックグラウンドで並列に起動する。完了通知を State に積む。
4. 全タスクが完了したら、companion は `merge-prs` を読む作業係を起動して成果物をマージする。

タスク定義の Markdown 形式は [`task-format.md`](task-format.md) に定める。計画の承認は求めない。実測が要る仮定は成果物の命題を持たない PoC 用タスク定義で扱い、`dev-workflow` の effort `low` で実測する。companion が生の出力で合否を判定し、成立で決着したら `define-tasks` に戻る。不成立ならユーザーと方針を決め直す。

`dev-workflow` は各タスクの完了条件を満たす。成果物の命題が PR を求める場合は `dev-workflow` が PR を作成する。全タスクの完了後、`merge-prs` が成果物をマージする。

## effort

effort は品質をどの軸で評価・改善するかを表す。選んだ軸は指摘が無くなるまで回す（上限 3 周）。effort は主スレッドが会話から判断して渡す。

| effort | `dev-workflow` で回す軸 | 拾う指摘 | テスト |
|---|---|---|---|
| low | なし。実装して実測の生の出力を返す | ― | 書かない |
| mid | verify-task、test-review | 重要度 high / mid | テストファースト |
| high | verify-task、test-review、code-review | low まで | テストファースト |

effort `high` では、全マージ後に `merge-prs` が結合 diff のレビューを行う。結合後レビューの観点は `merge-prs` の手順に従う。

- verify-task は「できているか、いないか」の二値なので、拾う範囲の対象外。FAIL・判定不能は常に拾う
- low は PoC 用である。PoC の完了は仮定が決着したことで、成立・不成立のどちらも完了なので、verify-task も回さない

## ループを抜けるとき

次の事態では、タスクの作業を止め、状況を呼び出し側（companion）へ返す。原因がタスク定義にある場合は `define-tasks` に戻る。

- effort が無い、委任経路が使えないなど、入力・環境の不備
- 3 周で収束しない
- 指摘の矛盾が既定の解決順で解けない
- 実装中に契約が成立しないと分かった
- 推論量 max でも進まない
- 指示と反する判断が要る
- サンドボックス外の操作を頭脳が代行しようとして拒否された（権限設定・classifier による拒否）

抜けるときはそのタスクをマージせず、作業中の worktree とブランチを残して返す。タスク定義が直された場合は、検収を通ったタスクも前提が変わって無効になりうるため、companion は全タスクの前提を見直す。

サンドボックス外の操作は、原則として頭脳が代行する。代行しても拒否された操作だけが、上記の抜ける条件になる。

## 後回しにしたもの

- 作業係（dev-workflow を回すサブエージェント）が寝たまま起きない問題の監視。実害は確認済み（過去ログで 9 回）。既存の watchdog の改修が要る
- Codex 側の watchdog の扱い。過去ログでは 43 件中 42 件が誤報
