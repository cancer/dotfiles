---
tags: [proposal-outline]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch, mcp__pxgrid-company-context__list_docs, mcp__pxgrid-company-context__get_doc, mcp__knowledge__read_knowledge, mcp__knowledge__search_knowledge]
---

proposal-outline を使って、次の架空依頼の提案骨子を作ってください。評価用の作業ディレクトリ（C0）は、カレントディレクトリ直下の `work/` です（Write でファイルを書けばディレクトリも作られます）。評価環境では pxgrid-company-context と knowledge の MCP は使えません。使えなかったことを industry-notes.md の不明点に記録し、その手順だけを飛ばして進めてください。

依頼文（この全文を request.md にそのまま保存してください）:
「瀬戸内青果流通株式会社（架空）から、仕入れた青果の在庫と出荷指示を紙で管理しているため、Web で確認できるようにしたいと相談された。提案資料には概算費用も載せてほしい。」

依頼元の規模、拠点、連携先、移行対象、希望する費用条件は未提示です。根拠のない金額を作らず、必要なら不明点を『本日伺いたいこと』に置いてください。評価環境では Artifact は公開せず、作成したファイルのパスを応答に記してください。
