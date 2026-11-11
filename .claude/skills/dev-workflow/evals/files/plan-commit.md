# タスク定義: counter.py にバージョン表示を追加する

## タスク

### T1: --version 出力の追加
- 対象: src/counter.py, tests/test_counter.py
- 完了条件:
  - p1_version: `python3 src/counter.py --version` が標準出力に `counter 1.0.0` を出し、終了コード 0 で終わる
  - p2_deliverable: `feature/counter-version` ブランチにこのタスクの変更がコミットされている
- 契約: なし

## 契約
なし

## 検証方法
- `python3 -m unittest discover -s tests -v`
