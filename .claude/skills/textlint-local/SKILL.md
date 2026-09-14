---
name: textlint-local
description: textlint が入っていない作業空間でも、スキル同梱の textlint で Markdown / テキストを校正する。「textlint かけて」「この文書を校正して」「lint して」など、文書を textlint で確認したいときに使う。文章の内容面のレビュー・推敲は対象外で、内容レビューは別スキルの領分である。
argument-hint: 対象ファイルパス
allowed-tools: Bash, Read, Glob
user-invocable: true
---

作業空間に textlint が導入されていなくても、対象ファイルを変更せずに、スキル同梱の textlint で Markdown / テキストを校正する。文章の内容面を評価したり、構成を推敲したりするスキルではない。

## 引数

$ARGUMENTS

## 手順

### 1. 対象ファイルを特定する

- 引数で渡されたパスを対象にする。相対パスの場合は現在の作業ディレクトリを基準に解決し、存在する通常ファイルであることを確認する。
- 引数が渡されていない場合は、直前の会話で書いた、または編集した文書を候補として提示し、対象を確認してから実行する。候補を特定できない場合は、対象ファイルのパスを尋ねる。
- lint に渡す対象ファイルのパスは、必ず絶対パスに解決する。対象ファイルの内容を必要に応じて `Read` で確認する。

### 2. 作業空間にある textlint を優先する

対象ファイルのディレクトリから親ディレクトリへたどり、対象ファイルを含む作業空間（通常はリポジトリルート）を特定する。その作業空間に `.textlintrc`、`.textlintrc.json`、`.textlintrc.yml` などの `.textlintrc*` と `node_modules/.bin/textlint` が両方ある場合は、作業空間の設定ファイルとバイナリを使う。作業空間固有のルールや用語辞書を尊重するためである。

作業空間の textlint を使う場合は、対象ファイルを絶対パスで渡す。たとえば、作業空間と設定ファイルを解決したうえで、次の形で実行する。

```bash
<作業空間>/node_modules/.bin/textlint -c <作業空間の.textlintrc設定> <対象ファイルの絶対パス>
```

### 3. 同梱 runtime を初回セットアップする

作業空間に textlint がない場合だけ、同梱 runtime を使う。次のバイナリが存在しなければ初回セットアップである。

```text
/Users/cancer/.claude/skills/textlint-local/runtime/node_modules/.bin/textlint
```

初回は依存関係のインストールに時間がかかることを先に伝え、次のコマンドを実行する。`npx` は使わない。

```bash
npm install --prefix /Users/cancer/.claude/skills/textlint-local/runtime
```

### 4. 同梱 runtime で実行する

同梱 runtime を使う場合は、インストール済みバイナリの絶対パスを直接呼び出し、同梱設定を `-c` で指定する。`<対象ファイルの絶対パス>` は実際の絶対パスに置き換える。

```bash
/Users/cancer/.claude/skills/textlint-local/runtime/node_modules/.bin/textlint -c /Users/cancer/.claude/skills/textlint-local/runtime/.textlintrc.json <対象ファイルの絶対パス>
```

この形は、`runtime/` 以外のディレクトリを cwd とし、`runtime/` 外の絶対パスを対象にしても、同梱設定からルールパッケージを解決できることを確認済みである。対象ファイルの側に移動して実行する必要はない。

### 5. 結果を報告する

textlint の出力と終了コードを確認し、指摘は次の形式で報告する。

```text
ファイル:行:列 — ルール名 — 内容
```

複数行の説明がある指摘は、該当箇所と要点が分かるようにまとめる。指摘が 0 件なら「指摘は 0 件」と明示する。

指摘がある場合の textlint の終了コード `1` は、検査自体の失敗ではなく、指摘が見つかったことを示す。終了コード `0` は指摘なしである。それ以外の終了コードや設定・実行エラーは、検査を完了できなかったものとして原因を報告する。

### 6. 文書を書き換える場合

`--fix` は既定で使わない。ユーザーが修正まで明示的に依頼した場合だけ、`--fix` を付ける前に、どの行をどのルールに従ってどう書き換えるかを伝える。明示的な依頼がない限り、検査結果の報告だけにとどめる。

## 注意

- 対象ファイルの側には一切ファイルを作らない。設定ファイルも `node_modules` も対象ファイルの作業空間には置かない。
- 同梱設定は日本語技術文書向けの `preset-ja-technical-writing` ベースである。英語文書や、別の文体・校正方針を持つ文書には合わないことがある。その可能性が分かったらユーザーに伝える。
