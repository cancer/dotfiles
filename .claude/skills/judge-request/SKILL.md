---
name: judge-request
description: 会話の中でユーザーの依頼が「作業として渡せそう」かを判定し、判定結果を呼び出し側（companion = 主スレッド）に返す。会話をユーザー発言の引用と事実だけの State に固定し、Jev で成果物の種類（実装 / 調査 / 文書）と、聞き漏らしている項目・確定事項との矛盾を判定する。「実装して」「調べて」「書いて」と直接言われていなくても、要件・対象・完了条件が会話に出そろってきた、ユーザーが「じゃあそれで」「進めて」と合意した、調査結果を受けて次に進もうとしている、といった場面で使う。使わないのは、ユーザーが /dev-workflow のようにスキル名で作業を明示したとき（そのスキルをそのまま呼ぶため）、感想・質問・壁打ちだけで作業の話になっていないとき
allowed-tools: Bash, Read, Write, AskUserQuestion
user-invocable: false
---

会話で固まりつつある依頼を、作業へ進められるか判定し、その結果を呼び出し側へ返す。何を聞くかを自分で考えず、Jev の判定に従う。

## なぜ自分で判断しないか

会話を見ている LLM は、依頼が固まったかどうかを自分の解釈で決めてしまう。迷っていても断定の文章が出るし、一度「実装だ」と言った後はその方向に寄る。その解釈が依頼文に混ざると、作業係は誤った前提のまま最後まで走る。

このスキルは、判断の入力を「ユーザーが実際に言ったこと」と「機械で集めた事実」だけに限り、判定を Jev（固定の問いに確率で答える分類器）に出す。自分の役割は引用を書き写し、聞く内容または次に読むスキルを判定結果に沿って呼び出し側へ返すことだけである。

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

Jev API キーはキーチェーン `typesafe-api-key`。スクリプトが失敗したら自分で判定せず、失敗した事実を呼び出し側へ返して止まる。

### 4. verdict.json の指示どおりに動く

確率は読まない。`verdict` と `ask` だけに従う。

| 出力 | すること |
|---|---|
| `kind` が null | `ask` の問い（「何を受け取りたいか」）を返却内容に含める。選択肢（実装 / 調査結果 / 文書）を示してよい |
| `items` に `no` か `ask` の項目がある | 各項目の `ask` をまとめて返却内容に含める |
| `contradiction` が `yes` か `ask` | 矛盾判定の `ask` を返却内容に含める。確認対象の○○は quotes.txt の該当発言を引用する |
| `ready` が true | kind に対応する次のスキルを示し、手順 5 で返す |

ユーザーからの回答を受けて呼び出し側が再判定を依頼した場合は、その回答を `quotes.txt` に原文のまま追記し、手順 2 からやり直す。

### 5. 返す

呼び出し側（companion = 主スレッド）へ、`verdict.json` と `state.txt` の絶対パスを返す。依頼内容を自分の要約で言い換えない。`verdict.json` の `ready` に応じて、次の情報を添える。

| 判定 | 返す内容 |
|---|---|
| `ready` が true | `kind` と `ready`、両方のファイルパス、次に読むスキルを返す。implement は `/Users/cancer/.claude/skills/run-implement/SKILL.md`、know は `/Users/cancer/.claude/skills/research/skill.md`（コードベース内の把握なら Explore）、write は `/Users/cancer/.claude/skills/article-writer/SKILL.md` とする |
| `ready` が false | `kind` と `ready`、両方のファイルパスを返す。kind が null なら top-level の `ask`、それ以外は `items.*.ask` と `contradiction.ask` のうち値があるものを返す。聞く内容を足したり、判定を自分で補ったりしない |

返した `ask` に対する回答や作業係の報告を受けた後、ユーザーが作業の話を続けたら、このスキルを最初からやり直す（State には前回の報告を分けて記録する）。

## やらないこと

- 依頼を自分で要約して返す。State のパスと判定結果を返す
- `verdict.json` の確率を見て、閾値をまたいで自分で決める
- 聞くべき項目を自分で考える。`ask` に無い項目は聞かない（聞きたくなったら、それはカタログに足すべき項目で、このスキルの実行中に足すものではない）
- `ready` が false のときに `ask` を省略したり、判定を `ready` に読み替えたりしない

## 参照

- 設計: `/Users/cancer/.claude/skills/run-implement/references/companion-design.md`（implement の流れは `/Users/cancer/.claude/skills/run-implement/references/implement-loop.md`、検討経緯は `/Users/cancer/.claude/skills/run-implement/references/gate-catalog.md`）
- 問いのカタログ: `scripts/catalog.json`（1 層目 `kind`、2 層目 `implement.* / know.* / write.*`、共通 `common.contradiction`）。問いを足す・直すのはここ
- 閾値: `scripts/thresholds.json`（`yes` 0.7 / `no` 0.3）
- 判定の記録: `judge-log.jsonl`（閾値を調整するときの材料）
