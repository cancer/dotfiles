---
name: verify-task
description: ワーカーの成果物が指示どおり完了しているかを検証する。完了チェックに特化し、品質レビューはしない。サブエージェントの作業を受け取った場面で使う。原則ベースの品質レビューは code-review の領分
argument-hint: <指示内容> <worktreeパスまたはブランチ名> [issue参照] [base]
model: sonnet
allowed-tools: Bash, Read, Glob, Grep
user-invocable: false
---

ワーカーの成果物が指示通りにできているかの検証を行う。品質レビューではなく、指示の完了チェックに特化。

## 引数
$ARGUMENTS

引数から以下を特定する：
- **指示内容**: ワーカーに何を依頼したか
- **worktreeパスまたはブランチ名**: ワーカーの作業場所
- **issue参照**（任意）: GitHub issueのURL、`owner/repo#番号`、または `#番号`
- **base**（任意）: 比較基準のコミットまたはブランチ。省略時は `git merge-base <デフォルトブランチ> HEAD`

**このスキルはどのモデルで実行するかを判断しない。** 実行エンジンと推論量の選択は呼び出し側の責務である（`dev-workflow` は `delegate-to-codex` 経由でこのスキルを Codex に実行させる）。ここに書くのは検証の手順だけとする。

## 検証の3軸

検収は「指示した命題が満たされているか」だけでは足りない。差分は指示の範囲内であっても、命題が触れていない挙動を変え、その挙動を守っていた検証を書き換えることがある。したがって次の3軸で見る。

1. **指示突合**: 指示・issue の命題が満たされているか。差分が指示の範囲に収まっているか
2. **挙動の保存**: 命題が触れていない既存の挙動が変わっていないか
3. **検証の保存**: 変更前に保証されていた命題が、いまも同等以上の強さで検証されているか。削除・置換された実装が保証していた命題（移送された命題）も対象に含む

2 と 3 は判断ではなく**列挙して突合する**。列挙の出所は `git diff` と grep であり、対象は差分から確定する。

**列挙の完全性は、列挙した本人には確かめられない。** 見落としが無いことを示す手段が無いため、網羅を主張しない。導出できなかった箇所は、その箇所を名指しして書く。

**base が一度もカバーしていなかった範囲は、このスキルでは扱えない。** 列挙しても網羅を保証できないので、判定の材料にしない（テストの不足は `test-review` と `test-analyze` の領分）。

**機械的チェック（lint / 型検査 / テスト実行）はこのスキルの範囲外である。** 判定が機械的に決まる検査は呼び出し側が自分で実行し、生の出力を依頼文で渡す（`dev-workflow` の Phase 4「機械的チェック」）。ここで再実行しない。渡された結果を読んでレポートに反映する。

## 検証プロンプト

下記の指示に沿って検証を完了させ、最終レポートを日本語で出力する。

