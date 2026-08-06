---
name: create-pr
description: PR作成の共通フロー。対象ブランチにコミット・push してPRを作成する。PRを作成するすべての場面で使用する
argument-hint: "[--branch <name>] [--title <title>] [--base <branch>]"
model: sonnet
allowed-tools: Bash, Skill, Read, Glob, Grep
user-invocable: true
---

GitHub PRを作成する。対象ブランチへのコミット・push・PR作成を一貫して行う。

**このスキルはブランチ名を考案しない。** 対象ブランチ名の出所は「引数で明示された名前」「現在のブランチ」「`create-branch` が決定した名前」の3つだけであり、それ以外の出所から名前を作ることを禁止する。プロジェクトのブランチ命名規則の解釈は `create-branch` の責務である。

## 引数
$ARGUMENTS

## 引数の形式

- `--branch <name>` (任意): PRを作る対象ブランチ名。省略時はステップ1で決定する
- `--title <title>` (任意): PRのタイトル。省略時はコミットメッセージから推測
- `--base <branch>` (任意): マージ先のブランチ。省略時はリポジトリのデフォルトブランチ

以降、対象ブランチを `TARGET`、マージ先を `BASE`、実行開始時のブランチを `CURRENT` と表記する。

## 確認を取る条件（危険条件）

ユーザーへの確認は次に該当するときだけ取る。該当しなければ確認せずに実行し、実行内容は最後の報告に含める。

| ID | 条件 | 確認内容 |
|---|---|---|
| D1 | `TARGET` に**他者が作成した**オープンPRがある | その変更をそのPRに追加してよいか |
| D2 | `CURRENT` ≠ `TARGET` で、未コミット変更を `TARGET` へ持ち込む | その変更を `TARGET` で commit する意図か |
| D3 | `TARGET` が存在せず作成が必要で、`CURRENT` ≠ `BASE`（他の作業ブランチの上に積む） | `CURRENT` を base にしてよいか |
| D4 | `--branch` 省略で `TARGET` を現在のブランチから推論し、その `TARGET` にオープンPRがある | 既存PRに追記するのか、新しいブランチを切って別PRにするのか |

D1 は過去の事故（他人の作業中PRのブランチへ無関係なコミットを混入させて push した）への対策であり、`TARGET` の決定経路にかかわらず必ず判定する。

D4 は、1つの作業ディレクトリから複数のPRを順に出す場面で、2本目以降が1本目のPRへ相乗りするのを防ぐ。`--branch` を明示指定した場合はユーザーが対象を表明しているため、自分のオープンPRへの追加では確認を取らない（提示のみ）。

## 現在のブランチを再利用してよい条件

「現在のブランチである」ことは、そのブランチでPRを作ってよい根拠にならない。worktree は1つのブランチに固定されたまま長く使われるため、PRを出し終えたブランチが現在のブランチとして残り続ける。`CURRENT` ≠ `BASE` はこの「用済みのブランチ」を除外できない。

したがって `--branch` 省略時は、`TARGET` を確定する前に**再利用してよい根拠を確認する**。根拠はブランチに紐づくPR履歴で判定する（ステップ3）。

| PR履歴（`gh pr list --head <TARGET> --state all`） | 判定 |
|---|---|
| PRが1つもない | 作業中または未使用のブランチ。再利用してよい |
| オープンPRがある | 継続作業か新規PRかをユーザーに確認する（D1 / D4） |
| merged / closed のPRだけがある | 用済みのブランチ。**再利用しない**。`create-branch` で新しいブランチを作る |

---

# ステップ1: BASE と TARGET の決定

## 1.1 BASE

`--base` があればその値。なければ `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name` で取得する。

## 1.2 TARGET

`CURRENT=$(git branch --show-current)` を取得する。空文字（detached HEAD）なら**即座にエラー終了**する。

```
ERROR: detached HEAD です。ブランチ上で実行してください。
```

### ケースA: `--branch` が指定されている

`TARGET` = その値。ローカル・リモートの存在を確認する。

```bash
LOCAL_EXISTS=$(git branch --list "$TARGET" | wc -l)
REMOTE_EXISTS=$(git ls-remote --heads origin "$TARGET" | wc -l)
```

- 存在する → 1.3 へ
- 存在しない → 名前はユーザー由来なので `CURRENT` から作成する。D3 に該当する場合のみ確認を取り、そのうえで `git checkout -b "$TARGET"` する（未コミット変更はそのまま新ブランチへ移る）

### ケースB: `--branch` が省略されている

- `CURRENT` ≠ `BASE` → `TARGET` = `CURRENT` を**暫定候補**とする。確定するのはステップ3でPR履歴による再利用根拠を確認した後である
- `CURRENT` = `BASE` → 作業ブランチが必要。`create-branch` スキルを呼んでブランチを決定・作成させ、その結果のブランチ名を `TARGET` にする
  - ブランチ名を自分で考案してはならない
  - `create-branch` がブランチを作成できなかった場合は、PR作成を中止して理由を報告する

