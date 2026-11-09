---
name: dispatch
description: 会話の中でユーザーの依頼が「作業として渡せそうだ」と感じたときに、渡す前に必ず使う。会話をユーザー発言の引用と事実だけの State に固定し、Jev で成果物の種類（実装 / 調査 / 文書）と、聞き漏らしている項目・確定事項との矛盾を判定して、足りない項目だけを聞き、揃ったら作業スキルへ State を渡す。「実装して」「調べて」「書いて」と直接言われていなくても、要件・対象・完了条件が会話に出そろってきた、ユーザーが「じゃあそれで」「進めて」と合意した、調査結果を受けて次に進もうとしている、といった場面で使う。使わないのは、ユーザーが /dev-workflow のようにスキル名で作業を明示したとき（そのまま呼ぶ）、感想・質問・壁打ちだけで作業の話になっていないとき
allowed-tools: Bash, Read, Write, Agent, AskUserQuestion
user-invocable: false
---

会話で固まりつつある依頼を、作業スキルへ渡せる形にする。何を聞くかを自分で考えず、Jev の判定に従う。

## なぜ自分で判断しないか

会話を見ている LLM は、依頼が固まったかどうかを自分の解釈で決めてしまう。迷っていても断定の文章が出るし、一度「実装だ」と言った後はその方向に寄る。その解釈が依頼文に混ざると、作業係は誤った前提のまま最後まで走る。

このスキルは、判断の入力を「ユーザーが実際に言ったこと」と「機械で集めた事実」だけに限り、判定を Jev（固定の問いに確率で答える分類器）に出し、閾値で「聞く / 渡す」を決める。自分の役割は、引用を書き写すことと、判定結果の指示どおりに聞くか渡すかすることだけである。

## 手順

スクリプトは `scripts/` にある（`SKILL_DIR` はこのスキルのディレクトリ）。作業ファイルは対象リポジトリ直下の `.claude/dispatch/` に置く。対象リポジトリが無ければ `mktemp -d -t dispatch` を使う。

### 1. ユーザー発言を引用で書き出す

`quotes.txt` に、この会話でユーザーが述べたことを**原文のまま**並べる。要約しない、言い換えない、自分の発言を入れない。長い会話なら、ユーザーが肯定した確定事項と直近の発言を残し、何を落としたかを機械的に決める（「直近 N ターン」のように）。選び方に自分の判断を入れない。

作業係（サブエージェント）の報告が会話にあれば、`worker-report.txt` に別で書く。報告の中の提案や前提は確定事項ではないので、ユーザー発言と混ぜない。

依頼の原文（issue 本文、貼られた仕様、依頼文）があれば `request.txt` に原文のまま書く。

### 2. State を組み立てる

```bash
python3 "$SKILL_DIR/scripts/build_state.py" --user-quotes quotes.txt [--request request.txt] [--worker-report worker-report.txt] [--cwd <対象リポジトリ>] [--ref <owner/repo#番号>] [--plan <計画書のパス>] --out state.txt
```

`.git` の有無、マニフェスト、既存テスト、issue / PR の種別はスクリプトが集める。自分で書き足さない。

### 3. Jev で判定する

```bash
python3 "$SKILL_DIR/scripts/judge_state.py" --state-file state.txt --catalog "$SKILL_DIR/scripts/catalog.json" --thresholds "$SKILL_DIR/scripts/thresholds.json" --out verdict.json --log judge-log.jsonl
```

ユーザーが種類を明示している（「実装して」「調べるだけでいい」など）なら `--kind implement|know|write` を付けて 1 層目を飛ばす。

Jev API キーはキーチェーン `typesafe-api-key`。スクリプトが失敗したら自分で判定せず、失敗した事実をユーザーに伝えて止まる。

### 4. verdict.json の指示どおりに動く

確率は読まない。`verdict` と `ask` だけに従う。

| 出力 | すること |
|---|---|
| `kind` が null | 「何を受け取りたいか」を聞く。選択肢（実装 / 調査結果 / 文書）を示してよい |
| `items` に `no` か `ask` の項目がある | それぞれに添えられた `ask` の文を、まとめて 1 回で聞く。`AskUserQuestion` が合う形なら使う |
| `contradiction` が `yes` か `ask` | 「前に○○と言われたが、変えるか」を聞く。○○は quotes.txt の該当発言を引用する |
| `ready` が true | 下記「渡す」へ |

聞いた答えは `quotes.txt` に原文のまま追記し、手順 2 からやり直す。`ready` になるまで繰り返す。1 回に聞く項目をまとめるのは、往復の回数を減らすためである。

### 5. 渡す

`kind` に対応するスキルを読ませる Agent を起動する。依頼文には `state.txt` の絶対パスを書き、**依頼の内容は State から読ませる**。自分で要約を書かない（要約に解釈が混ざるのを避けるため、ここまで State を作ってきた）。

| kind | 読ませるスキル | subagent_type / model |
|---|---|---|
| implement | `/Users/cancer/.claude/skills/plan/SKILL.md`。dev-workflow へは直接渡さない。計画の承認、PoC での差し戻し、承認後に `dev-workflow --effort low|mid|high` へ渡すまでの流れは `references/implement-loop.md` に従う | Plan / opus |
| know | `/Users/cancer/.claude/skills/research/skill.md`。コードベース内の把握なら Explore（スキル不要） | tech-researcher / haiku、Explore / sonnet |
| write | `/Users/cancer/.claude/skills/article-writer/SKILL.md` | general-purpose / opus |

依頼文の例:

```
以下のスキルを読み、その手順に従って作業してください。
- /Users/cancer/.claude/skills/dev-workflow/SKILL.md

依頼の内容は次のファイルにあります。ユーザーの発言は引用で、事実はスクリプトが集めたものです。これを依頼として読んでください。
- /path/to/.claude/dispatch/state.txt

ユーザーに確認が必要な判断が出たら、推測で進めず、その時点までの状況と質問を報告して終了してください。
```

起動したらユーザーに「○○を△△に出した」と 1 行で伝える。作業係から報告が返ったら、要約して伝え、報告を `worker-report.txt` に積む。次にユーザーが作業の話を続けたら、このスキルを最初からやり直す（State には前回の報告が入っている）。

## やらないこと

- 依頼文を自分で要約して書く。State を渡す
- `verdict.json` の確率を見て、閾値をまたいで自分で決める
- 聞くべき項目を自分で考える。`ask` に無い項目は聞かない（聞きたくなったら、それはカタログに足すべき項目で、このスキルの実行中に足すものではない）
- 判定が `ready` でないのに渡す。ユーザーが「このまま進めて」と言ったときだけ、その発言を quotes.txt に追記したうえで渡してよい

## 参照

- 設計: `references/companion-design.md`（implement の流れは `references/implement-loop.md`、検討経緯は `references/gate-catalog.md`）
- 問いのカタログ: `scripts/catalog.json`（1 層目 `kind`、2 層目 `implement.* / know.* / write.*`、共通 `common.contradiction`）。問いを足す・直すのはここ
- 閾値: `scripts/thresholds.json`（`yes` 0.7 / `no` 0.3）
- 判定の記録: `judge-log.jsonl`（閾値を調整するときの材料）
