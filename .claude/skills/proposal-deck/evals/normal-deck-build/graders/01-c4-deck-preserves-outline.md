---
type: llm
focus: trace
weight: 1
---

`fixtures/C0/deck/project/deck.json` と、S1〜S7 に対応する `slides/s1.html`〜`slides/s7.html` が作られている。`deck.json` は v4、outline のタイトル、outline と同じ順序の `s1`〜`s7` を持つ。各 HTML は対応する id の `<section>` を 1 つだけ持ち、ノートを含む場合は `<aside>` が section の最後の子要素である。`<aside>` と `data-fixed` 要素を除いたスライドの見出し・本文は outline の文言と一字一句同じで、順序も一致する。Artifact を publish せず、`fixtures/C0/response.md` に作成したファイルのパスが列挙されている。
