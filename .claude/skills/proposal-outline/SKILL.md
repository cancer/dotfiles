---
name: proposal-outline
description: 「提案の骨子だけ作って」「提案内容をまとめて」など、提案内容の整理を頼まれたときに使う。商談全体を進める proposal、骨子からスライドを作る proposal-deck、技術記事を書く article-writer とは役割を分ける。
---

# 提案内容の骨子を作る

依頼元の業界と依頼内容を理解し、提案の骨子と社内用の業界理解メモを作る。商談前の作業なので、商談で得た内容を前提にしない。

作業場所はオーケストレーターから渡された案件ディレクトリ C0 とする。通常モードでは C0 を使い、レビュー後の修正モードでは C0 と C5 のレビュー結果を使う。成果物は C1 の `outline.md` と C2 の `industry-notes.md`。C0 の `request.md` は依頼文の原文を保持する。

## 作業手順

### 1. 依頼を受け取る

依頼は形式を問わず受け取り、ユーザーに整理し直すよう求めない。C0 の `request.md` に依頼元から受け取った原文を保存する。既に原文が保存されている場合は内容を保ち、要約や言い換えで置き換えない。

次の二項目のうち、欠けているものだけを尋ねる。

- 依頼元企業名
- 相談のきっかけ

両方がそろっていれば追加の入力質問をせず、手順 2 へ進む。どちらかが欠けている場合は不足項目を尋ね、回答が得られるまで手順 2 以降を始めない。ほかに分からない点はこの段階で質問せず、手順 5 の「本日伺いたいこと」に置く。

### 2. 依頼元とその業界を理解する

この工程を最優先する。業界に詳しくない前提で、依頼元の事業、業界構造、依頼内容が関わる業務の流れ、業界用語、業界固有の課題・規制・慣習を調べる。情報源は依頼元の公式情報、業界団体、官公庁の統計・白書、業界紙、同業他社の公開事例とする。

調べ方と C2 の記載形式は [`references/industry-research.md`](references/industry-research.md) に従う。確認できた事実と不明点を分けて C0 の `industry-notes.md` に出典付きで残す。社内用メモ自体はスライドへ載せない（F8、承認済み state.txt のユーザー発言）。依頼内容と無関係な業績・経営方針・ニュースを提案根拠に使わない（F13）。

### 3. 弊社側の情報を読む

`pxgrid-company-context` の `list_docs` で目次を取得し、理念、戦略、開発ポリシー、用語の記事を読む。依頼内容に関係する実績を使う場合は、`works/README.md` と該当実績の `overview.md` を読む。

実績を外向きの提案に使うときは `works/README.md` の `visibility` と `client_public` の開示ルールに従う。`visibility: internal` の実績は、`overview.md` の `external_label` が定める粒度でだけ説明する。出典のない実績内容は補わない。

次の knowledge 原文を `read_knowledge` で読み、要約や社内メモで代替しない。

- `entries/write-for-reader-inference.md`
- `entries/evaluate-information-by-inferability.md`

後段の担当スキルにも、この二つの knowledge 原文をそれぞれ `read_knowledge` で読むよう伝える（承認済み state.txt のユーザー発言）。

### 4. 仮説を立てる

依頼文と業界調査で確認した内容から、依頼の範囲内で「状況 → 課題の仮説 → 弊社のアプローチ」を組み立てる。依頼文に書かれた事実、業界の確認済み事実、提案側の仮説を混同しない。課題仮説は断定せず、確かめたい内容として示す。

依頼内容と無関係な企業情報を根拠にした提案と、依頼外の領域への提案をしない（F13、承認済み state.txt のユーザー発言）。不明な事実は補わず、商談で確認する質問にする。

### 5. 骨子を作る

C1 の形式で C0 の `outline.md` を作る。見出しはスライドで伝える結論を言い切る文にする（F6）。スライドの並びは次の七つの役割を基本とし、役割の順序を保つ。

1. `cover` — 表紙
2. `understanding` — ご相談内容の理解
3. `hypothesis` — 想定される課題（仮説）
4. `approach` — 弊社のアプローチ
5. `why_us` — 弊社に任せる理由
6. `process` — 進め方
7. `questions_next` — 本日伺いたいこと・次の一歩

同じ役割を続けて使ってよい。不明点は `questions_next` に置く。費用を求められた依頼だけ `cost_requested: true` とし、`process` と `questions_next` の間に `cost` の役割を置く。それ以外は `cost_requested: false` とし、`cost` の役割を置かない（承認済み state.txt の手順 5）。費用の概算に必要な前提が足りない場合は、確かめる項目を費用スライドまたは `questions_next` に示す。

