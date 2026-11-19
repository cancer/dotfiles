---
name: proposal
description: 商談に持っていく提案スライドを作りたい、「○○社への提案資料のたたき台」を作りたい場合に使う。商談後の詳細提案書、見積明細、技術記事（article-writer）は対象外。
---

# 商談前提案スライドの進行

このスキルは、案件ごとの作業場所 C0 を正本にして、提案内容 A、レビュー C、スライド B を順番に進める。サブスキルは主スレッドの Skill ツールで読み込む。Artifact ツールが主スレッドにあるため、各 Artifact の公開と URL の記録も主スレッドで行う。

## C0 を作る

依頼を受けたら、`~/.claude/proposals/<YYYYMMDD>-<client-slug>/` を案件の作業場所 C0 にする。日付は実行日の `YYYYMMDD`、`client-slug` は依頼元の英語名またはローマ字表記から作る英小文字ケバブケースにする。

1. C0 と `deck/`、`review/` を作る。
2. ユーザーの依頼文を受け取ったまま `request.md` に保存する。
3. `artifacts.json` を `{"outline":"","deck":""}` で初期化する。Artifact を公開したら対応する URL を記録する。
4. `loop-history.json` を `{}` で初期化する。

`loop_state.py` は review ごとの指摘 ID 列を `outline` と `deck` に分けて履歴へ追記する。同じ target・同じ周回番号の review で再実行した場合は追記せず、その周回の記録を置き換えるので、失敗後のやり直しで連続回数は増えない。

## A → 承認① → C⇄A

1. 主スレッドで `proposal-outline` を読み込み、C0 を渡して実行する。`outline.md` と `industry-notes.md` はこのスキルが作る。
2. `questions.md` が存在して内容が空でなければ、記載された質問をユーザーに聞いて停止する。空か存在しない場合だけ次へ進む。
3. `proposal-outline` の最終手順で Artifact が公開され、URL が `artifacts.json` の `outline` に記録されていることを確認する。URL が無ければ、この主スレッドで公開して記録する。
4. 見出しの列と Artifact URL をユーザーに示し、骨子の承認①を求める。承認①以外の内容について、ユーザーに承認を求めない。
5. 承認①の後に outline のレビュー周回を行う。周回番号は 1 から始める。

周回ごとに、まず C6 の `review.py` を呼ぶ。

```bash
python3 /Users/cancer/.claude/skills/proposal-review/scripts/review.py \
  --workdir <C0> --target outline --round <n> \
  --out <C0>/review/outline-round-<n>.json
```

終了コードが 0 以外なら、標準エラーの理由を報告して停止する。指摘の有無を見て独自に合否を決めない。終了コード 0 のときだけ、ループ判定スクリプトを実行する。

```bash
python3 /Users/cancer/.claude/skills/proposal/scripts/loop_state.py \
  --review <C0>/review/outline-round-<n>.json \
  --history <C0>/loop-history.json
```

判定 JSON の `next` に従う。

| `next` | 行動 |
|---|---|
| `done` | outline のループを終え、B へ進む。 |
| `fix` | `findings` を C5 JSON のまま `proposal-outline` の修正モードへ渡す。提供内容・約束・費用を増やす改善案は自動修正せず、`ask` としてユーザーに聞いて停止する（F1）。修正後に `questions.md` が空でない場合も質問して停止する。続行できる場合は、最新の `outline.md` を Artifact に反映し、`artifacts.json` の `outline` URL を更新する。 |
| `ask` | `findings` の内容をユーザーに聞いて停止する。 |
| `stalled` | `stalled_ids` を示して停止する。同じ指摘が 3 回連続のレビューに出た状態である。 |

## B → 承認② → C⇄B

1. `proposal-deck` を主スレッドの Skill ツールで読み込んで実行する。B は毎回 C0 の `outline.md` を読み直す。
2. B が `deck-gaps.md` に内容を書いた場合は、その時点で止まり、記載された不足をユーザーに示す。空か存在しない場合は続ける。
3. 挿絵の方向を確認できる試作を 1 枚作り、試作と方向性をユーザーに示して承認②を求める。承認②以外の内容について、ユーザーに承認を求めない。
4. 承認②の後、`proposal-deck` を再開して残りのスライドを作る。`deck-gaps.md` が空でない場合は止める。
5. 完成した deck のレビュー周回を行う。周回番号は 1 から始める。

周回ごとに、まず C6 の `review.py` を呼ぶ。

```bash
python3 /Users/cancer/.claude/skills/proposal-review/scripts/review.py \
  --workdir <C0> --target deck --round <n> \
  --out <C0>/review/deck-round-<n>.json
```

終了コードが 0 以外なら、標準エラーの理由を報告して停止する。終了コード 0 のときだけ、同じループ判定スクリプトを呼び出す。

| `next` | 行動 |
|---|---|
| `done` | deck のループを終え、完成を報告する。 |
| `fix` | C5 の指摘を次の表どおりに渡す。修正後に questions.md または deck-gaps.md が空でない場合は停止する。 |
| `ask` | `findings` の内容をユーザーに聞いて停止する。 |
| `stalled` | `stalled_ids` を示して停止する。 |

| deck の指摘 | 渡す先と次の行動 |
|---|---|
| `R-deck-*` または `R-format` | `proposal-deck` の修正モードへ渡す。 |
| `J-*` または `reader.*` | `proposal-outline` の修正モードへ渡す。outline を直した後、Artifact を最新化して `artifacts.json` の `outline` URL を更新し、`proposal-deck` で最新の `outline.md` に再同期する。 |
| その他の `R-*` | `proposal-outline` の修正モードへ渡す。デッキの文言は outline から変えず、outline を直した後に deck を再同期する。 |

## 完成

outline と deck の両方のレビューが `done` になったら、`artifacts.json` に outline と deck の Artifact URL が記録されていることを確認し、deck の Artifact URL をユーザーに報告する。
