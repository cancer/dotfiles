---
name: test-analyze
model: opus
description: リスクベースのテストギャップ分析を行い、テストが不足している高リスク箇所を特定する。レポート提示後の「low も調べて」等、low リスクの追加分析依頼にも対応する
argument-hint: <target-path> [--handler-pattern <pattern,...>] [--analyze-low] [--use-cache]
allowed-tools: Read, Glob, Grep, Bash
user-invocable: true
---

指定された実装コードとテストコードを分析し、リスクの高いテストギャップを特定・提案する。

分析は3段階のパイプラインで実行する。Stage1/2 は機械的な列挙・集計、Stage3 が判断を伴う抽出である（後述「各 Stage の実行」を参照）。各段は入力が有限の列挙集合かつスキーマで完了判定でき、確実に終了する。Claude 主スレッドはオーケストレーションと最終レポート整形のみを担当し、open-ended な再帰的分析を行わない。

## 引数

$ARGUMENTS

形式：
- 第1引数（必須、ただし `--use-cache` 指定時は省略可）: 分析対象のパス（ファイル / ディレクトリ / glob）
- `--handler-pattern <pattern,...>`: ハンドラ判定用パターン（カンマ区切り）。パス glob、import 名、デコレータ、関数 export 形のいずれも可
- `--analyze-low`: **対象リスク選択フラグ**。Stage3 の対象を `risk == "low"` のみに切り替える（既定は `high + medium`）。`--use-cache` の有無とは独立
- `--use-cache`: **中間ファイル再利用フラグ**。`.claude/test-analyze/` 配下の既存 `stage1-files.json` / `stage2-triage.ndjson` をそのまま使い、Stage1 と Stage2 をスキップする。`--analyze-low` の有無とは独立

組み合わせの典型例：
| ケース | フラグ | 挙動 |
|---|---|---|
| 初回実行 | （なし） | Stage1〜4 を全て実行、Stage3 は high+medium |
| 後追いで low も詳細化 | `--analyze-low --use-cache` | Stage1/2 をスキップし、Stage3 を low に対して実行、レポートに low 詳細を追記 |
| 同じ対象で high+medium を再レポートしたい | `--use-cache` | Stage1/2 をスキップ、Stage3（high+medium）を再生成 |
| 実装が変わったので low を新規に解析 | `--analyze-low` | Stage1〜2 を再実行、Stage3 は low のみ |

なお、ユーザーが Stage4 受領後に「low も調べて」「low の詳細が欲しい」等の自然言語で追加分析を依頼した場合、Claude は **`--analyze-low --use-cache`** を付けて本 skill を再起動する形で応答する（コードに変更が無い前提でキャッシュを再利用）。

## 実行手順

### 0. 事前検証・モード判定（Claude 主スレッド）

#### 0.0 フラグ解釈
- `--use-cache` が指定されている → Stage1 と Stage2 を**スキップ**し、`.claude/test-analyze/stage1-files.json` と `.claude/test-analyze/stage2-triage.ndjson` を再利用する
  - 必須前提: 両ファイルが存在すること。どちらか欠けていれば reject し「先に `--use-cache` 無しで実行してください」と案内
  - `--use-cache` 指定時は handler-pattern の解決（0.1）も省略可（Stage2 を再実行しないため必要ない）。引数 / CLAUDE.md の解決を試み、見つからなくても reject せず処理を継続する
- `--analyze-low` が指定されている → Stage3 の対象を `risk == "low"` のみに切り替える
- `--use-cache` と `--analyze-low` は独立に評価する。両方無し → 全段実行、Stage3 は high+medium / 両方あり → キャッシュ利用＋ low のみ Stage3 / 片方だけ → 上記表のとおり

#### 0.1 ハンドラ検出規則の解決
1. 引数 `--handler-pattern` があればそれを使う
2. なければプロジェクト直下の CLAUDE.md から `## test-analyze: handler patterns` 節を読み取る
3. どちらにもなければ skill を **reject** し、以下のメッセージで終了：

   > test-analyze: ハンドラ検出規則が未定義のため処理を継続できません。`--handler-pattern` 引数で渡すか、プロジェクトの CLAUDE.md に `## test-analyze: handler patterns` 節を追加してください。
   >
   > 例:
   > ```md
   > ## test-analyze: handler patterns
   > - src/handlers/**
   > - src/pages/api/**
   > - @app.route
   > - export const (GET|POST|PUT|DELETE)
   > ```

#### 0.2 中間ファイル領域の準備
- 解決した handler-pattern とその出典（引数 / CLAUDE.md）を以降の stage プロンプトに含める前提で保持する
- プロジェクト直下に `.claude/test-analyze/` ディレクトリを用意（無ければ作成）
- 既存の `stage*.{json,ndjson}` は前回キャッシュとして残置（再実行時の再開判断に使う）

#### 0.3 各 Stage の実行

**このスキルはどのモデルで実行するかを判断しない。** 実行エンジンと推論量の選択は呼び出し側の責務である（`dev-workflow` は `delegate-to-codex` 経由でこのスキルを Codex に実行させる）。

