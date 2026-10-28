---
tags: [article-writer]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Write, Edit, Bash, Agent, Skill]
---

技術ブログ向けの記事を最後まで書いて、draft.md に保存して。記事に必要な前提は下にまとめた。確認したい点があれば、下の情報を私の回答として扱い、選んだ解釈を記録して進めて。

トピック: Svelte 5 で writable store を $state のクラスに置き換えた話
対象読者: Svelte 4 の store を使ったことがある中級者
狙う効果: 複数コンポーネントで共有する状態を store で持っている読者が、Svelte 5 移行時に store をそのまま残すのではなく $state を持つクラスへの置き換えを検討する
結論: コンポーネント間で共有する可変状態は、store の subscribe/update より、$state フィールドを持つクラスのインスタンスを context で配る方が、型推論と更新の追跡が単純になる
却下した代替案: (a) store をそのまま残し $ プレフィックスで読む → 動くが、派生値のたびに derived を作る必要があり、型が Readable<T> に包まれて補完が効きにくい。(b) モジュールスコープの $state を直接 export する → 再代入できず、テストごとに状態を初期化できない
読者に要求する前提: Svelte 4 の writable/derived、コンポーネントの props と context は知っている。runes（$state/$derived）は名前を聞いた程度
文字数: 4000 字程度
