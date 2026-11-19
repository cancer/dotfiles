---
name: proposal-deck
description: 「承認済みの提案骨子をスライドにして」「この骨子から提案資料を作って」など、proposal-outline が作成した outline.md から商談前のスライドを作る依頼で使う。提案内容をまとめるだけなら proposal-outline、案件全体を進めるなら proposal を使う。
---

# proposal-deck

入力ファイルは `~/.claude/proposals/<YYYYMMDD>-<client-slug>/outline.md` だけとする。C1 の契約に沿ったスライドファイルへ変換し、見た目を整えてもスライドの内容はこのファイルだけから取る。

## 入力と不足時の停止

1. 作業のたびに、C0 の `outline.md` をファイルから読み直す。前の実行で読んだ内容や会話中の複製を使わない（F12）。
2. `outline.md` のタイトル、S番号、見出し、本文を順に確認する。スライドに載せる文字列は見出しと本文だけとし、内容の出典は `outline.md` だけにする（state.txt request / C1）。
3. C1 の内容が足りない、挿絵の描写内容が空、または Markdown 表をそのまま表として扱えない場合は、`C0/deck-gaps.md` に該当する S番号と A に補ってほしい内容を書き、そこで停止する。欠けた内容を推測して埋めず、デッキを作らない（state.txt request / C1）。

## C4 のデッキを作る

入力に不足がなければ、次の順で進める。

1. 主スレッドで Slides 型 Artifact（`https://claude.ai/artifact/8jTsAFQMFDb2oA8MsPJ2eL`）を publish し、返された型の指示に従う（state.txt request / C4）。
2. Artifact の read で組織のデフォルト DS（`https://claude.ai/artifact/JsoP6AVQXpfqcfppEyxsBC`）を読み、そのルールを適用する（state.txt request）。
3. 1 枚につき 1 つの主張を置き、C1 の各スライドを同じ順で作る。見出しは outline の見出し文を使い、本文は outline の箇条書き・表・挿絵指定のいずれかを使う。
4. C4 に従い、ファイル書き込みツールで直接 `C0/deck/project/deck.json` と `C0/deck/project/slides/<id>.html` を書く。スクリプトによる生成は行わない（state.txt request / C4）。

スライド id は outline の `S<n>` を小文字にした `s<n>` とし、`deck.json` の `order` は outline の順序にする。`deck.json` は `v: 4`、outline のタイトル、`order` を持たせ、他の必須項目は Slides 型 Artifact の指示に従う。各 HTML は該当 id の `<section>` を 1 つだけ持つ。ノートを置く場合は `<aside>` をその section の最後の子要素にする。ロゴ、ページ番号、社名などの固定表示要素には `data-fixed` を付ける（C4）。

見出しと本文の文言は outline から一字も変えない。言い換え、要約、表記修正、文の追加・削除をしない。可視文言を変えてよい例外は、C4 の `data-fixed` を付けた固定要素だけとする（F7 / C1 / C4）。スライド枚数の数値上限は設けず、outline の全スライドを作る（state.txt request）。

## 挿絵

outline に挿絵指定がある場合だけ、次の順で進める。

1. outline 順で最初の挿絵を 1 枚試作する。画像生成は `delegate-to-codex` を使って herdr のペイン内の Codex に imagegen を依頼する方法だけを使う。herdr の外では別の方法で生成せず、生成していない画像を生成済みと報告しない（state.txt request）。
2. 試作を見せて、方向性の承認②をユーザーから受ける。承認②を受けるまでは残りの挿絵を作らない（state.txt request）。
3. 承認後、残りの挿絵を同じ経路で依頼する。

依頼文は [`references/illustration-request.md`](references/illustration-request.md) の雛形を使う。画像の配置と埋め込み方は Slides 型 Artifact が返す指示に従う（state.txt request / C4）。
