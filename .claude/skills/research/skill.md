---
name: research
description: 調べ物をする際に使用。Web検索と技術ドキュメント検索を適切に使い分ける
allowed-tools: mcp__context7__resolve-library-id, mcp__context7__query-docs, Bash
user-invocable: false
---

# 調べ物スキル

調べ物をする際は、情報源を適切に選択すること。

## 情報源の優先順位

### 1. 専用MCPドキュメントツール（最優先）
特定の技術・サービスに関する質問は、利用可能なMCPドキュメント検索ツールを優先使用する。

### 2. Context7
専用ツールがない技術・ライブラリについては、Context7でドキュメントを検索する：
1. `mcp__context7__resolve-library-id` でライブラリIDを特定
2. `mcp__context7__query-docs` でドキュメントを取得

### 3. Web検索（gemini-cli）
上記でカバーされない一般的な調べ物には、Bashで `gemini` コマンドを直接実行する：
```bash
echo "検索クエリや質問" | gemini -m gemini-2.5-flash
```

## 注意事項
- 複数の情報源を組み合わせて調査する場合は並列実行を活用
