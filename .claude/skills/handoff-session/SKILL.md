---
name: handoff-session
description: 現行の Claude Code セッションで「コンテキストがいっぱいになった」「引き継ぎたい」「別セッションで続けて」と依頼されたときに、作業を新しい Claude Code セッションへ引き継ぐために使う。引き継ぎ文書の作成、新しい herdr ペインでの claude 起動、作業種別に応じた workflow への継続依頼までを扱う。残作業の実行・検収・PR 作成は引き継ぎ文書で指定した workflow、別モデルへの委任は delegate-to-codex の領分である
argument-hint: "[引き継ぐ作業の説明] [--multiplexer <名前>] [--mode <権限モード>] [--worktree|--no-worktree] [--cwd <パス>]"
allowed-tools: Bash, Write, Read, AskUserQuestion
user-invocable: true
---

現行の Claude Code セッションの作業を、新しい Claude Code セッションへ一度だけ渡す。引き継ぎ文書を正確な前提として残し、herdr の新しいペインで claude を起動し、文書を読んだセッションへ引き継ぎ文書で指定した workflow の継続を依頼する。

## 引数

$ARGUMENTS

- **引き継ぐ作業の説明**: 省略を許す。省略時は、現行セッションで確認できる直近の作業を対象にする。
- **`--multiplexer <名前>`**: 既定は `herdr`。`herdr` 以外の値が渡されたら、その経路は未実装なので実行せず、ユーザーへ伝えて終了する。
- **`--mode <権限モード>`**: 既定は `auto`。値を解釈・変更せず、`claude --permission-mode` の値として渡す。
- **`--worktree` / `--no-worktree`**: 既定は git リポジトリなら worktree を使う。判定は作業説明や依頼文の表現ではなく、`git -C <cwd> rev-parse --git-dir` の成否で行う。`--no-worktree` が渡されたら `--worktree` を付けない。
- **`--cwd <パス>`**: 既定は現在の作業ディレクトリ。ペインの作業ディレクトリ、git 判定、状態の記録に同じ値を使う。

## 前提の確認

このスキルの受け渡し経路は herdr のペインに限る。delegate-to-codex と同じ理由で、別経路へ退避しない。

```bash
test "${HERDR_ENV:-}" = 1
```

この判定が偽なら、引き継ぎ文書もペインも作らず、「`HERDR_ENV` が `1` ではないため、herdr のペイン内で実行してほしい」とユーザーへ伝えて終了する。

`--multiplexer` の値が `herdr` でない場合も、同様に実行せず、未実装の経路であることをユーザーへ伝えて終了する。

## 手順

### 1. 引き継ぎ文書を書き出す

まず `cwd`、作業説明、worktree の有無、現在のリポジトリ状態を確定する。現在のブランチを変更するコマンドは実行しない。

worktree の判定は次の順序で行う。

1. `--no-worktree` が指定されていれば、`--worktree` を付けない。
2. `--worktree` が指定されていれば、`--worktree` を付ける。
3. どちらも指定されていなければ、`git -C <cwd> rev-parse --git-dir` が成功したときだけ `--worktree` を付ける。

作業説明が指定されていればその内容を、指定されていなければ現行セッションの直近の作業を、確認できた範囲で短い kebab-case の slug にする。確認できない対象を slug に推測で含めず、英数字の識別子が得られない場合は `undetermined` を使う。

UTC の `YYYYMMDDTHHMMSSZ` を取得し、次の出力先を組み立てる。

```text
~/.claude/handoffs/<UTC の YYYYMMDDTHHMMSSZ>-<作業を表す kebab-case の slug>.md
```

出力先はリポジトリの外へ置く。worktree を使っても同じパスで参照でき、リポジトリの作業ツリーを汚さないためである。ディレクトリが無ければ Bash で作る。

```bash
mkdir -p ~/.claude/handoffs
```

文書は必ず Write ツールで指定した出力先へ書く。Bash のリダイレクト、ヒアドキュメント、直接のコマンド埋め込みで文書を作らない。delegate-to-codex の手順 2 と同じく、文書中のバックティックをシェル経由で欠落させないためである。

文書は次の見出しをすべて持つ出力契約とする。埋められない欄は削らず、`未確定` と書く。

```markdown
## 1. 目的（何を達成しようとしているか）

- 目的: 未確定

## 2. 確定済みの決定（ユーザーが承認した設計・方針。根拠つきで）

- 決定: 未確定
  - 根拠: 未確定

## 3. 現在の状態（リポジトリのパス・ブランチ・変更済みファイル・関連する issue / PR・起動中のエージェントやペイン）

- リポジトリのパス: 未確定
- ブランチ: 未確定
- 変更済みファイル: 未確定
- 関連する issue / PR: 未確定
- 起動中のエージェントやペイン: 未確定

## 4. 残作業（着手可能な単位に分けて）

- 残作業: 未確定

## 5. 検収条件（何が満たされたら完了か）

- 条件: 未確定

## 6. 触ってはいけない範囲

- 範囲: 未確定

## 7. 参照パス（読むべきファイル・スキル・文書の絶対パス）

- パス: 未確定

## 8. 継続する workflow

- workflow: `/dev-workflow <承認済み計画のパス> --effort low|mid|high`、または `plan から`（承認済みの計画が無い場合）
```

上の `未確定` を、現行セッションで確認できた情報に置き換える。確認できない欄の `未確定` は残す。

