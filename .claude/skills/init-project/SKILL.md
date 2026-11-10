---
name: init-project
description: 空のディレクトリから新規プロジェクトを初期構築し、テストの実行と評価ができる状態（テスト実行・型検査・lint・format・未使用検出・カバレッジのファイル出力・CI）まで揃えるスキル。「新しいプロジェクトを作る」「ゼロから作る」「scaffolding したい」「リポジトリを新規に立てる」「新規で MCP サーバ / Worker / CLI を作りたい」と言われた場面では必ず使う。テスト環境やカバレッジ・CI の話が出ていなくても、新規プロジェクトの作成であれば使う。既存リポジトリへのテスト環境の後付けは対象外。CLAUDE.md だけを生成するのはビルトイン init の領分、既存コードへの実装は dev-workflow の領分
argument-hint: "[<path>] [--stack workers|web|lib|rust]"
allowed-tools: Bash, Read, Write, Edit, Glob, Grep, AskUserQuestion, Skill, mcp__knowledge__search_knowledge, mcp__knowledge__read_knowledge
user-invocable: true
---

空のディレクトリから、**テストの実行と評価ができる状態**のプロジェクトを立ち上げる。

中心原則は2つある。

1. **骨組みは既存の scaffolder に任せ、このスキルが足すのは評価環境の差分だけである。** 骨組み（依存の初期構成・エントリポイント・設定の雛形）を自前テンプレートで抱えると、その依存表がスキルの中で陳腐化する。C3 / vite / `cargo init` は常に最新の骨組みを吐くので、そこには手を出さない。
2. **完成の判定は文章ではなくコマンドの終了コードで行う。** 「揃った」と書いても揃っていないことがあるので、下記の検査項目のコマンドが実際に exit 0 になることを確認して初めて完了とする。

references 内の `<skill>` は本スキルのディレクトリ（`~/.claude/skills/init-project`）を指す。

**検査は `&&` で繋がず1つずつ実行し、都度 `$?` を見る。** 繋ぐと最初に落ちた時点で止まり、残りの項目の状態が分からない。パイプも挟まない（このシェルは zsh なので `${PIPESTATUS[0]}` では取れない）。

**終了コードそのものが環境側で書き換えられていないか疑う。** この環境には Bash をラップするフック（rtk）があり、lint の出力を別ツールの形式として解釈しようとして、成功したコマンドに exit 1 を返した実例がある。終了コードと出力の内容が食い違うときは、ラップを迂回して素のコマンドで確認する。

## 適用条件

対象は**空のディレクトリ、または `.git` もマニフェスト（`package.json` / `Cargo.toml`）も存在しないディレクトリ**である。

適用しない場面:

- 既存リポジトリにテスト環境を後付けする → 本スキルは扱わない（既存構成の調査と非破壊的な統合が主で、判断の中身が別物になる）
- CLAUDE.md だけを作る → ビルトインの `init`
- 既存コードへの実装・修正 → `dev-workflow`
- 「使い捨て」「テスト不要」と明示された単発スクリプト → inline で書く

## 揃える検査項目

node 系統（`workers` / `web` / `lib`）は7項目、`rust` 系統は未使用検出を除く6項目である。

| 項目 | 意味 | 系統 |
|---|---|---|
| テスト実行 | テストランナーが実際にテストを走らせて緑になる | 全 |
| 型検査 | `tsc --noEmit` 相当が通る | 全 |
| lint | 非破壊の lint が通る | 全 |
| format | 差分チェック（書き換えではない）が通る | 全 |
| 未使用検出 | 未使用のファイル・エクスポート・依存が無いことを knip が確認する | node のみ |
| カバレッジ | **行情報を持つファイル**として出力される（JSON / LCOV） | 全 |
| CI | 上記が CI 設定に載っている | 全 |

カバレッジをファイルとして出す理由は、`test-review` が評価の入力にそれを要求するためである（`~/.claude/skills/test-review/references/report-inputs.md`）。行情報の無い `coverage-summary.json` では変更行と突き合わせられないので、`json`（istanbul の `coverage-final.json`）か LCOV を出す。