## 1.3 他の worktree との衝突確認

`TARGET` が既に存在し、かつ `CURRENT` ≠ `TARGET` の場合だけ実行する。`git branch --list` はリポジトリ全体のブランチを返すため、存在しても**別の worktree がチェックアウト中**であることがある。その状態で `git checkout` すると `fatal: '<TARGET>' is already used by worktree at '<path>'` で失敗する。

```bash
git worktree list --porcelain
```

出力に `branch refs/heads/<TARGET>` を持つ worktree があり、それが現在の作業ディレクトリでない場合、**即座にエラー終了**する。

```
ERROR: <TARGET> は別の worktree (<path>) がチェックアウト中です。
その worktree で /create-pr を実行してください。
```

worktree の移動・削除・強制チェックアウトは行わない。

### やってはいけないこと

- `BASE`（デフォルトブランチ）を `TARGET` にすること
- `create-branch` を経由せずに、命名規則を自分で推測してブランチ名を作ること
- 以前のセッションのブランチ名を記憶から拾って `TARGET` にすること

# ステップ2: TARGET ブランチへの切り替え

`CURRENT` = `TARGET` なら何もしない（ステップ1でブランチを作成した直後もこれに該当する）。

`CURRENT` ≠ `TARGET` の場合:

1. `git status --porcelain` で未コミット変更（追跡外含む）を確認
2. 変更があれば D2 に該当する。`git status` / `git diff` の内容を提示し、「これらの変更を `TARGET` に持ち込んで commit する意図か」を確認する
   - 判断ポイントは「`CURRENT` に置いておくべき変更ではないか」
   - 明示的な許可がない限り続行しない
3. 変更を退避: `git stash push --include-untracked -m "create-pr:switch-to-<TARGET>"`
4. `git checkout "$TARGET"`
5. リモートにブランチが存在すれば同期: `git pull --ff-only origin "$TARGET"`
6. 手順3で stash した場合は `git stash pop`。コンフリクトしたら中断してユーザーに報告
7. `git branch --show-current` で `TARGET` に切り替わったことを確認

# ステップ3: PR履歴の確認と TARGET の確定（絶対実行）

**このステップを実行せずに次へ進むことは絶対に禁止する。** ここで D1 / D4 を判定し、`TARGET` を確定する。

```bash
gh pr list --head "$TARGET" --state all --json number,title,author,url,state
```

`--state open` ではなく `--state all` を使う。merged / closed のPRを持つブランチは用済みであり、その事実はオープンPRだけを見ても分からない。

PR履歴が空ならステップ4へ。ある場合は次で分岐する。

| 状況 | 処理 |
|---|---|
| オープンPRを他者が作成している（D1） | 確認を取る（下記） |
| オープンPRが自分のもので、`TARGET` は `--branch` 省略で推論した（D4） | 確認を取る（下記） |
| オープンPRが自分のもので、`TARGET` は `--branch` で明示指定された | 番号・タイトル・URL を報告に含めてステップ4へ（確認しない） |
| オープンPRはなく merged / closed のPRだけがあり、`TARGET` は `--branch` 省略で推論した | 用済みのブランチなので**再利用しない**。`create-branch` でブランチを作成し、それを `TARGET` にしてこのステップを最初からやり直す（確認は取らない。該当PRの番号と新しいブランチ名を報告する） |
| オープンPRはなく merged / closed のPRだけがあり、`TARGET` は `--branch` で明示指定された | ユーザーが対象を表明しているので続行する。該当PRの番号を報告に含めてステップ4へ |

## 確認の手順（D1 / D4）

以下をすべて実行する。**省略可能なものは1つもない**。

1. PRの番号・タイトル・作者・URL を提示する
2. これから含めようとしている変更（`git status` / `git diff` / `git diff --cached`）を提示する
3. **明示的に質問する**
   - D1: 「これらの変更を既存PR #N に追加してよいか」
   - D4: 「これらの変更を既存PR #N に追加するか、新しいブランチを切って別PRにするか」
4. 回答に応じて分岐する
   - 既存PRに追加してよい → ステップ4へ
   - 新しいブランチで別PRにする → `create-branch` スキルを呼んでブランチを作成し、それを `TARGET` にしてステップ3を最初からやり直す
   - 回答がない → 待機し、続行しない

## やってはいけないこと

- ステップ2でユーザーが確認したことを理由に、このステップをスキップすること
- 「`--branch` で既存ブランチを明示指定したから相乗りでよいはず」と解釈すること（明示指定でも、未コミット変更がPRのスコープに合っているかは別問題）
- 「ついでだから」「同じセッションで作った変更だから」を理由に相乗りを正当化すること

