---
name: proposal-review
description: 提案資料をレビューしてほしいときに使う（例:「提案資料をレビューして」「この骨子を確認して」）。コードの品質確認は code-review、仕様書の完全性確認は spec-review を使う。
---

# proposal-review

商談前の提案骨子またはスライドをレビューし、C5 形式の指摘一覧のみを返す。レビュー対象は修正しない。

## 入力と出力

- `--target outline` は C0 の `outline.md`、`--target deck` は C0 の `deck/` を対象にする。
- Jev には C0 の `request.md`、`industry-notes.md` の「確認済み事実」節、対象文書だけを渡す。
- 出力は C5 JSON とし、指摘の有無にかかわらず `review.py` の終了コード 0 を成功とする。
- Jev または入力に失敗した場合は、終了コードが 0 以外になり、標準エラーに理由が出る。呼び出し側で結果を推測せず、その理由を報告する。

## 実行

```bash
python3 ~/.claude/skills/proposal-review/scripts/review.py \
  --workdir <C0> \
  --target outline \
  --round <n> \
  --out <C0>/review/<target>-round-<n>.json
```

`PROPOSAL_JUDGE_SCRIPT` を設定すると Jev スクリプトを差し替えられる。機械判定は `check_rules.py`、意味判定と読者評価は `judge_review.py` が行う。ルールと語彙は `scripts/rules.json`、Jev の質問は `scripts/catalog.json`、合格閾値は `scripts/thresholds.json` にある。

指摘の根拠となった観測済みの失敗は [references/observed-failures.md](references/observed-failures.md) に記録している。