`industry-notes.md` は社内用として C2 形式に保ち、スライド本文へ転記しない（F8、承認済み state.txt のユーザー発言）。C0 に質問が残る場合は `questions.md` に記録し、そこで作業を止める。

すべての成果物を確定した最後に、主スレッドで `outline.md` を Artifact として公開し、その URL を C0 の `artifacts.json` の `outline` に記録する（承認済み state.txt の「Artifact への公開は手順の最後に…」というユーザー指示）。

## C1: outline.md の形式

```markdown
---
client: <依頼元企業名>
trigger: <相談のきっかけ>
cost_requested: true|false
---
# <提案タイトル>

## S<n> [<role>] <結論を言い切る見出し文>
<本文: 「- 」で始まる 1〜3 行 | Markdown の表 1 つ | 「挿絵: <描く内容>」1 行 と任意で「- 」1〜3 行>
```

`role` は `cover`, `understanding`, `hypothesis`, `approach`, `why_us`, `process`, `questions_next`, `cost` のいずれか。`cover` から `questions_next` までの七役はこの順で一回以上現れる。同じ役割は連続してよい。`cost` は費用を求められた場合だけ、`process` と `questions_next` の間に置く。スライドに載る文字列は見出し文と本文だけ。

`industry-notes.md` の見出しと四つの節は [`references/industry-research.md`](references/industry-research.md) の C2 形式に従う。

## 修正モード

修正モードの入力は C0 の `request.md`、`industry-notes.md`、`outline.md` と、`target: outline` の C5 JSON である。C5 の各 finding を `id`, `rule`, `slide`, `category`, `message` から特定し、依頼原文と確認済み情報に照らして修正する。

- 既存の依頼内容と確認済み情報で直せる指摘は `outline.md` を直す。業界の事実を訂正・補足した場合は、対応する出典を確認して `industry-notes.md` も直す。
- 不明点を確認質問へ移すだけで直せる場合は、C1 の `questions_next` を更新する。
- 提供内容・約束・費用を増やさないと直せない場合、またはユーザーにしか出せない事実が要る場合は、その指摘と必要な質問を C0 の `questions.md` に書いて止まる（F1、F9、F10、承認済み state.txt の「提供内容・約束・費用を増やさないと直せない指摘や、ユーザーにしか出せない事実が要る指摘は questions.md に書いて止まる」という指示）。費用負担やユーザーが否定した条件を推測で決めない。

質問が残っている間は、修正済みとしてレビューへ戻さない。`questions.md` が空または存在しない場合は質問なし。

## 出典との対応

スキル内の禁止事項と停止条件は、次の観測済みの失敗または承認済み state.txt のユーザー発言に基づく。

| 指示 | 根拠 |
|---|---|
| 入力を整理し直すよう求めず、依頼元企業名と相談のきっかけが欠ける場合だけ尋ねる | state.txt「形式を問わず受け取り整理をユーザーに求めない。依頼元企業名と相談のきっかけが無いときだけ聞く」 |
| 商談内容を前提にしない | state.txt「商談前なので商談内容は使えない」 |
| 確認できない情報を事実として補わず、確認済み事実と不明点を分ける | state.txt 手順 2「確認済み事実と不明点を分ける」 |
| 業界理解メモをスライドに載せない | state.txt 手順 2「社内用『業界理解メモ』に出典付きで残し…スライドには載せない」、F8 |
| works を提案に使うときに開示範囲を守る | state.txt の T1 指示「works を使うときは works/README.md の開示ルールと overview.md の external_label に従う」 |
| 業績など無関係な企業情報を提案根拠にせず、依頼外へ提案しない | state.txt 手順 4、F13 |
| 課題仮説を断定しない | state.txt 手順 4「仮説は断定せず確かめたいことにする」 |
| スライド見出しを結論文にし、七つの基本役割を指定順に並べる | state.txt 手順 5、C1、F6 |
| 費用スライドは費用を求められたときだけ置く | state.txt 手順 5「費用は依頼で求められた場合のみ」、C1 |
| 新しい提供内容・約束・費用や、ユーザーしか出せない事実が修正に必要なら質問して止まる | state.txt の修正モード、F1、F9、F10 |
| Artifact 公開と URL の記録は作業の最後に行う | state.txt の T1 指示「主スレッドで outline.md を Artifact として公開し、URL を artifacts.json に記録する」 |