「確定済みの決定」には、ユーザーが承認した設計・方針だけを書く。各決定の根拠は、現行会話のユーザー指示、コードベースの参照、公式ドキュメント URL、issue / PR / 仕様書のいずれかにする。

「現在の状態」は、書き出す直前に確認した事実だけで埋める。リポジトリのパス、ブランチ、変更済みファイルは `git -C <cwd>` の結果を使い、関連する issue / PR と起動中のエージェントやペインは現行セッションで確認済みの情報だけを書く。確認していない状態を、依頼文やブランチ名から推測しない。

「継続する workflow」は、残作業にユーザーが承認した計画（`dispatch/references/implement-loop.md`「入力の形」の形式）があれば `/dev-workflow <計画のパス> --effort low|mid|high` とし、effort は品質をどの軸で評価・改善するかを会話から判断して確定する。承認済みの計画が無ければ `plan から` とし、引き継ぎ先の主スレッドが `plan` で計画を作ってユーザーの承認を得るところから始める（dev-workflow は計画の無い依頼を受け付けない）。判断できなければ、引き継ぎ先へ送る前に AskUserQuestion で確認する。

### 2. ペインを用意する

`cwd` が省略された場合は、次のコマンドをそのまま実行する。

```bash
herdr pane split --current --direction right --cwd "$PWD" --no-focus
```

`--cwd` が指定された場合は、`"$PWD"` の位置へ指定された `cwd` を渡す。分割コマンドの出力から新しい `pane_id` を記録する。

分割直後のペインがまだシェルプロンプトに達していない場合がある。その状態で `agent start` が `agent_pane_busy` または `is not an available shell` で失敗したら、pane split をやり直さず、同じ `pane_id` に対して 2 秒ほど空けて数回まで `agent start` を再試行する。

### 3. claude を起動する

agent name は `handoff-session-<UTC の YYYYMMDDTHHMMSSZ>` として記録する。worktree を使う場合は次を実行する。

```bash
herdr agent start <名前> --kind claude --pane <pane_id> --timeout 60000 \
  -- --permission-mode <mode> --worktree
```

worktree を使わない場合は `--worktree` を省く。

`--` より後ろは claude のネイティブ引数である。`--mode` の値は `--permission-mode` の直後へそのまま渡す。`--worktree` は git リポジトリの判定が成功した場合、またはユーザーが明示した場合だけ渡す。claude の `--permission-mode` には `auto` があり、`-w, --worktree` は git worktree を作る引数であることを `claude --help` で確認済みである。

起動後、発注前に必ず画面を確認する。

```bash
herdr agent read <名前> --source visible
```

信頼確認や更新プロンプトが表示された場合、選択肢を読んでから意図する番号を `herdr pane send-text` で送り、その後に `herdr pane send-keys <pane_id> enter` を送る。選択肢が会話から確定できない場合は AskUserQuestion で確認する。更新プロンプトではユーザー環境を更新しない選択肢を選ぶ。

**素の `enter` を単独で送らない。** 選択肢の入力として意図しない更新や信頼確認を実行させないためである。選択肢を処理した後、画面を再読し、選択肢への入力待ちでないことを確認してから発注へ進む。

### 4. 引き継ぎ作業を渡す

送信用の本文を、文書の絶対パスを埋め込んだ別の Markdown ファイルへ Write ツールで書く。本文は次の 3 点を含める。

```text
引き継ぎ文書 <引き継ぎ文書の絶対パス> を読んでください。
読んだうえで、引き継ぎ文書で指定された workflow を使って残作業を継続してください。
引き継ぎ文書に書かれていない前提を推測で補わないでください。
```

送信用の本文も Bash のリダイレクト、ヒアドキュメント、直接のコマンド埋め込みで作らない。Write 後、次の形で渡す。

```bash
herdr agent prompt <名前> "$(cat <送る本文のパス>)"
```

`--wait` は付けない。引き継ぎ先は対話セッションであり、完了を待つ対象ではない。prompt が成功した時点で受け渡し済みとし、現行セッションは残作業を続けない。

### 5. 報告して終わる

受け渡しが成功したら、ユーザーへ次を報告する。

- 引き継ぎ文書の絶対パス
- エージェント名
- `pane_id`
- ペイン起動時に渡した `--permission-mode <mode>`、`--worktree` の有無、`--cwd <cwd>`
- worktree を使ったかどうかと、その根拠（明示指定、または `git -C <cwd> rev-parse --git-dir` の成否）

受け渡し後に現行セッションで残作業、検収、PR 作成を行わない。同じ作業を 2 つのセッションで並走させない。

## 責務の境界

このスキルが担うのは、引き継ぎ文書の作成、新しい herdr ペインでの claude 起動、引き継ぎ本文の受け渡しまでである。残作業の計画は引き継ぎ先の主スレッドと `plan`、実行・検収は `/dev-workflow` の責務であり（PR 作成は含まない）、ここでは行わない。

別モデルへの委任は `delegate-to-codex` の領分である。このスキルは claude の新しい対話セッションへ引き継ぐときだけ使う。

## 適用範囲外

- 同じ Claude Code セッションで作業を続ける依頼
- 残作業そのものの実装・修正・検収・PR 作成
- herdr 以外のマルチプレクサを使う依頼
- herdr のペイン外での実行
