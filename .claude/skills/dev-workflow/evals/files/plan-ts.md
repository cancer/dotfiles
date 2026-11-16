# 計画: src/age.ts に canVote を追加する

## Context
- TypeScript 7 / Vitest 5 / Node 24 のライブラリ。投票可否の判定を足す（owner/repo#31）

## タスク

### T1: canVote の追加
- 対象: src/age.ts, test/age.test.ts
- 完了条件:
  - p1_can_vote: `canVote(age: number, citizen: boolean): boolean` が、citizen が false なら false、true なら age が 18 以上で true を返す
- 契約: 提供 なし / 利用 なし

## 契約

なし

## 検証方法
- `npx vitest run`
- `npx tsc --noEmit`