閾値は **90** を全項目に置く。新規時点ではコードが 0 行なので分母 0 となり、この閾値は無条件で通る。**閾値が効き始めるのはユーザーが最初のコードを書いた瞬間から**であり、初日から縛るためではなく「これ以上未検証の分岐を増やさない」保持線として置く。

そのためには **計測対象の指定が必須**である。vitest 4 では `coverage.all` が廃止され、`coverage.include` を明示しないと**テストから import されたファイルだけ**が計測対象になる。指定を欠くと、未検証のコードを置いても分母は 0 のまま・`coverage-final.json` は `{}`・exit 0 のままで、保持線は永久に作動しない（実測で確認した）。だから coverage スクリプトには `--coverage.include=src/**` を必ず入れる。

これは「対象を絞って閾値を通す」ことの逆である。絞ると通ってしまう性質を持つのは `--coverage.exclude` の方で、`include` は**未検証のファイルを分母に載せるための指定**にあたる。

未使用検出（knip）を置く理由は、**lint が見ている範囲と重ならない**ことにある。oxlint が見るのはファイルの内部であり、「どこからも import されないファイル」「使われないエクスポート」「宣言されているが誰も使わない依存」はファイルを跨いだ関係なので lint では検出できない。カバレッジ閾値と同じく、新規時点では未使用が 0 件なので無条件で通り、**未使用が増え始めた瞬間から**保持線として作動する。

knip は JS/TS を対象とするため、`rust` 系統には置かない。

**knip が依存を「使用済み」と判定する根拠は npm script である。** `oxlint` / `oxfmt` は knip のプラグインを持たないので、スクリプトに登録する前に knip を走らせると `Unused devDependencies` で落ちる（実測で確認した）。差分を当てる順序として、スクリプト登録より後に knip を実行する。

**設定ファイルが要るのは Workers 系統だけである。** C3 の `vitest.config.mts` は `test` キーを持たないため、knip の Vitest プラグインがテストファイルの entry を導出できず、`test/index.spec.ts` を `Unused files` として報告する（`knip --debug` で、この設定から得られた entry が `src/vite-env.d.ts` だけであることを確認した）。加えて `cloudflare:test` の import が未宣言の依存 `cloudflare` として報告される。両方を `assets/knip-workers.json` で吸収する。`lib` / `web` 系統は設定ファイル無しで exit 0 になる（実測で確認した）。

ミューテーションテストは検査項目に含めない。TypeScript では Stryker が TypeScript 7 に未対応で導入できないという外的制約があり、Rust では `cargo-mutants` を導入するが CI では走らせない（全変異ごとにスイートを回すため実行時間が読めない）。

## 系統

| `--stack` | 骨組み | 用途 |
|---|---|---|
| `workers` | C3（`npm create cloudflare@latest`） | Cloudflare Workers。Astro / SvelteKit 等のフレームワーク付き Web もここ（C3 の `--framework`） |
| `web` | `npm create vite@latest` | Workers に載せない Web アプリ |
| `lib` | `npm init -y` + 最小構成 | ライブラリ / CLI / MCP サーバ |
| `rust` | `cargo init --lib` | Rust |

各系統の具体的なコマンドは `references/<stack>.md` にある。**その系統のファイルだけを読む**（他系統は読まない。同型の説明でコンテキストを消費しても判断は良くならない）。

## 手順

### 0. 対象ディレクトリと系統を確定する（着手前に必ず行う）

**確定していない状態で骨組み生成コマンドを実行してはならない。** 系統を取り違えると、その誤りが以降のすべての生成物に伝播する。空ディレクトリには観測できる手がかりが無いため、確定の材料は引数か本人の回答しかない。

