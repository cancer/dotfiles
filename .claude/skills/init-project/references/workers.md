# Workers 系統

C3 の生成物は**テスト構成まで含んでいる**ので、足すものは少ない。ただし後述の3点（`test` スクリプトが watch モード、`typecheck` が無い、v8 provider が動かない）は放置すると検査項目が緑にならない。以下は C3 v2.72.3 / `--type=hello-world --lang=ts` の実物で確認した内容である。

## 骨組み

```bash
npm create cloudflare@latest <name> -- --type=hello-world --lang=ts \
  --no-deploy --no-git --no-agents --no-open -y
```

各フラグの理由:

- `--no-git`: `git init` と最初のコミットは手順5でこちらが行う
- `--no-agents`: AGENTS.md を作らせない。Cloudflare API の手引きは `~/.claude/skills/cloudflare/` にあり、CLAUDE.md も置くので指示ファイルが三重になる
- `--no-open` と `-y`（`--accept-defaults`）: **これが無いと対話待ちで止まる**（AGENTS.md の確認プロンプトが出る）

フレームワーク付きの Web（Astro / SvelteKit 等）もこの系統で扱う: `--type=web-app --framework=<name> --ts`。選択肢の決定木は `~/.claude/skills/cloudflare/references/c3/configuration.md` にある。

## C3 が既に用意するもの（触らない）

| ファイル / 設定 | 内容 |
|---|---|
| `test/index.spec.ts` | hello-world 用のテスト（インラインスナップショット付き） |
| `vitest.config.mts` | `@cloudflare/vitest-plugin` の `cloudflareTest()` を通した設定 |
| `test/tsconfig.json` | テスト側の型設定（ルートの tsconfig とは別） |
| `tsconfig.json` | `include` は `["worker-configuration.d.ts", "src/**/*.ts"]`、**`exclude` は `["test"]`** |
| `.gitignore` | 用意されている。上書きしない |
| `.editorconfig` | `indent_style = tab` を宣言する。oxfmt はこれを読まないので実害は無いが、方針は食い違っている |
| `.vscode/settings.json` | `wrangler.json` の関連付けのみ |
| devDependencies | `vitest` / `@cloudflare/vitest-plugin` / `typescript` / `wrangler` / `@types/node` |

**ルートの型検査はテストを含まない**（`exclude: ["test"]`）。`npm run typecheck` が緑でも、テストコードの型は検査されていない。テスト側を検査するには別途 `npx tsc --noEmit -p test/tsconfig.json` を実行する（exit 0 を実測で確認済み）。この事実は CLAUDE.md に書く。

テスト用の依存は **`@cloudflare/vitest-plugin`** である（`@cloudflare/vitest-pool-workers` ではない）。既にあるので追加しない。

## 差分

```bash
cd <name>
npm i -D oxlint oxfmt @vitest/coverage-istanbul knip
```

**カバレッジは istanbul provider を使う。** `@vitest/coverage-v8` は Workers ランタイムでは動かない——`Error: The Session method is not implemented`（workerd に `node:inspector` の Session が無い）で落ち、テスト自体が実行されない（`Test Files no tests`）。istanbul は変換時に計測コードを埋め込む方式なので inspector に依存せず、`coverage/coverage-final.json` を出せる（実測で確認）。この JSON は `test-review --coverage-json` がそのまま受け付ける形式である。

```bash
npm pkg set \
  scripts.lint="oxlint" \
  scripts.lint:fix="oxlint --fix" \
  scripts.format="oxfmt" \
  scripts.format:check="oxfmt --check" \
  scripts.typecheck="tsc --noEmit" \
  scripts.knip="knip" \
  scripts.test="vitest run" \
  scripts.coverage="vitest run --coverage --coverage.provider=istanbul --coverage.include=src/** --coverage.reporter=json --coverage.reporter=text --coverage.thresholds.lines=90 --coverage.thresholds.statements=90 --coverage.thresholds.functions=90 --coverage.thresholds.branches=90"
```

