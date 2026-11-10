# 計画: counter.py に --help と --json を追加する

## Context
- src/counter.py の CLI に --help と --json を足す（owner/repo#12）

## タスク

### T1: --help の追加
- 対象: src/counter.py, tests/test_counter.py
- 完了条件:
  - p1_help_usage: `python3 src/counter.py --help` が usage を表示して終了コード 0 で終わる
  - p2_help_verbose: usage に --verbose の説明行が含まれる
- 契約: 提供 C1 / 利用 なし

### T2: --json 出力の追加
- 対象: src/counter_json.py, tests/test_counter_json.py
- 完了条件:
  - p1_json_output: `python3 src/counter.py --json` が {"count": <int>} の JSON を 1 行で出力する
- 契約: 提供 なし / 利用 C1

## 契約

### C1: 引数解析の結果
- 提供: T1 / 利用: T2
- 内容: `parse_args(argv: list[str]) -> dict` を src/counter.py に置き、キー "verbose": bool, "json": bool を返す

## 検証方法
- `python3 -m unittest discover -s tests -v`
