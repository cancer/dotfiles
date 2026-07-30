# レポート入力の作り方と渡し方

`collect_metrics.py` はテストを実行しない。ここに挙げたレポートは CI が既に出力しているものを使うのが前提であり、無い場合は該当コマンドを出力に記載する（自分で実行しない。実行するかどうかは読み手が決める）。

## TypeScript / JavaScript

| 種別 | 生成コマンド | 渡す引数 |
|---|---|---|
| 実行結果・実行時間 | `vitest run --reporter=json --outputFile=reports/vitest.json` | `--test-json reports/vitest.json` |
| 同（Jest） | `jest --json --outputFile=reports/jest.json` | `--test-json reports/jest.json` |
| カバレッジ (istanbul) | `vitest run --coverage --coverage.reporter=json` → `coverage/coverage-final.json` | `--coverage-json coverage/coverage-final.json` |
| カバレッジ (LCOV) | `vitest run --coverage --coverage.reporter=lcov` → `coverage/lcov.info` | `--coverage-lcov coverage/lcov.info` |
| ミューテーション | `npx stryker run --reporters json` → `reports/mutation/mutation.json` | `--mutation-json reports/mutation/mutation.json` |

`coverage-summary.json`（json-summary）には行情報が無いため、変更行との突き合わせには使えない。`coverage-final.json` か LCOV を使う。

## Rust

| 種別 | 生成コマンド | 渡す引数 |
|---|---|---|
| 実行結果・実行時間 | `cargo nextest run --message-format libtest-json > reports/nextest.jsonl`（要 `NEXTEST_EXPERIMENTAL_LIBTEST_JSON=1`） | `--nextest-json reports/nextest.jsonl` |
| 同（標準） | `cargo test -- -Z unstable-options --format json --report-time > reports/test.jsonl`（nightly） | `--nextest-json reports/test.jsonl` |
| カバレッジ | `cargo llvm-cov --lcov --output-path reports/lcov.info` / `cargo tarpaulin --out Lcov` | `--coverage-lcov reports/lcov.info` |
| ミューテーション | `cargo mutants --json`（`mutants.out/outcomes.json`） | `--mutation-json mutants.out/outcomes.json` |

## 実行間のばらつき・不安定さ

`--test-json` / `--nextest-json` を**2 件以上**渡したときだけ、同一テストの結果不一致（`unstable_status`）と実行時間のばらつき（`duration_variance`）を検出する。1 件だけでは `not_measured` に「複数実行間のばらつき」が入る。

有用な組み合わせ:

- CI の直近 N 回分のレポート（同一条件の反復）
- 単独実行のレポートと全体実行のレポート（実行順序・共有状態の影響を切り分ける）
- 直列実行のレポートと並列実行のレポート（並列時のリソース競合を切り分ける）

これらを取得するコマンド（`vitest run --sequence.shuffle`, `vitest run --no-file-parallelism`, `cargo nextest run --test-threads=1` など）はユーザーに提示し、実行するかどうかはユーザーが決める。

## パス表記の揺れ

レポート内のパスが絶対パスでも、`collect_metrics.py` はリポジトリルート相対へ正規化して `targets.json` と突き合わせる。突き合わせ結果が空で、かつカバレッジファイル数が 0 でない場合は、レポートが別のリポジトリルートで生成された可能性を疑う（`changed_scope` が空であることを「未検証行なし」と読み替えてはいけない）。