1. 対象ディレクトリを決める（引数のパス、省略時は現在の作業ディレクトリ）
2. そのディレクトリの状態を機械的に確認する:
   ```bash
   test -d "$DIR" && echo EXISTS || echo NOT_CREATED
   test -e "$DIR/.git" && echo HAS_GIT
   test -e "$DIR/package.json" -o -e "$DIR/Cargo.toml" && echo HAS_MANIFEST
   ```
   `HAS_GIT` か `HAS_MANIFEST` が出たら**本スキルの対象外**である。停止して、後付けは扱わないことを伝える。`NOT_CREATED` は正常系で、scaffolder がディレクトリごと作る
3. **パスとプロジェクト名を対応させる。** C3 と `cargo init` が引数に取るのはディレクトリ名（= プロジェクト名）なので、`$DIR` の親へ移動して basename を渡す:
   ```bash
   cd "$(dirname "$DIR")" && NAME="$(basename "$DIR")"
   ```
4. `--stack` が渡されていなければ、依頼文から系統を推定する（既定の初期値は `workers`）
5. **推定した系統・作成先パス・プロジェクト名を提示して確認を取る。** 承認を得るまで次へ進まない

用途は依頼文にしか書かれていないことが普通である（「MCP サーバを作りたい」と言う人は `--stack lib` とは言わない）。だから推定した内容を必ず見せる。

### 1. 骨組みを生成する

`references/<stack>.md` のコマンドを実行する。

### 2. 差分を当てる

依存の追加とスクリプトの登録は**公式 CLI だけで行う**（`npm i -D` / `npm pkg set` / `cargo add --dev`）。`package.json` を読んで書き戻す処理を自前で持つと、同じ入力でも結果が揺れる。`npm pkg set` はドット記法で対象キーだけを書き換えるので、他のキーや依存に触らずに何度でも同じ結果になる。

設定ファイル（`.oxlintrc.json` / `.oxfmtrc.json` / `.gitignore` / CI の YAML）は `assets/` から配置する。

**既に同名のファイルが存在する場合は上書きせず、そのファイルを正とする。** scaffolder が吐いた設定（Workers の `vitest.config.ts` の pool 設定など）を消すと、テストが動かない構成が黙って残る。上書きの代わりに、必要な指定（カバレッジの reporter と閾値）はスクリプト側のコマンドラインに置く。

**依存の導入が公開直後のバージョンで失敗することがある。** この環境の npm には safe-chain の minimum package age チェックがあり、公開されて間もない版は `npm error code E403 ... blocked by safe-chain direct download minimum package age` で拒否される（`oxlint@1.81.0` で実測）。失敗したら、エラーに出ているパッケージを**直前の版に固定して**入れ直す（例 `npm i -D oxlint@1.80.0`）。チェックを無効化するフラグは使わない。

**`.gitignore` は lint より先に置く。** oxlint は `.gitignore` を無視パターンとして読むので、これが無いと `node_modules/` 配下を走査して、依存パッケージの配布物に対する指摘で lint が落ちる（実測で確認した）。

パッチを当て終えたら、**検査の前に formatter を1回書き換えモードで走らせる**（`npm run format`）。`npm pkg set` が書き戻す `package.json` の整形は oxfmt の整形と一致しないため、これを省くと `format:check` が最初から落ちる（同じく実測で確認した）。

### 3. 実装コードを外し、placeholder テストを置く

scaffolder が吐く hello-world の実装コードは残さない。ユーザーが最初に書くコードの場所を占領するうえ、それを覆うためのテスト（実装をなぞるテスト）を書く必要が生じる。

- `src/` を空にし、placeholder テストを1本置く
- 例外は Workers 系統である。`wrangler.jsonc` の `main` が指すエントリは必須なので、固定レスポンスを返す最小のエントリを残し、それを叩く placeholder テストで覆う
- Rust も `lib.rs` を空にし、placeholder テストを1本置く

テストを必ず1本置く理由は、**テストが 0 件のときの挙動がランナーによって違う**ことにある。vitest はテスト 0 件で `No test files found` として exit 1 になるが、`cargo test` は 0 件でも exit 0 で成功する。1本置けば、テストが実際に実行されていることが終了コードに表れる。

