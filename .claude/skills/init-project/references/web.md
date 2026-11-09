# Web（vite）系統

## 骨組み

```bash
npm create vite@latest <name> -- --template vanilla-ts
cd <name> && npm i
```

## 差分

```bash
npm i -D vitest @vitest/coverage-v8 oxlint oxfmt knip
npm pkg set \
  scripts.lint="oxlint" \
  scripts.lint:fix="oxlint --fix" \
  scripts.format="oxfmt" \
  scripts.format:check="oxfmt --check" \
  scripts.typecheck="tsc --noEmit" \
  scripts.knip="knip" \
  scripts.test="vitest run" \
  scripts.coverage="vitest run --coverage --coverage.provider=v8 --coverage.include=src/** --coverage.reporter=json --coverage.reporter=text --coverage.thresholds.lines=90 --coverage.thresholds.statements=90 --coverage.thresholds.functions=90 --coverage.thresholds.branches=90"
```

`tsconfig.json` は vite の生成物を使う（上書きしない）。

```bash
[ -e .gitignore ]     || cp <skill>/assets/gitignore-node .gitignore
[ -e .oxlintrc.json ] || cp <skill>/assets/oxlintrc.json .oxlintrc.json
[ -e .oxfmtrc.json ]  || cp <skill>/assets/oxfmtrc.json  .oxfmtrc.json
mkdir -p .github/workflows && [ -e .github/workflows/quality.yml ] || cp <skill>/assets/ci-node.yml .github/workflows/quality.yml
```

## 実装コードの除去と placeholder

vite の `vanilla-ts` テンプレートは `src/main.ts`（読み込み時に `document.querySelector` を実行する）と `src/counter.ts` を吐く。これらを削除する。

削除する効果はカバレッジにも及ぶ。DOM を触る実装が残っていると、閾値 90 を満たすために jsdom 等の DOM 環境を追加することになるが、実装を消せばその必要が無い。

```bash
rm -f src/main.ts src/counter.ts src/style.css src/vite-env.d.ts
```

`tsconfig.json`（vite の生成物）の `include` は `["src"]` で `test/` を拾わないため、placeholder テストは **`src/` 配下に置く**。`test/` に置くと型検査の入力が 0 件になり `error TS18003` で落ちる（実測で確認した）。

`src/placeholder.test.ts`:

```ts
import { expect, test } from "vitest";

// 足場のテスト。最初の実装で差し替える。
test("placeholder", () => {
  expect(true).toBe(true);
});
```

`index.html` は `<script type="module" src="/src/main.ts">` を持つので、`src/main.ts` を消すと `npm run dev` が壊れる。中身だけを空にした置き場として残す。

```ts
export {};
```

**空ファイルにしてはいけない。** oxlint の `unicorn(no-empty-file)` が `Empty files are not allowed` で lint を落とす（実測で確認した）。`export {};` の1行なら lint・型検査・カバレッジのすべてを通る。

## knip

設定ファイルは要らない。`index.html` から参照される `src/main.ts` と、既定の entry パターンで拾われる placeholder テストが entry になるため、この状態で exit 0 になる（実測で確認した）。

`oxlint` / `oxfmt` は knip のプラグインを持たないため、**npm script に登録されていることだけが使用済みの根拠**になる。スクリプト登録前に走らせると `Unused devDependencies` で落ちる（実測で確認した）。

## 検査（すべて exit 0 であること）

CLAUDE.md を先に書いてから（oxfmt は Markdown も整形するため）、format を1回走らせ、検査は**1件ずつ**実行して都度 `$?` を見る。

```bash
npm run format
npm run lint;         echo "lint=$?"
npm run format:check; echo "format:check=$?"
npm run typecheck;    echo "typecheck=$?"
npm run knip;         echo "knip=$?"
npm test;             echo "test=$?"
npm run coverage;     echo "coverage=$?"
```
