# Rust 系統

## 骨組み

```bash
cargo init --lib <name>
cd <name>
```

`--lib` を使う理由は、`--bin` が吐く `main.rs`（`println!` だけでテストなし）はカバレッジ対象になるがテストで覆えないため、閾値に引っかかることである。ライブラリとして始め、バイナリが必要になった時点で `src/main.rs` を足す。

## 差分

```bash
cargo install cargo-llvm-cov --locked   # 未インストールの場合のみ
cargo install cargo-mutants --locked    # 未インストールの場合のみ
rustup component add rustfmt clippy
mkdir -p .github/workflows && cp <skill>/assets/ci-rust.yml .github/workflows/quality.yml
cat <skill>/assets/gitignore-rust >> .gitignore
```

`cargo-llvm-cov` を選ぶ理由は、閾値を落とすフラグ（`--fail-under-lines` / `--fail-under-regions` / `--fail-under-functions`）が公式 README に列挙されており、macOS aarch64 の prebuilt binary があって安定版 Rust で動くことである（https://github.com/taiki-e/cargo-llvm-cov ）。

## placeholder

`src/lib.rs` の生成物（`add` 関数とそのテスト）は hello-world 相当の実装コードなので消す。ただしテストは1本残す——`cargo test` はテストが 0 件でも exit 0 になるため、テストが実際に実行されていることを終了コードで確かめられなくなる。

`src/lib.rs`:

```rust
#[cfg(test)]
mod tests {
    // 足場のテスト。最初の実装で差し替える。
    #[test]
    fn placeholder() {
        assert!(true);
    }
}
```

## 検査（すべて exit 0 であること）

```bash
cargo fmt --check
cargo clippy -- -D warnings
cargo test
mkdir -p reports && cargo llvm-cov --lcov --output-path reports/lcov.info --fail-under-lines 90
```

`cargo llvm-cov` の `--fail-under-lines` が**カバレッジ対象 0 行のときどう振る舞うかは未検証**である（vitest は分母 0 を `Unknown%` として閾値判定の対象外にし exit 0 になるが、llvm-cov で同じとは限らない）。0 行で失敗する場合は、その事実を報告し、閾値をコミット後の最初の実装まで外すか、`--fail-under-lines` を CI 側だけに置くかをユーザーに確認する。**黙って閾値を下げてはいけない。**

型検査に相当するものは Rust ではコンパイル自体（`cargo test` / `cargo clippy` に含まれる）なので、独立した項目は持たない。

## ミューテーションテスト

CI では走らせず、手で実行できる状態にする（全変異ごとにスイートを回すため実行時間が読めない）。

```bash
cargo mutants --json   # 出力は mutants.out/outcomes.json
```

これは `test-review --mutation-json mutants.out/outcomes.json` の入力になる。ただし cargo-mutants の JSON は beta 扱いでスキーマが公開されていないため、突き合わせが空になる可能性がある。