`test` の上書きは**必須**である。C3 の既定は `vitest`（watch モード）なので、そのままだと CI で終了せずタイムアウトする。`typecheck` は C3 が用意しないので追加する。

```bash
rm -f .prettierrc   # prettier は依存に無く、oxfmt と設定が衝突するだけの死んだ設定
[ -e .oxlintrc.json ] || cp <skill>/assets/oxlintrc.json .oxlintrc.json
[ -e .oxfmtrc.json ]  || cp <skill>/assets/oxfmtrc.json  .oxfmtrc.json
[ -e knip.json ]      || cp <skill>/assets/knip-workers.json knip.json
mkdir -p .github/workflows && [ -e .github/workflows/quality.yml ] || cp <skill>/assets/ci-node.yml .github/workflows/quality.yml
```

`.gitignore` は C3 のものを使う（他系統では `assets/gitignore-node` を置くが、ここでは不要）。

## 実装コードの除去と placeholder

`wrangler.jsonc` の `main` が指すエントリは必須なので、最小のエントリを残して placeholder テストで覆う。C3 の `test/index.spec.ts` は `"Hello World!"` のインラインスナップショットを持つため、エントリを書き換えるなら**同じファイルを置き換える**（残すとスナップショット不一致で落ちる）。

`src/index.ts`:

```ts
export default {
  fetch(): Response {
    return new Response("ok");
  },
} satisfies ExportedHandler<Env>;
```

`test/index.spec.ts`:

```ts
import { SELF } from "cloudflare:test";
import { expect, test } from "vitest";

// 足場のテスト。最初の実装で差し替える。
test("responds", async () => {
  const res = await SELF.fetch("https://example.com/");
  expect(res.status).toBe(200);
});
```

ルートの `tsconfig.json` の `include` は `src/**/*.ts` なので、エントリが残っている限り型検査の入力は 0 件にならない。

## knip

**この系統だけ `knip.json` が要る。** 理由は2つあり、どちらも C3 の生成物に由来する。

1. `vitest.config.mts` が `test` キーを持たないため、knip の Vitest プラグインがテストファイルの entry を導出できない。`knip --debug` で、この設定から得られた entry が `src/vite-env.d.ts` だけであることを確認した。その結果 `test/index.spec.ts` が `Unused files` として報告され exit 1 になる
2. テストの `import { SELF } from "cloudflare:test"` が、未宣言の依存 `cloudflare` として `Unlisted dependencies` に報告される

`assets/knip-workers.json` は前者を `vitest.entry` の明示で、後者を `ignoreDependencies` で吸収する。この設定を置いた状態で exit 0 になり、`src/` に未使用ファイルを1つ置くと exit 1 になることを実測で確認した。

`test` スクリプトが watch モードであっても knip の判定は変わらないが、`oxlint` / `oxfmt` は knip のプラグインを持たないため、スクリプト登録より後に knip を実行する（登録前は `Unused devDependencies` で落ちる）。

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

`npm run format` は C3 の生成物 3 ファイル（`tsconfig.json` / `wrangler.jsonc` / `worker-configuration.d.ts`）をタブからスペースへ書き換える。「生成物を正とする」方針は**設定の内容を消さない**ことを指しており、整形の差は内容を変えないので受け入れる（矛盾しているように読めるので、CLAUDE.md に記録する）。

**`npm run cf-typegen` を実行した後は `format:check` が落ちる。** `wrangler types` が `worker-configuration.d.ts` をタブで再生成するためで、`npm run format` を続けて走らせれば戻る。これは以後も毎回起きるので、CLAUDE.md に書き残す。

## デプロイ

```bash
npx wrangler whoami   # 認証状態の確認（未認証でも次へ進んでよい）
npx wrangler deploy
```

失敗しても停止しない。理由を報告して続行する。Worker を1回作っておくのは、Workers Builds の trigger が既存の Worker に紐づくためである。