各 Stage は、このスキルを実行しているエンジンの中で順に処理する。プロンプト本体（read-only 制約・入出力スキーマ・完了判定）は Stage ごとに定義され、実行エンジンによらず共通である。

Stage1 / Stage2 は機械的な列挙と集計であり、判断を伴わない。サブエージェントを起動できる環境なら、コンテキストを節約するためにこの2段を軽量なワーカーへ切り出してよい。切り出す場合も、read-only であること・中間ファイルの出力先・完了判定の条件をプロンプトへ明記する。

### 1. Stage1: 対象列挙（read-only）

#### 入出力
- 入力: 分析対象パス（引数）
- 出力: `.claude/test-analyze/stage1-files.json`

#### 出力スキーマ
```json
{
  "files": [
    {
      "src": "src/foo.ts",
      "test": "src/foo.test.ts",
      "functions": [
        { "name": "doX", "start_line": 10, "end_line": 42, "exported": true }
      ]
    }
  ]
}
```

#### 委任
「各 Stage の実行」（0.3）に従い、以下の趣旨のプロンプトで処理する（read-only）。

> 対象 `<target-path>` 配下の実装ファイルとテストファイルのペアを列挙し、各実装ファイルから関数/メソッドのシグネチャと開始・終了行を抽出してください。
> - 制約: 対象ファイル自身のみ読む。import 先は辿らない。read-only（ファイル書き換え禁止）。
> - 出力先: `.claude/test-analyze/stage1-files.json`
> - スキーマ: 上記 JSON
> - 完了判定: 列挙対象ファイルすべてが `files` 配列に含まれた時点で終了

### 2. Stage2: シグナル抽出 + 粗トリアージ（read-only）

Stage1 の列挙結果に対し、機械的シグナルだけを集計してリスクを high/medium/low に粗くラベリングする。判断ではなく **観測可能なシグナルの集計** に倒すことで、確実に終了させる。

#### 入出力
- 入力: `.claude/test-analyze/stage1-files.json`
- 出力: `.claude/test-analyze/stage2-triage.ndjson`（1関数1行 NDJSON）

#### シグナル定義（すべて grep / count で機械的に集計）
1. **分岐数**: 関数本体内の `if|else if|switch|case|while|for|三項演算子` の出現回数
2. **外部依存数**: 関数本体から呼び出される import 由来識別子の数（import 行から名前を集めて関数本体で grep）
3. **可逆性キーワード**: 関数本体または呼び出し関数名に `delete|drop|unlink|truncate|destroy|\brm\b` を含むか（boolean）
4. **影響範囲キーワード**: 関数名 / ファイル名 / import 文字列に `auth|payment|billing|persist|session|token|password` を含むか（マッチした語）
5. **境界/ハンドラ判定**: ファイルパス / export 構造 / デコレータが解決済み handler-pattern にマッチするか（マッチしたパターン）

#### 決定的マッピング規則
- 可逆性キーワードあり **OR** 境界判定一致 **OR** 影響範囲キーワード一致 → **high**
- 上記いずれでもなく 分岐数 ≥ 5 **OR** 外部依存数 ≥ 3 → **medium**
- それ以外 → **low**

#### 出力スキーマ（各行 = 1関数）
```json
{
  "src": "src/foo.ts",
  "name": "doX",
  "start_line": 10,
  "end_line": 42,
  "test_exists": true,
  "signals": {
    "branches": 7,
    "external_deps": 2,
    "destructive_keyword": false,
    "scope_keyword": "auth",
    "handler_match": "src/handlers/**"
  },
  "risk": "high",
  "evidence": "handler-match: src/handlers/**; scope-keyword: auth"
}
```

#### evidence 制約
- 1行 ≤ 80字
- 観測されたシグナル名と該当値のみを並べる（自由記述禁止、推論禁止）

#### 委任
「各 Stage の実行」（0.3）に従い、以下の趣旨で処理する（read-only）：

> Stage1 の出力 `.claude/test-analyze/stage1-files.json` を入力に、各関数につき 5 シグナル（分岐数 / 外部依存数 / 可逆性キーワード / 影響範囲キーワード / 境界・ハンドラ判定）を機械的に集計し、決定的規則で high/medium/low をラベリングしてください。
> - 集計手段は grep / count のみ。判断・推論は禁止。
> - シグナル定義: 上記
> - マッピング規則: 上記
> - 制約: 対象ファイル自身のみ読む。import 先は辿らない。read-only。
> - evidence は 1行 ≤ 80字、観測シグナル名と値のみ。
> - 出力先: `.claude/test-analyze/stage2-triage.ndjson`
> - 完了判定: 入力に含まれる全関数が出力に1行ずつ書かれた時点で終了

### 3. Stage3: 深い推論（read-only、対象リスクは `--analyze-low` に依存）

Stage2 の粗評価結果に対し、命題抽出・[要確認]タグ・テストレベル判断を行う。対象とするリスクレベルはフラグで決まる：

- `--analyze-low` 無し（既定）: `risk == "high" || risk == "medium"` の関数集合
- `--analyze-low` 有り: `risk == "low"` の関数集合のみ

