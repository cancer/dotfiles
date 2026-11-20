---
name: dispatch
description: 会話の中でユーザーの依頼が「作業として渡せそうだ」と感じたときに、渡す前に必ず使う。会話から依頼を項目ごとに解釈して State に固定し（根拠としてユーザー発言・承認された提案・既定値を添える）、Jev が固定の問いで抜けと矛盾を判定し、既定値でも埋まらない項目だけを聞き、判定が通ったら作業スキルへ State を渡す。「実装して」「調べて」「書いて」と直接言われていなくても、要件・対象・完了条件が会話に出そろってきた、ユーザーが「じゃあそれで」「進めて」と合意した、調査結果を受けて次に進もうとしている、といった場面で使う。使わないのは、ユーザーが /dev-workflow のようにスキル名で作業を明示したとき（そのまま呼ぶ）、感想・質問・壁打ちだけで作業の話になっていないとき
allowed-tools: Bash, Read, Write, Agent, AskUserQuestion, Skill
user-invocable: false
---

会話で固まった依頼を State に固定して、作業スキルへ渡す。聞くのは、渡すために足りないものを埋める手段であって目的ではない。

## 解釈を書き、Jev に確かめさせる

State の中心は、ユーザー発言から companion（自分）が解釈した項目別の内容である。原本の引用だけでは「それを採用しよう」「全部」のような一括承認の中身が State に入らず、作業係が原本を自分で解釈することになる。解釈は消せないので、State に書き出して Jev に確かめさせる。Jev は固定の問い（`scripts/catalog.json`）で、解釈に抜けがないか・引用と矛盾しないか・裏付けのない内容が混ざっていないかを判定する。

ユーザーへ解釈を復唱して承認を取ることはしない。裏付けのない内容は Jev が止めるので、復唱は同じ確認の繰り返しになり、長い復唱はユーザーに読まれない。

既定値がある項目はユーザーに聞かない。聞くのは、ユーザー発言にも承認された提案にも既定値にも無いものだけである。

## 手順

スクリプトは `scripts/` にある（`SKILL_DIR` はこのスキルのディレクトリ）。作業ファイルは対象リポジトリ直下の `.claude/dispatch/` に置く。対象リポジトリが無ければ `mktemp -d -t dispatch` を使う。

### 1. 根拠を書き出す

- `quotes.txt`: この会話でのユーザー発言を**原文のまま**並べる。長い会話なら、確定事項と直近の発言を残す
- `approved.txt`: ユーザーが提案をまとめて承認した場合（「じゃあそれで」「B 案で」「全部」）、承認された提案（自分または作業係の発言）を原文のまま書き写し、承認した発言の引用と組にする。書き写すのは承認の発言が指している提案だけで、範囲を広げない
- `worker-report.txt`: 作業係の報告。承認されていない提案は確定事項ではないので、ここに留める
- `request.txt`: 依頼の原文（issue 本文、貼られた仕様）があれば原文のまま

### 2. 種類を判定する

```bash
python3 "$SKILL_DIR/scripts/build_state.py" --user-quotes quotes.txt [--approved approved.txt] [--request request.txt] [--worker-report worker-report.txt] [--cwd <対象リポジトリ>] [--ref <owner/repo#番号>] [--plan <計画書のパス>] --out state.txt
python3 "$SKILL_DIR/scripts/judge_state.py" --state-file state.txt --catalog "$SKILL_DIR/scripts/catalog.json" --thresholds "$SKILL_DIR/scripts/thresholds.json" --out verdict.json --log judge-log.jsonl
```

ユーザーが種類を明示している（「実装して」「調べるだけでいい」「新しく立ち上げて」など）なら、ここは飛ばして手順 3 で `--kind implement|know|write|init` を付ける。`kind` が null なら、`message` をそのまま示して聞き、答えを quotes.txt に追記してやり直す。

Jev API キーはキーチェーン `typesafe-api-key`。スクリプトが失敗したら自分で判定せず、失敗した事実をユーザーに伝えて止まる。

### 3. 解釈を書いて判定する

`catalog.json` の `items` のうち、その種類の項目について `interpretation.json` を書く。

```json
{"items": {
  "implement.completion": {"value": "python3 src/counter.py --help に --verbose の説明行が出て、既存テスト 3 件と追加 1 件が通る", "source": "発言「…」"},
  "implement.deliverable": {"value": "PR", "source": "既定値"}
}}
```

- `value` はユーザー発言・承認された提案から書く。自分の推測を足さない（足すと、その項目の `supported` の問いで止まる）
- どちらにも無い項目は、カタログの `default` があればその値を書き、`source` を「既定値」にする。`default` が null なら `value` を空にする
- `source` には根拠の引用、「承認された提案」、「既定値」のどれかを書く