```
You are responsible for verifying whether a worker's output fully matches the requested task.

Input:
- Raw arguments: $ARGUMENTS
- Instruction content: extract from the raw arguments
- Worktree path or branch name: extract from the raw arguments
- Issue reference: extract if provided, otherwise none
- Base commit: extract if provided, otherwise none

Complete this task in a single execution. Do not ask the user for confirmation.
Write the final user-facing report in Japanese.

Requirements:
- Parse the raw arguments first and determine the normalized input values before taking action.
- Determine the base explicitly before any comparison. If the caller supplied a base, use it. Otherwise use `git merge-base <default branch> HEAD`. Do not assume `HEAD~..HEAD`; a worktree branch often has multiple commits. Report the base you used. Every comparison below is against that base.
- If an issue reference is provided, fetch the issue and inspect both the body and comments for additional requirements, clarifications, or scope changes.
- Inspect the worker changes in the specified worktree path or branch.
- Use git diff against the base to understand what was actually changed.
- Enumerate the propositions the instruction (and the issue, if provided) requires. Everything below is judged against that list.

Axis 1 - Instruction match:
- Verify whether all requested changes were implemented.
- Verify whether the diff stays within the requested scope (no unrelated files, features, or refactors). This axis is about the *scope of the diff*, not about behavior.
- Verify whether the implementation matches the intended meaning of the instruction, not just superficial keywords.
- If an issue is provided, treat the issue as the source of truth and verify the changes against the issue requirements as well.

Axis 2 - Behavior preservation:
- A change inside the requested scope can still alter behavior no proposition covers. Axis 1 does not catch this, because the change itself was requested.
- Enumerate every input domain where the observable output differs between base and HEAD. Each of the following creates such a domain: added or removed early returns and guards; a changed range or timing of input reading; a changed point at which a response is finalized; changed dependencies invoked or their call order; changed routing or error responses; changed default values, constants, thresholds or branch conditions; changed signatures and argument counts; deleted functions and their call sites.
- For each domain, classify it as covered by an instruction/issue proposition, or not covered. State the evidence for the classification.
- Any domain that is not covered by a proposition is a FAIL candidate. Report it with the concrete inputs and the before/after outputs, not as a general remark.
- The worker's own claim that behavior is unchanged (a "what I did not change" section in the PR body or report) is not evidence. Confirm each such claim against the diff. A refactor described as behavior-preserving is exactly where this axis pays off.
- Completeness of this enumeration cannot be verified from the inside, so do not claim it. Name the parts of the diff whose affected domains you could not derive, and report them as such. A FAIL on this axis requires a named domain, its concrete inputs, and its before/after outputs.

Axis 3 - Verification preservation:
- Enumerate ALL test changes against the base: `git diff <base>..HEAD -- <test paths>`. Classify each one as added / deleted / test file removed / moved to another test level (unit to integration, or the reverse) / expected value rewritten / input or setup changed / assertion replaced or removed / skipped or ignored.
- Also enumerate changes that shrink what is measured rather than what is asserted: coverage-exclusion pragmas added (`v8 ignore`, `istanbul ignore`, `c8 ignore` and equivalents), coverage thresholds lowered or omitted for a new suite, and test runner include/exclude changes. Each of these is a reduction of verification and belongs in this list.
- For every deleted, moved, rewritten, replaced, skipped, or excluded item, produce three things: the proposition the original asserted, where that proposition is verified now, and a strength comparison against the original.
- Compare strength on: covered input domain, boundary and edge cases, number of cases, tolerance, direction of inequality, specificity of the assertion, and whether the collaborator is a stand-in or the real thing.
- Treat these as weakening: a specific assertion replaced by a general one; a relative relation replaced by a single absolute value; exact comparison replaced by a looser predicate; boundary or edge cases dropped; case count reduced; tolerance widened; the real dependency replaced by a stand-in; skip/ignore or a coverage exclusion added. A stand-in replaced by the real dependency is strengthening, and the reverse is not.
- When tests are moved between levels, do not accept the count. Match the propositions one by one. A reduction from N cases to M is only acceptable if every one of the N propositions has a named counterpart at the destination. Report the pairs, not the totals.
- Changing a test's inputs or setup removes the previous input domain from coverage. If the removed domain is where behavior changed, treat it as a FAIL candidate: a test rewritten so it no longer enters the changed region hides that change instead of verifying it.
- Rewriting an expected value redefines the proposition being asserted. Require the reason to be traceable to the instruction or the issue. If it is not traceable, it is a FAIL candidate.
- A maintained coverage threshold, a green suite, or the worker's statement that every removed proposition "has been confirmed to have a counterpart" is not evidence. Name the counterpart yourself for each item.
- No counterpart, or a weaker counterpart, is a FAIL candidate. Do not PASS unless every enumerated item is accounted for.
- Report the counts alongside the list: the number of changed test files from `git diff <base>..HEAD --stat -- <test paths>`, the number of test cases you classified, and the number of deleted or replaced units you examined. The caller reconciles these against the same commands, so a list shorter than its count is visible rather than silent.
- Enumerate a second source as well: every function, branch, or module deleted or replaced between base and HEAD. Test diffs alone miss these, because the deletion itself was requested and its tests may not appear as deletions at all.
- For each deleted or replaced unit, list the propositions it guaranteed at base - taken from its own tests, its doc comments, and the assertions or expectations at its call sites.
- For each such proposition, state where it is guaranteed now, which test verifies it, and the strength comparison on the same dimensions above.
- A proposition with no counterpart, or one whose only remaining verification is a trivial case (identity input, zero input, a single happy path), is a FAIL candidate. Replacing several specific propositions with one general test is weakening.
- Judging whether the tests that remain are themselves adequate (empty assertions, mock-heavy tests, test strategy, duplication between levels) is out of scope here; that belongs to test-review. This axis only asks whether verification that existed at the base was lost.

Constraints:
- Do not modify files.
- Do not fix problems.
- Do not run lint, typecheck, or the test suite. Those are run by the caller and their raw output is supplied in the request. Read that output and reflect it in your report; if it was not supplied, record it as not supplied instead of running it yourself, and do not read a missing result as a pass.
- Produce only a verification report.

Use these commands as needed:
- gh issue view <number> --repo <owner/repo> --json number,title,body,labels,comments
- git merge-base <default branch> HEAD
- git diff <base>..HEAD
- git diff <base>..HEAD --stat
- git diff <base>..HEAD -- <test paths>
- git status
- git branch --show-current

Output format:

## 検証結果

### issueとの突合
(記載可能な場合のみ)
- issue: <owner/repo#番号> <issueタイトル>
- [ ] issueの要件がすべて満たされている
- [ ] 指示内容とissueの間に齟齬がない

### 機械的チェックの結果（呼び出し側が実行）
- <check or lint command>: pass / fail / 未提供
- <typecheck command>: pass / fail / 未提供
- <test command>: pass / fail / 未提供

### 指示突合
- 命題一覧: <指示・issueから抽出した命題>
- [ ] 指示された変更がすべて実施されている
- [ ] 差分が指示の範囲に収まっている
- [ ] 指示の意図と異なる実装になっていない

### 挙動の保存
- base: <使用したコミット/ブランチとその決め方>
- 挙動が変わる入力域（全件）:
  - <入力域>: 命題内 / 命題外 — <変更前の出力> → <変更後の出力> — <根拠>
- ワーカーが「変えていない」と主張した挙動: <主張> — 差分での確認結果
- [ ] 命題外の入力域で挙動が変わっていない
- [ ] 差分の全体について入力域を列挙できた
- [ ] 「変えていない」という主張を差分で確認した

### 検証の保存
- テスト差分（全件）:
  - <テスト名>: 追加 / 削除 / ファイル削除 / レベル移送 / 期待値の書き換え / 入力・セットアップの変更 / アサーションの置換 / skip — 元の命題: <命題> — 現在の検証箇所: <場所または「なし」> — 強さ: 同等以上 / 弱化（<理由>）
  - 移送された命題: <元の所在（削除・置換された関数/分岐）> — 元の命題: <命題> — 現在の所在: <実装の場所> — 検証箇所: <テストまたは「なし」> — 強さ: 同等以上 / 弱化（<理由>）
  - 計測範囲の変更（全件）: <カバレッジ除外プラグマ / 閾値 / include・exclude> — 除外された対象: <対象> — 命題内 / 命題外
- [ ] 削除・置換された関数/分岐の命題を全件列挙し、移送先の検証と突合できた
- [ ] 削除・移送・書き換え・置換・skip の全件に対応する検証がある（件数ではなく命題ごとに対応づけた）
- [ ] 対応する検証が同等以上の強さである
- [ ] 期待値の書き換えの根拠が指示またはissueに辿れる
- [ ] 計測範囲の縮小（除外プラグマ・閾値・include/exclude）が指示の命題内である

### 判定
PASS / FAIL（理由）

PASS は、次の2つを満たす場合とする。

- 列挙した入力域に、命題外の挙動変化が無い
- 失われた検証に、同等以上の強さの対応が付いている

**列挙を導出できなかった箇所は FAIL の理由にしない。** 成果物の欠陥ではなく、検証の届かない範囲である。判定とは別に、その箇所を名指しして書く。

対応の付かない項目、根拠を示せない項目があれば FAIL とし、何が説明できなかったのかを書く。

At the start of the report, include the normalized values used for instruction content, worktree path or branch name, issue reference, and base.
```

## 実行方針

- **1回の実行で検証を完了させる**こと
- 検証ループや複数回の呼び出しは禁止

## 注意

- 現在の作業ディレクトリや対象worktreeで検証可能な範囲を前提とする
- ファイルの修正や問題の修正は行わない。検証レポートのみを出力する
- **`test-review` との境界**: このスキルが見るのは base 比較で**失われた検証**（削除・緩和・回避されたテスト）である。いま存在するテストそのものの妥当性（空検証・モック偏重・テスト戦略）は `test-review` の領分
