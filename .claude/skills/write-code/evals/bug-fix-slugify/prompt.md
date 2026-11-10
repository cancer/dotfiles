---
tags: [write-code]
max_turns: 40
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

src/slugify.js の slugify に不具合があります。"Hello,  World!!" が "hello--world-" になってしまいます。期待値は "hello-world"（連続する区切りは1つのハイフンにまとめ、先頭と末尾のハイフンは除く）。修正してください。

Input files: package.json, src/slugify.js
