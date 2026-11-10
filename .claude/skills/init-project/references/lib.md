# ライブラリ / CLI / MCP サーバ 系統

骨組みを生成する scaffolder は使わない。この用途で必要なのは `package.json` と `tsconfig.json` と `src/` だけで、vite テンプレートを通すと `index.html` / `public/` / `vite.config.ts` という使わない資産が必ず付く。

## 骨組みと差分

```bash
mkdir -p <name> && cd <name>
npm init -y
npm pkg set type=module name=<name>
npm pkg set private=true --json
npm pkg delete main
npm i -D typescript vitest @vitest/coverage-v8 oxlint oxfmt knip
npm pkg set \
  scripts.lint="oxlint" \
  scripts.lint:fix="oxlint --fix" \
  scripts.format="oxfmt" \
  scripts.format:check="oxfmt --check" \
  scripts.typecheck="tsc --noEmit" \
  scripts.knip="knip" \
  scripts.test="vitest run" \
  scripts.coverage="vitest run --coverage --coverage.provider=v8 --coverage.include=src/** --coverage.reporter=json --coverage.reporter=text --coverage.thresholds.lines=90 --coverage.thresholds.statements=90 --coverage.thresholds.functions=90 --coverage.thresholds.branches=90"
cp <skill>/assets/tsconfig.lib.json tsconfig.json
cp <skill>/assets/gitignore-node .gitignore
cp <skill>/assets/oxlintrc.json .oxlintrc.json
cp <skill>/assets/oxfmtrc.json .oxfmtrc.json
mkdir -p .github/workflows src test && cp <skill>/assets/ci-node.yml .github/workflows/quality.yml
```

`tsconfig.json` に `target` と `lib` を書かない理由は、tsc の既定値が常にその版の最新（現行の TypeScript 7 では `es2025`）であり、書いた値はその時点で古くなるためである。実行環境（workerd / Node の LTS）は tsc の既定に追いついている。

`module` / `moduleResolution` は実行形態で決まる。この系統はバンドラを通さず Node が直接解決するため `NodeNext` を使う。

`npm pkg set` の注意点が2つある。**`--json` はコマンド全体の値を JSON.parse するフラグなので、`type=module` と同じ呼び出しに混ぜると `Unexpected token 'm', "module" is not valid JSON` で落ちる**（実測で確認した）。真偽値だけを別の呼び出しに分ける。もうひとつ、`npm init -y` は `main: "index.js"` を書くが `src/` は空で実体が無いため、消しておく（エントリポイントは最初の実装時に決まる）。

**ランタイム依存は入れない。** この系統は MCP サーバの用途を含むが、`@modelcontextprotocol/sdk` のような実装用の依存は足さない。使うコードが1行も無い時点でバージョンと peer 依存を固定することになるうえ、このスキルが足すのは評価環境の差分だけである。最初の実装時に入れる旨を CLAUDE.md に書く。

## placeholder

`test/placeholder.test.ts`:

```ts
import { expect, test } from "vitest";

// 足場のテスト。最初の実装で差し替える。
test("placeholder", () => {
  expect(true).toBe(true);
});
```

`src/` は空のままにする。テストが1本あれば `tsc --noEmit` は `include` からテストを拾うので TS18003 にはならない。

## knip

設定ファイルは要らない。vitest の設定ファイルが無いので knip の Vitest プラグインが既定の entry パターン（`**/*.{test,spec}.*`）を使い、placeholder テストを entry として拾う。`src/` が空でも `Unused files` は出ない（実測で確認した）。

`oxlint` / `oxfmt` は knip のプラグインを持たないため、**npm script に登録されていることだけが使用済みの根拠**になる。スクリプト登録前に走らせると `Unused devDependencies` で落ちる（実測で確認した）。

## 検査（すべて exit 0 であること）

先に formatter を1回走らせる（`npm pkg set` が書き戻した `package.json` の整形が oxfmt と一致しないため、省くと `format:check` が落ちる）。`.gitignore` を置いていないと oxlint が `node_modules/` を走査して落ちる。

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
