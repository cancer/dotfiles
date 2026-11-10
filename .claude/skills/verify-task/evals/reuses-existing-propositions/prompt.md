---
max_turns: 40
timeout_seconds: 900
---

verify-task スキルを実行して、ワーカーの成果物を検証してください。引数: 指示内容=「src/counter.py の main に --verbose フラグを追加する。--verbose 指定時は `lines: <件数>` の形式で出力し、未指定時の出力は従来どおり件数のみとする。--help の説明文に --verbose を記載する。」 worktree=<REPO> base=main。機械的チェックの結果: pytest pass（3 passed）、lint 未提供、型検査 未提供。これは差し戻し後の2周目の再実行です。
