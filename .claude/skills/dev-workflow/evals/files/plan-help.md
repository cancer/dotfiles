# タスク定義: counter.py に --json 出力を追加する

## タスク

### T1: 引数解析の実装
- 対象: src/counter_args.py, tests/test_counter_args.py
- 完了条件:
  - p1_parse_args: `parse_args(argv: list[str]) -> dict` を実装し、`--json` の場合はキー `"json": true` を返す
  - p2_deliverable: `feature/counter-args` から `main` への PR が作成され、`main` と競合せず、CI が通っている
- 契約: 提供 C1 / 利用 なし

### T2: --json 出力の追加
- 対象: src/counter.py, tests/test_counter.py
- 完了条件:
  - p1_json_output: `python3 src/counter.py --json` が `{"count": <int>}` の JSON を 1 行で出力する
  - p2_deliverable: `feature/counter-json` から `main` への PR が作成され、`main` と競合せず、CI が通っている
- 契約: 提供 なし / 利用 C1

## 契約

### C1: 引数解析の結果
- 提供: T1 / 利用: T2
- 内容: `parse_args(argv: list[str]) -> dict` を `src/counter_args.py` に置き、`--json` の場合はキー `"json": true` を返す

## 検証方法
- `python3 -m unittest discover -s tests -v`
