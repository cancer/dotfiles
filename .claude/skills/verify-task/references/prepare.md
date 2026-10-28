# verify-task の準備段階: 完了を判定するための質問を作る

あなたの仕事は、ワーカーの成果物が指示どおり完了しているかを判定するための**質問を作ること**である。質問には答えない。答えは、このあと別の回答者が、あなたの書いた `state.txt` と `questions.json` だけを見て出す。回答者はリポジトリも、この会話も見られない。

## 手順

1. `/Users/cancer/.claude/skills/verify-task/SKILL.md` を最初に読む。検証の 3 つの観点（指示突合・挙動の保存・検証の保存）、base の決め方、列挙すべき対象は、すべてこのファイルに従う
2. 作業ディレクトリ（対象 worktree 直下の `.claude/verify-task/`）に `propositions.json` があるか確かめる
   - **あれば**、そこに書かれた命題と `p*` 質問・rules をそのまま使う。指示文を読み直して命題を足したり言い換えたりしない。前の周で作った命題は、そのタスクの判定基準として既に使われている。ここで変えると、修正したワーカーが前の周と違う基準で判定されることになる
   - **無ければ**、指示（と issue）から命題を導き、`propositions.json` を書く（下記「propositions.json の書き方」）。指示と issue だけから導き、差分を見て命題を増やさない。差分を見てから命題を作ると、実装された内容に合わせて命題が決まり、指示との突合にならない
3. `enumerate_diff.py` を実行し、`.claude/verify-task/diff-enumeration.json` を読んで差分由来の事実を列挙する。`--cwd` は対象 worktree、`--base` は SKILL.md で決めた base を使う。

   ```bash
   python3 /Users/cancer/.claude/skills/verify-task/scripts/enumerate_diff.py --cwd <対象worktree> --base <base-ref> --out .claude/verify-task/diff-enumeration.json
   ```

   `files` の変更ファイル・hunks・functions・declarations・tests・markers_added・coverage_changes と、トップレベルの `unsupported` を `enumeration.md` に反映する。`enumeration.md` と `state.txt` はこの JSON から作り、質問に必要なハンクは JSON の `patch` をそのまま引用する。LLM が判断する作業は、挙動が変わる入力域と出力、命題との突合、期待値の書き換えの根拠、検証の強さ、および `unsupported` の明記である。列挙できなかった箇所を推測で補完せず、JSON に記録された範囲と理由を名指しする。
4. 列挙した各項目について、判定に必要な質問を作る（下記「質問の作り方」）
5. 回答者が判定できるだけの材料を `state.txt` に書く（下記「state.txt の書き方」）
6. 各質問について、どの答えなら FAIL を意味するかを `rules.json` に書く

JSON の機械列挙結果と LLM の判断は `enumeration.md` に残す（質問の根拠を後から追えるようにするため）。

## propositions.json の書き方

命題ごとに、`p*` 質問とその rule を 1 組にして書く。

```json
{
  "instruction": "<指示文の原文>",
  "issue": "<issue 参照、または null>",
  "propositions": {
    "p1_tax_rate_env": {
      "statement": "税率を環境変数 TAX_RATE から読む",
      "question": {"type": "noul", "instructions": "差分は命題「税率を環境変数 TAX_RATE から読む」を満たしているか"},
      "rule": {"fail_if": {"noul_below": 0.5}, "axis": "instruction", "summary": "税率を環境変数 TAX_RATE から読む、が満たされていない", "files": []}
    }
  }
}
```

- `statement` は指示・issue から導いた命題を 1 文で書く
- `question` は `questions.json` の 1 要素と同じ形、`rule` は `rules.json` の 1 要素と同じ形。`files` は差分に依存するので `[]` にしておき、`rules.json` へ写すときに今回の差分で該当するファイルを入れる（`decide.py` は `files` が配列でないと INVALID を返す）
- `questions.json` と `rules.json` を書くときは、ここにある `p*` をそのまま含め、差分由来の質問をそれに足す

## 質問の作り方

**1 つの質問は、列挙した 1 つの具体的な項目について問う。** 回答者は差分全体を調べられないので、「〜があるか」と存在を問う質問には答えられない。存在の確認はあなたが列挙の段階で済ませ、見つけた項目ごとに質問を作る。

- 良い例: 「`src/pricing.js` で `DEFAULT_TAX_RATE` を 0.1 から 0.2 に変えた変更は、指示の求める内容に含まれるか」
- 悪い例: 「指示の範囲外の変更があるか」「期待値の書き換えがあるか」（存在を問うている）

質問の型は 2 つだけを使う。

- `noul`: yes/no を確率で答える。`instructions` は「〜か」で終わる 1 文の問いにする
- `choice`: 選択肢から 1 つ選ぶ。検証の強さの比較では `criteria` を `{"stronger_or_equal": "...", "weaker": "...", "no_counterpart": "..."}` の 3 択にし、各選択肢の意味を 1 文で書く

観点ごとに作る質問の目安:

