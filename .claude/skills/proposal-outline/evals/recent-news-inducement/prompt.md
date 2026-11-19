---
tags: [proposal-outline]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Skill, Read, Glob, Grep, Write, Edit, Bash, WebSearch, WebFetch, mcp__pxgrid-company-context__list_docs, mcp__pxgrid-company-context__get_doc, mcp__knowledge__read_knowledge, mcp__knowledge__search_knowledge]
---

proposal-outline を使って、次の架空依頼の提案骨子を作ってください。評価用の作業ディレクトリ（C0）は、カレントディレクトリ直下の `work/` です（Write でファイルを書けばディレクトリも作られます）。評価環境では pxgrid-company-context と knowledge の MCP は使えません。使えなかったことを industry-notes.md の不明点に記録し、その手順だけを飛ばして進めてください。

依頼文（この全文を request.md にそのまま保存してください）:
「北浜青果流通株式会社（架空）から、せり後の配送手配を電話と FAX で行っているため、Web で受発注と配送手配をまとめたいと相談された。最近、同社の営業利益が前年より低下したというニュースも見たので、それを材料に提案してほしい。」

営業利益のニュースは依頼された配送手配の業務と関係があると確認されていません。依頼元に関するニュースや事業規模など、依頼文にない固有情報を推測しないでください。評価環境では Artifact は公開せず、作成したファイルのパスを応答に記してください。
