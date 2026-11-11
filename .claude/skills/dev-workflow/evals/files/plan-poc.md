# タスク定義: PoC — tomllib で設定ファイルを読めるか

## タスク

### T1: tomllib 読み込みの実測
- 対象: poc/read_toml.py, config.toml
- 完了条件:
  - p1_measure: `python3 poc/read_toml.py config.toml` を実行し、標準出力と終了コードをそのまま返す
- 契約: なし

## 契約
なし