**placeholder テストの置き場所は、その系統の `tsconfig.json` の `include` に合わせる。** 型検査の入力が 0 件になると `error TS18003: No inputs were found in config file` で落ちるため、`src/` を空にした状態では「テストが include の範囲に入っているか」が型検査の成否を決める。

`tsconfig.json` はコメント付き（JSONC）のことが多く、`node -e "require('./tsconfig.json')"` は `SyntaxError` で落ちる（C3 の生成物で実測）。中身を直接読む。

```bash
grep -nE '"(include|exclude)"' tsconfig.json
```

- `include` が `test/` を含む（本スキルが配置する `lib` 系統の tsconfig） → `test/placeholder.test.ts`
- `include` が `src` だけ（vite の生成物） → `src/placeholder.test.ts` に置く
- `exclude` に `test` がある（C3 の生成物） → テストは**ルートの型検査の対象外**である。エントリが残っているので `tsc --noEmit` は通るが、テストの型は検査されていない。この事実を CLAUDE.md に書き、テスト側を検査するコマンド（`tsc --noEmit -p test/tsconfig.json`）を併記する

scaffolder の tsconfig を書き換えて `test/` を含めるやり方は採らない（Q15 の方針どおり生成物を正とする）。テストを `src/` 配下に置く構成には実績がある（`~/repos/codegrid-cloud-broadcast/vitest.config.ts` の include は `src/**/*.test.ts`）。

**カバレッジの provider は系統で違う。** Workers（workerd 上で実行）では `@vitest/coverage-v8` が `Error: The Session method is not implemented` で落ちるので istanbul を使う。それ以外の Node 上で走る系統は v8 で動く。どちらでも出力は `coverage/coverage-final.json` である。

**テスト実行スクリプトが watch モードになっていないか確かめる。** scaffolder は `test: vitest`（watch）を置くことがあり、そのままだと CI が終了しない。`vitest run` に上書きする。

### 4. CLAUDE.md を置く

`assets/CLAUDE.md.template` を元に、プロジェクト固有の規約と開発規律を書く。

書くのは**キー名や設定ファイルから読み取れない情報**に限る:

- どの npm script が非破壊でどれが破壊的か（`lint` は非破壊、`lint:fix` が破壊的）
- カバレッジ閾値 90 が保持線であること
- 未使用検出（knip）も同じ保持線であること。node 系統のみに置いていること
- placeholder テストは最初の実装で差し替える前提であること
- ミューテーションテストを入れていない理由（Stryker が TS 7 未対応）と、対応後に再検討すること
- Workers 系統なら Workers Builds の接続手順（後述）

開発規律（TDD・実装の進め方・PR の作り方）は**本文をコピーせず、`~/.claude/skills/<name>/SKILL.md` の絶対パスを参照する形で書く**。コピーするとスキル側の更新に追随しなくなる。

**CLAUDE.md は検査より先に書く。** oxfmt は Markdown も整形対象にするため、検査を通したあとに CLAUDE.md を追加すると、その時点から `format:check` が落ちる状態になる（実測で確認した）。

### 5. 検査項目を実行して確認する

`references/<stack>.md` の検査コマンドを順に実行し、**すべて exit 0 であることを確認する**。落ちたものがあれば、その時点で報告して止まる（生成物を残したまま原因を伝える。中途半端に「完了」と言わない）。

lint が実際に機能していることを疑う場合は、意図的に違反を含む一時ファイルを置いて exit 1 になることを確かめてから消す。設定の誤りで**何も検査していないのに緑になる**経路があるため、緑という結果だけでは検査が働いている証拠にならない。

### 6. git 初期化と最初のコミット

```bash
git init -b main && git add -A && git commit -m "chore: プロジェクトの初期構築"
```

ブランチ名を明示するのは、`assets/ci-node.yml` と `assets/ci-rust.yml` の push トリガが `main` 固定だからである。既定ブランチ名の設定に依存させると、CI が発火しないリポジトリができる。

