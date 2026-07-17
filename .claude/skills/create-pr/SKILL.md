---
name: create-pr
description: PR作成の共通フロー。--branchで指定されたブランチに対してPRを作成する。PRを作成するすべての場面で使用する
argument-hint: "--branch <name> [--title <title>] [--base <branch>]"
model: sonnet
allowed-tools: Bash
user-invocable: true
---

GitHub PRを作成する。`--branch` で指定されたブランチを対象に、コミット・push・PR作成を一貫して行う。
**ブランチの作成はこのスキルの責務外**（`/create-branch` を使う）。指定されたブランチが存在しない場合はエラー終了する。
現在のブランチが指定ブランチと異なる場合は、未コミット変更を安全に保ったうえで指定ブランチに切り替える。

## 引数
$ARGUMENTS

## 引数の形式

- `--branch <name>` (**必須**): PRを作る対象ブランチ名。省略不可。理由は下記参照
- `--title <title>` (任意): PRのタイトル。省略時はコミットメッセージから推測
- `--base <branch>` (任意): マージ先のブランチ。省略時はリポジトリのデフォルトブランチ

### なぜ `--branch` が必須か

過去に「現在のブランチが他者の作業中PRに紐付いていることに気付かず、そこへ無関係な変更コミットを混入させて push する」という事故が発生した。

「現在のブランチ = PR したいブランチ」という暗黙の前提は危険である。`--branch` を必須にすることで、PRを作成する瞬間に **「このPRはどのブランチのものか」をユーザーが明示的に判断する** ことを強制する。これは事故防止の中核であり、デフォルトを設けたり省略を許可してはならない。

呼び出し時に `--branch` が指定されていなければ、即座にエラーで終了する。「現在のブランチを推測で使う」「以前のセッションのブランチを記憶から拾う」などの代替動作は禁止する。

---

# ステップ1: 引数検証

1. `--branch <name>` が指定されているか確認する。**指定されていなければ即座にエラー終了**:
   ```
   ERROR: --branch <name> は必須です。PRを作るブランチ名を明示的に指定してください。
   ```
2. `--base` が指定されていればその値を採用。未指定なら `gh repo view --json defaultBranchRef --jq .defaultBranchRef.name` でデフォルトブランチを取得して使用する

以降、`--branch` 値を `TARGET`、`--base` 値を `BASE` と表記する。

# ステップ2: TARGET ブランチの存在確認

`TARGET` がローカルまたはリモートに存在することを確認する。

```bash
LOCAL_EXISTS=$(git branch --list "$TARGET" | wc -l)
REMOTE_EXISTS=$(git ls-remote --heads origin "$TARGET" | wc -l)
```

両方とも0の場合（ブランチが存在しない）、**即座にエラー終了**:

```
ERROR: 指定ブランチ <TARGET> が存在しません。
PRを作る前にブランチを作成してください:
- /create-branch スキルを使う
- または git checkout -b <TARGET> でブランチを作成
ブランチ作成後に /create-pr --branch <TARGET> を再実行してください。
```

ブランチ作成は `/create-pr` の責務ではない。存在チェックで終わる。

# ステップ3: TARGET ブランチへの切り替え

`CURRENT=$(git branch --show-current)` を取得する。

## ケースA: CURRENT = TARGET（既に対象ブランチ上にいる）

→ ステップ4 へ進む。

## ケースB: CURRENT ≠ TARGET（切り替えが必要）

未コミット変更を保ったまま安全に切り替える。

1. `git status --porcelain` で未コミット変更（追跡外含む）の有無を確認
2. 未コミット変更があれば内容を `git status` / `git diff` でユーザーに提示し、「これらの変更を <TARGET> に持ち込んで commit する意図か」を**必ずユーザーに明示確認する**
   - 「現在のブランチ <CURRENT> に置いておくべき変更ではないか」が判断ポイント
   - ユーザーが明示的に「<TARGET> に持ち込んでよい」と答えた場合のみ続行
3. 未コミット変更を退避: `git stash push --include-untracked -m "create-pr:switch-to-<TARGET>"`
4. `git checkout <TARGET>`
5. ローカル追跡があればリモートと同期: `git pull --ff-only origin <TARGET>`（リモートにブランチが存在する場合のみ）
6. `git stash pop`（ステップ3で stash した場合）。コンフリクトが発生したら中断してユーザーに報告
7. `git branch --show-current` で `<TARGET>` に切り替わったことを確認

→ ステップ4 へ進む。

# ステップ4: 既存PRへの相乗り検出（絶対実行）

**このステップを実行せずに次へ進むことは絶対に禁止する。**

過去に「他人の作業中PRのブランチに、無関係な変更コミットを混入させて push する」という事故が発生している。このステップはその再発防止のために存在する。

## 4.1 TARGET に既存オープンPRがあるか必ず確認する

```bash
gh pr list --head "$TARGET" --state open --json number,title,author,url
```

## 4.2 結果に応じて分岐

### A. 既存PRが存在しない場合
→ ステップ5へ進む。