# ステップ4: コミット

1. `git status` で未コミットの変更（staged/unstaged両方）を確認する
2. 変更がある場合:
   - `git diff` と `git diff --cached` で内容を把握する
   - 関連ファイルを `git add` でステージング（`git add -A` は機密ファイル混入リスクがあるため、内容を確認した上で使用）
   - 変更内容を表す commit message で `git commit -m "<message>"` する
3. 変更がなければスキップ

# ステップ5: 検証

`TARGET` ブランチで以下を実行し、失敗したら PR 作成を中止して結果を報告する。

1. プロジェクトの check/lint/typecheck コマンドを特定する
   - `package.json` の `scripts`、`CLAUDE.md` / `README.md` の記述を確認
2. 特定できたコマンドを実行する
3. いずれかが失敗した場合、PR 作成はせず失敗内容をユーザーに報告して終了する

検証コマンドが特定できなかった場合は、その旨を報告しつつ次に進む。

# ステップ6: push

1. `git remote -v` でリモートを確認する
2. `git push -u origin "$TARGET"` で push する（既にリモート追跡済みなら通常の push でよい）

# ステップ7: PR作成

1. `git log --oneline "$BASE"..HEAD` と `git diff "$BASE"...HEAD` で PR に含まれる変更を把握する
2. **コミット数チェック**: `COMMIT_COUNT=$(git rev-list --count "$BASE"..HEAD)` でコミット数を数える。**20以上（`>= 20`）の場合**、PR作成を中止し、PRを分割するよう指示して終了する:
   - 理由: Cloudflare Workers CI は push に 20+ commits（または 3000+ file changes）が含まれると [build watch paths](https://developers.cloudflare.com/workers/ci-cd/builds/build-watch-paths/) のパスマッチングをバイパスし、常にプロジェクト全体をビルドする。watch-paths による monorepo ビルド最適化を効かせるには、1つのPR（push）を 19 コミット以下に収める必要がある
   - **確認は取らない**。分割が必要である旨とコミット数 N を報告して終了する
   - **例外**: ユーザーが事前に「コミット数が20以上でもよい」と明示している場合に限り、このチェックを無視してそのまま続行してよい
3. PR本文を一時ファイルに書き出す
   - **必ず** `BODY_FILE=$(mktemp /tmp/pr_body.XXXXXX)` で一意な一時ファイルを作る（固定パス禁止）
   - 書き出し後、ファイルが存在し空でないことを確認する。空または存在しない場合は PR 作成を中止して報告する
4. `gh pr create --title "<title>" --base "$BASE" --head "$TARGET" --body-file "$BODY_FILE"` で PR を作成する
5. 成否にかかわらず一時ファイルを削除する

## PR本文のテンプレート

```markdown
## Summary
<1〜3行で変更内容をまとめる>

## Changes
<主な変更点を箇条書き>

---
🤖 *This PR was created via [Claude Code](https://claude.ai/claude-code)*
```

# ステップ8: 結果報告

成功時の報告：
- PR URL
- PR title
- target branch と、その決定経路（`--branch` 指定 / 現在のブランチを再利用 / `create-branch` による作成）
- 現在のブランチを再利用しなかった場合は、その根拠（用済みと判定したPR番号）
- base branch
- 実行した検証コマンドと結果
- ブランチの作成・切り替えを行った場合はその内容
- 既存オープンPRを検出した場合はその内容と処理

失敗時の報告：
- PR作成を中止した理由
- 具体的なエラー内容
- 途中までPRが作られていた場合はそのURL

# 注意事項

- ブランチ名の出所は「引数」「現在のブランチ」「`create-branch` の決定」の3つだけ。命名規則を推測して名前を作ることは禁止
- 「現在のブランチである」ことを再利用の根拠にしない。`--branch` 省略時はPR履歴で再利用の可否を判定する（ステップ3）
- `BASE`（デフォルトブランチ）を `TARGET` にしない
- 確認は危険条件 D1〜D4 に限る。該当しない操作は確認せず実行し、報告に含める
- ステップ3 は他のチェックと独立した安全ネット。`TARGET` の決定経路にかかわらず常に実行する
- worktree 内での実行を前提に含める。他の worktree がチェックアウト中のブランチへは checkout せず、エラー終了する（ステップ1.3）
- ブランチの切り替えでは未コミット変更を失わない（stash → checkout → pop）
- 現在の作業ディレクトリが対象リポジトリであることを前提とする
- 検証（lint/typecheck等）が失敗した状態でPRを作らない
- 一時ファイルは必ず `mktemp` で一意に作る。固定パスは禁止
- `git push --force` 等の破壊的操作はユーザーの明示的な許可がない限り行わない
- コミット数が 20 以上のPRは build watch paths がバイパスされるため、分割をユーザーに促す（ステップ7-2）
