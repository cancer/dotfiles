---
tags: [write-code]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

src/duration.js に parseDuration(str) を実装してください。仕様: "1h30m" のような文字列を秒数で返す。単位は h・m・s で、各単位は省略可能だが順序は h→m→s 固定。空文字列・未知の単位・順序違反・数値の無い単位（"h"）は RangeError を投げる。"0s" は 0。

Input files: package.json