```bash
python3 "$SKILL_DIR/scripts/build_state.py" ... --interpretation interpretation.json --out state.txt
python3 "$SKILL_DIR/scripts/judge_state.py" ... --kind <種類> --interpretation interpretation.json [--answered-file answered.txt] --out verdict.json --log judge-log.jsonl
```

### 4. verdict.json に従う

`ready` と `message` だけを見る。確率を読んで自分で判断を変えない。

- `ready` が false: `message` を**そのまま**ユーザーに示して聞く。`message` には、止まった項目、解釈の値、満たしていない問いの文、既定値、聞く文が入っている。言い換えたり、スコアだけを示したりしない。複数あれば 1 回でまとめて聞く。答えは quotes.txt に追記し、聞いた項目 ID を `answered.txt` に 1 行ずつ追記し、手順 3 からやり直す。一度聞いて答えを得た項目は、再判定で問いが通らなくても止めない（同じことを聞き続けないため）
- `ready` が true: 手順 5 へ

### 5. コンセプトと照合する

kind が `implement` で対象リポジトリ直下に `CONCEPT.md` がある場合、State の解釈を `CONCEPT.md` の全節（「誰に」「何を」「目的」「すること」「しないこと」）と照合する。「誰に」は、CONCEPT.md に書かれた目的・使う場面・前提として持っている知識や環境と State の解釈を照合する。

- 食い違う場合、または判定できない場合は、Skill ツールで `app-concept` を照合モードとして呼び、対象リポジトリ直下の `CONCEPT.md` の絶対パスと State の解釈を変更要求として渡す。決着するまで先へ進まない。要求が修正された場合は、その内容を `quotes.txt` に追記し、解釈を書き直す手順 3 からやり直す
- 対象リポジトリ直下に `CONCEPT.md` が無い場合、または kind が `implement` 以外の場合は、この手順を飛ばす

照合を通ったら、ユーザーに確認せず手順 6 で渡す。

### 6. 渡す

`kind` に対応するスキルを読ませる Agent を起動する。依頼文には `state.txt` の絶対パスを書き、依頼の内容は State から読ませる。State の外で別の要約を書かない（State の解釈と食い違うのを避けるため）。

| kind | 読ませるスキル | subagent_type / model |
|---|---|---|
| implement | `/Users/cancer/.claude/skills/plan/SKILL.md`。dev-workflow へは直接渡さない。PoC での差し戻しを含め、`dev-workflow --effort low|mid|high` へ渡すまでの流れは `references/implement-loop.md` に従う | Plan / opus |
| know | `/Users/cancer/.claude/skills/research/skill.md`。コードベース内の把握なら Explore（スキル不要） | tech-researcher / haiku、Explore / sonnet |
| write | `/Users/cancer/.claude/skills/article-writer/SKILL.md` | general-purpose / opus |
| init | `init-project`。主スレッドで Skill ツールから呼ぶ（引数は作成先パスと、init.purpose の用途を含む依頼文）。用途が書かれていれば init-project は確認せずに進む | 主スレッド |

init の会話で機能の実装まで頼まれていたら、立ち上げが終わってからこのスキルを最初からやり直し、implement として渡す。

依頼文の例:

```
以下のスキルを読み、その手順に従って作業してください。
- /Users/cancer/.claude/skills/plan/SKILL.md

依頼の内容は次のファイルにあります。「解釈」節が Jev の判定を通った依頼で、引用・承認された提案・事実はその根拠です。
- /path/to/.claude/dispatch/state.txt

ユーザーに確認が必要な判断が出たら、推測で進めず、その時点までの状況と質問を報告して終了してください。
```

起動したらユーザーに「○○を△△に出した」と 1 行で伝える。作業係から報告が返ったら、要約して伝え、報告を `worker-report.txt` に積む。次にユーザーが作業の話を続けたら、このスキルを最初からやり直す。

## やらないこと

- 既定値がある項目をユーザーに聞く
- 聞く項目や問いをその場で考える。問いは `catalog.json` に固定されている（足りないと感じたらカタログに足すべき項目で、実行中には足さない）
- `message` を言い換える、スコアだけを示す
- Jev の判定（とコンセプト照合）を通った後で、解釈を復唱して承認を求める

## 参照

- 設計: `references/companion-design.md`（implement の流れは `references/implement-loop.md`、検討経緯は `references/gate-catalog.md`）
- 問いと既定値のカタログ: `scripts/catalog.json`（`kind`、種類ごとの `items`（`ask`・`default`・`questions`）、共通の `common`）
- 閾値: `scripts/thresholds.json`（`yes` 0.7 / `no` 0.3）
- 判定の記録: `judge-log.jsonl`（閾値や問いを調整するときの材料）