### B. 既存PRが存在する場合
以下をすべて実行する。**省略可能なものは1つもない。**

1. 検出した既存PRの「番号・タイトル・作者・URL」をユーザーに提示する
2. これからPRに含めようとしている未コミット変更（`git status` / `git diff` / `git diff --cached`）の内容をユーザーに提示する
3. **ユーザーに明示的に質問する**: 「これらの変更を既存PR #N にそのまま追加してよいか」
4. ユーザー回答に応じて分岐:
   - **既存PRに追加してよい（明示許可あり）**: ステップ5へ進む
   - **判断不明 / 回答なし**: ユーザー指示が来るまで待機。続行禁止

## 4.3 やってはいけないこと

- このステップを「ステップ3でユーザーが確認したからもう大丈夫だろう」と推測でスキップすること
- 「ユーザーが --branch で既存ブランチを明示指定したから相乗りでよいはず」と勝手に解釈すること（明示指定でも、未コミット変更が PR スコープに合っているかは別問題）
- 「ついでだから」「同じセッションで作った変更だから」を理由に相乗りを正当化すること

# ステップ5: コミット

1. `git status` で未コミットの変更（staged/unstaged両方）を確認する
2. 変更がある場合:
   - `git diff` と `git diff --cached` で内容を把握する
   - 関連ファイルを `git add` でステージング（`git add -A` は機密ファイル混入リスクがあるため、内容を確認した上で使用）
   - 変更内容を表す commit message で `git commit -m "<message>"` する
3. 変更がなければスキップ

# ステップ6: 検証

`TARGET` ブランチで以下を実行し、失敗したら PR 作成を中止して結果を報告する。

1. プロジェクトの check/lint/typecheck コマンドを特定する
   - `package.json` の `scripts`、`CLAUDE.md` / `README.md` の記述を確認
2. 特定できたコマンドを実行する
3. いずれかが失敗した場合、PR 作成はせず失敗内容をユーザーに報告して終了する

検証コマンドが特定できなかった場合は、その旨を報告しつつ次に進む。

# ステップ7: push

1. `git remote -v` でリモートを確認する
2. `git push -u origin <TARGET>` で push する（既にリモート追跡済みなら通常の push でよい）

# ステップ8: PR作成

1. `git log --oneline <BASE>..HEAD` と `git diff <BASE>...HEAD` で PR に含まれる変更を把握する
2. **コミット数チェック**: `COMMIT_COUNT=$(git rev-list --count <BASE>..HEAD)` でコミット数を数える。**20以上（`>= 20`）の場合**、PR作成を中止し、PRを分割するよう指示して終了する:
   - 理由: Cloudflare Workers CI は push に 20+ commits（または 3000+ file changes）が含まれると [build watch paths](https://developers.cloudflare.com/workers/ci-cd/builds/build-watch-paths/) のパスマッチングをバイパスし、常にプロジェクト全体をビルドする。watch-paths による monorepo ビルド最適化を効かせるには、1つのPR（push）を 19 コミット以下に収める必要がある
   - **確認は取らない**。分割が必要である旨とコミット数 N を報告して終了する
   - **例外**: ユーザーが事前に「コミット数が20以上でもよい」と明示している場合に限り、このチェックを無視してそのまま続行してよい
3. PR本文を一時ファイルに書き出す
   - **必ず** `BODY_FILE=$(mktemp /tmp/pr_body.XXXXXX)` で一意な一時ファイルを作る（固定パス禁止）
   - 書き出し後、ファイルが存在し空でないことを確認する。空または存在しない場合は PR 作成を中止して報告する
4. `gh pr create --title "<title>" --base "<BASE>" --head "<TARGET>" --body-file "$BODY_FILE"` で PR を作成する
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

# ステップ9: 結果報告

成功時の報告：
- PR URL
- PR title
- target branch (`--branch`)
- base branch (`--base`)
- 実行した検証コマンドと結果
- ステップ3 でブランチ切り替えがあった場合はその内容
- ステップ4 で既存PR検出があった場合は分岐の処理内容

失敗時の報告：
- PR作成を中止した理由
- 具体的なエラー内容
- 途中までPRが作られていた場合はそのURL

# 注意事項

- `--branch` は必須。省略時はエラーで即終了する。デフォルト値を設けることは禁止
- ブランチの作成はこのスキルの責務外。存在しない場合は即エラー終了する
- ブランチの切り替えは行うが、未コミット変更がある場合はユーザーに明示確認する（変更を別ブランチに持ち込むことが意図と一致しているか）
- ステップ4 は他のチェックと独立した安全ネット。常に実行する
- 現在の作業ディレクトリが対象リポジトリであることを前提とする
- 検証（lint/typecheck等）が失敗した状態でPRを作らない
- 一時ファイルは必ず `mktemp` で一意に作る。固定パスは禁止
- `git push --force` 等の破壊的操作はユーザーの明示的な許可がない限り行わない
- コミット数が 20 以上のPRは build watch paths がバイパスされるため、分割をユーザーに促す（ステップ8-2）