コミットは `gh-commit` スキルを経由しない。同スキルは変更を論理単位へ分割する手順だが、scaffold 一式は分割する単位を持たない（すべてが「プロジェクトの初期構築」という1単位）。以降の変更は通常どおり `gh-commit` の領分である。

リモートリポジトリの作成（`gh repo create`）と push は**行わない**（命名・可視性・組織の選択を伴う外向きの操作なので、本人が決める）。

`src/` を空にした系統では、空ディレクトリは git の管理対象にならない（clone しても `src/` は現れない）。型検査はテスト側で入力が満たされるので実害は無いので、`.gitkeep` は置かない——最初の実装で消す前提のファイルを増やさない。

### 7. Workers 系統のみ: Workers Builds を使うと決まっているときだけデプロイする

`wrangler deploy` を1回実行する目的は、**Workers Builds の trigger を貼れる状態を作ること**である（trigger は既存の Worker に紐づくので、Worker が先に存在している必要がある）。

したがって、リモートリポジトリを作らない場合はこの操作の目的が成立しない。**目的が無いまま実行すると、アカウント上に使われない Worker を残すだけになる**（`workers.dev` のサブドメインも占有する）。手順0の確認で Workers Builds を使うと合意できているときに限って実行する。

実行する場合:

```bash
npx wrangler whoami   # どのアカウントに作られるかを確認する。会社アカウントなら特に確認を取る
npx wrangler deploy
```

**失敗しても停止しない。** 認証切れ・アカウント未選択・名前衝突で失敗しうるが、骨組みは正しく出来ているので、理由を報告して続行する。作ってしまった Worker を消すのは `npx wrangler delete --name <name>` である。

### 8. 報告する

最後に、次を明示して終える:

- 検査項目の実行結果（どのコマンドが exit 0 だったか）
- **未検証の項目**: CI 設定は push していないので未検証であること
- Workers 系統なら、Workers Builds の接続が手動で残っていること
- `wrangler deploy` を試みた場合はその結果

## Workers Builds（Workers 系統のみ）

品質検査は GitHub Actions が回し、ビルドとデプロイは Cloudflare 側の Workers Builds に任せる構成を取る。GitHub Actions を品質検査に残す理由は、レポートファイルを後から取り出せる必要があるためである（Workers Builds からカバレッジのレポートファイルを回収する手段は確認できていない）。

接続はこのスキルの範囲外である。以下を CLAUDE.md に手順として書き残す（Cloudflare 公式ドキュメント: https://developers.cloudflare.com/workers/ci-cd/builds/ ）:

1. ダッシュボードで "Cloudflare Workers & Pages" GitHub App をインストールする（**一度だけ手動が必要**）
2. リモートリポジトリを作って push する
3. REST API で接続と trigger を作る（`PUT /builds/repos/connections` → `GET /workers/scripts` → `POST /builds/triggers`）。API トークンは **user-scoped** が必須で、`Workers Builds Configuration: Edit` と `Workers Scripts: Read` の権限が必要
4. `wrangler.jsonc` の `name` がダッシュボードの Worker 名と一致していること（不一致だとビルドが失敗する）
5. Preview URL が必要なら `preview_urls = true` を設定する

ビルド/デプロイのコマンドはリポジトリ内で宣言できない（"Workers Builds does not honor the configurations set in Custom Builds within your Wrangler configuration file"）。Open Beta であり、API の形は変わりうる。

## やってはいけないこと

- **系統と作成先を確認せずに骨組み生成コマンドを実行する**（誤りが全生成物に伝播する）
- **既存の設定ファイルを上書きする**（scaffolder 側の必要な設定が黙って消える）
- **カバレッジ対象を絞って閾値を通す**（`--coverage.exclude` で未カバーのコードを外すのは、閾値を置いた目的を空洞化させる）
- **検査項目のどれかが落ちた状態で「完了」と報告する**