`low` を既定で深掘りしないのは、件数規模が大きくなりがちで Stage3 のコスト/時間を支配しやすいため。必要なときだけ `--analyze-low` で実行する分離。

#### 入出力
- 入力: `.claude/test-analyze/stage2-triage.ndjson` から `--analyze-low` に応じた risk の行を抽出
- 出力: `.claude/test-analyze/stage3-detail.ndjson`（1関数1行 NDJSON、追記方式）。`--analyze-low` 有無の双方で同じファイルに追記し、`risk` フィールドで区別する

#### バッチ処理
- 5件ずつ委任先に投げる（K = 5）。各バッチが独立に完了し、出力ファイルに追記
- バッチ単位で再実行可能。途中で止まっても出力済みのバッチは破棄せず再開できる

#### 各関数あたりのスキーマ上限（出力上限の固定により reasoning 膨張を防ぐ）
- `propositions`: 命題 ≤ 5
- `needs_review_tags`: ≤ 3
- `recommended_test_level`: `unit | integration | e2e` の1つ
- `rationale`: ≤ 200字

#### 出力スキーマ
```json
{
  "src": "src/foo.ts",
  "name": "doX",
  "risk": "high",
  "propositions": [
    { "text": "認証失敗時は 401 を返す", "source": "function-name", "needs_review": false }
  ],
  "needs_review_tags": ["エラーレスポンスの形式が未確定"],
  "recommended_test_level": "integration",
  "rationale": "境界ハンドラかつ認証関連、外部I/Oあり"
}
```

#### 委任（バッチごと）
「各 Stage の実行」（0.3）に従って処理する。本 skill は research/diagnosis 用途なので、**read-only で実行**する旨をプロンプトに必ず含める：

> 以下の N 件（N ≤ 5）の関数について、命題リスト・[要確認]タグ・テストレベルを抽出してください。
> - 入力: <Stage2出力からの該当バッチ抜粋>
> - 各関数あたり: 命題 ≤ 5、[要確認] ≤ 3、テストレベル ∈ {unit|integration|e2e}、rationale ≤ 200字
> - 制約: 対象関数の本体と同ファイル内の関連関数のみ読む。import 先は辿らない。read-only。
> - 出力先: `.claude/test-analyze/stage3-detail.ndjson` に追記
> - 完了判定: バッチ内の N 件すべてが1行ずつ追記された時点で終了

### 4. 最終レポート整形（Claude 主スレッド）

#### 入力
- `.claude/test-analyze/stage2-triage.ndjson`（全件のリスクラベルと件数集計用）
- `.claude/test-analyze/stage3-detail.ndjson`（深掘り済み。risk フィールドで high/medium/low を区別）

#### 処理
- Stage3 の結果を risk 高い順に整列（high → medium → low、low は存在する場合のみ）
- `--analyze-low` 無しの実行: high+medium を主テーブルに、low は件数集計のみ
- `--analyze-low` 有りの実行: 既存の high+medium 出力には触れず、low 詳細セクションを追加して提示
- 部分読み込み可能：必要な行のみ Read tool の offset/limit や grep で参照する

## 出力形式

### テストギャップ（リスクの高い順）

| 箇所 | リスク | 根拠 | 推奨テスト | テストレベル |
|------|--------|------|------------|--------------|
| `file:line` | high/medium | Stage2 evidence + Stage3 rationale | 追加すべきテストの具体例（Stage3 propositions ベース） | unit/integration/e2e |

- low はテーブルに含めず、件数のみ集計表示する
- 「テストは十分である」という判定は出さない
- ギャップが見つからない場合でも「見落としの可能性がある」旨を記載する

### 仕様推測の [要確認] 項目

Stage3 の `needs_review_tags` を関数横断で集約して提示する。

### low リスク件数 / 詳細

- `--analyze-low` 無しの実行: Stage2 の low 件数を `<件数> 件（深掘りスキップ。`/test-analyze --analyze-low --use-cache` または「low も調べて」で追加分析可能）` の形で1行記載する
- `--analyze-low` 有りの実行後: `low` 行が `stage3-detail.ndjson` に存在する場合、上記の主テーブルに準じた書式で「low リスク詳細」サブセクションを追加する

### メタ情報

- handler-pattern の出典（引数 / CLAUDE.md）と決定値
- 中間ファイルの位置: `.claude/test-analyze/`
- 各 stage の所要件数（対象関数数 / high / medium / low）
- 分析対象パス

## エラーハンドリング・再実行

- 各 stage は中間ファイルに書き出した後に終了するため、Stage2 や Stage3 で委任先がエラー終了した場合、当該 stage から再実行できる
- 再実行時は `.claude/test-analyze/` の既存ファイルを参照し、未完了の stage（または Stage3 の未処理バッチ）から再開する
- ハンドラ検出規則が変更された場合、`--use-cache` を付けず Stage2 を再実行する
- low の追加分析を依頼され、かつコードに変更が無い場合は `--analyze-low --use-cache` で再起動し、Stage1/2 はスキップして Stage3 から開始する
- コードが変わったあとに low の追加分析が必要な場合は、`--analyze-low` のみ（`--use-cache` 無し）で再実行する