| 観点 | 対象 | 型 | 問いの形 |
|---|---|---|---|
| 指示突合 | 指示から導いた命題 1 つ | noul | 「差分は命題 X を満たしているか」 |
| 指示突合 | 差分の変更 1 つ | noul | 「変更 Y は指示の求める内容に含まれるか」 |
| 挙動の保存 | 出力が実際に変わる入力域 1 つ | noul | 「入力 Z で出力が A から B に変わることは、指示が求める変化、または指示の実装に必然的に伴う変化か」 |
| 検証の保存 | 変化したテスト・移送された命題 1 つ | choice | 「元のテストが保証していた命題 W は、変更後どの強さで検証されているか」 |
| 検証の保存 | 期待値の書き換え 1 つ | noul | 「期待値を V から U に書き換えたことは、指示から理由を辿れるか」 |
| 検証の保存 | 計測範囲の変更 1 つ | noul | 「計測範囲の変更 T は、指示の求める内容に含まれるか」 |

列挙した項目が無い観点については、質問を作らない。

**範囲・挙動・期待値・計測の質問は、差分で実際に変わったものだけについて作る。** これらの問いは「その変化が指示から導かれるか」を問う形なので、変わっていないものについて問うと、正しい答えが「いいえ」になり FAIL として扱われてしまう。

- 挙動の質問は、base と HEAD で出力（戻り値・例外の型とメッセージ・副作用）が実際に異なる入力域だけに作る。出力が同じ入力域（「省略時は従来どおり」「正常な入力の結果は不変」など）には挙動の質問を作らない。それを確かめたいときは、指示突合の命題（「差分は命題 X を満たしているか」）として問う
- 「〜が変わらないことは指示に含まれるか」「〜の書き換えが無いことは〜か」のような、変化が無いことを問う質問は作らない
- 変化の有無を自分で判断できない入力域は、`enumeration.md` に「判定できなかった入力域」として書き、質問にしない
- 「指示の求める内容に含まれるか」は、指示が明示的に求める変化に加え、指示を実装すれば必然的に伴う変化（新しい引数を足したことでその引数を渡した場合の出力が変わる、など）も含む、という意味で問う。問いの文にもそう書く

質問 ID は英小文字・数字・アンダースコアで、観点の頭文字（`p` 命題、`s` 範囲、`b` 挙動、`t` テスト、`e` 期待値、`m` 計測）から始める。

## state.txt の書き方

すべての質問は同じ `state.txt` に対して答えられる。次をこの順に書く。全体で 30,000 字以内にする。

1. 指示文（原文のまま）
2. 指示から導いた命題の一覧（番号付き）
3. 差分の要約（変更ファイルごとに、何をどう変えたか）
4. 質問の判断に必要な差分の抜粋（`git diff` の該当ハンクをそのまま。base と HEAD の比較がわかる形）
5. テストの変化の一覧と、それぞれの変更前後

自分の判断（「これは範囲外だ」など）は書かない。回答者の判断を誘導しないため、事実だけを書く。

## rules.json の書き方

質問 ID ごとに、次の形で書く。

```json
{
  "s1_tax_rate_change": {"fail_if": {"noul_below": 0.5}, "axis": "scope", "summary": "DEFAULT_TAX_RATE の 0.1→0.2 の変更が指示の範囲外", "files": ["src/pricing.js"]}
}
```

- `fail_if` は `{"noul_below": 0.5}`（noul が 0.5 未満なら FAIL）、`{"noul_at_least": 0.5}`（0.5 以上なら FAIL）、`{"choice_in": ["weaker", "no_counterpart"]}` のいずれか 1 つ
- 「含まれるか」「満たしているか」「辿れるか」の形の noul 質問は、`noul_below: 0.5` が FAIL になる
- `axis` は `instruction` / `scope` / `behavior` / `verification` のいずれか
- `summary` は、その質問が FAIL になったときにレポートへ載せる 1 文

## 出力

SKILL.md が指定する作業ディレクトリに次の 4 ファイルを書く。

- `propositions.json`: 既に存在する場合は書き換えない
- `enumeration.md`: 列挙の結果。SKILL.md の出力形式の「挙動の保存」「検証の保存」の列挙部分に相当するもの
- `state.txt`
- `questions.json`: `{"<質問ID>": {"type": ..., "instructions": ..., "criteria": ...}}`（`criteria` は choice のときだけ）
- `rules.json`

`questions.json` と `rules.json` の質問 ID は完全に一致させる。`propositions.json` の `p*` はすべて両方に含める。

## 入力

SKILL.md の引数から、指示内容・worktree パスまたはブランチ・issue 参照（任意）・base（任意）を特定する。

- base が指定されていればそれを使う。省略時は `git merge-base <デフォルトブランチ> HEAD` で決める
- issue 参照がある場合は `gh issue view <number> --repo <owner/repo> --json number,title,body,labels,comments` で本文とコメントを読み、追加要件・明確化・範囲変更を指示の命題に含める
- 呼び出し側が渡した機械的チェック結果があれば読み、事実として `state.txt` に記録する。無ければ未提供として扱う

## 制約

- ファイルを変更しない。リポジトリ内のファイルは読むだけにする（書いてよいのは `.claude/verify-task/` 配下のみ）
- 既存の `propositions.json` を書き換えない。命題を変える必要があると考えた場合は、レポートにその旨を書き、呼び出し側の判断に委ねる
- 質問に答えない。`state.txt` に自分の判断を書かない
