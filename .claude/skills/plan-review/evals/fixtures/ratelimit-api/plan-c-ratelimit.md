# ログイン API のレート制限 実装計画

## 目的

`POST /auth/login` への総当たり試行を抑える。**同一 IP の失敗が 15 分窓で 10 回に達した時点から、その IP を 15 分間ブロックする**（ブロック開始は 10 回目の失敗時刻。カウント窓の残りとは無関係）。

## 前提（実在を確認したもの）

- ミドルウェアの登録口: `src/middleware/index.ts:7-10`（`compose()` に配列で積む。上から順に実行される）
- ミドルウェアの型: `src/middleware/auth.ts:9`（`(ctx, next) => Promise<void>`）
- 対象経路の正の定義: `src/routes.ts:2-3` の `LOGIN_PATH` / `LOGIN_METHOD`
- 失敗時に立つ状態: `src/middleware/auth.ts:15`（認証情報の欠落）と `:20`（パスワード不一致）。**どちらも `ctx.status = 401`** なので、401 の観測で総当たりを数えられる
- IP の供給元: `src/server.ts:17`（TCP のリモートアドレス）。`X-Forwarded-For` は採用しない方針が `src/server.ts:6` に書かれている。したがって `ctx.request.ip` をキーに使ってよい
- Redis クライアント: `src/lib/redis.ts:16` の `getRedis()`（接続は初回呼び出し時。import 時には張らない）。使えるコマンドは `src/lib/redis.ts:1-10` の `incr` / `setIfAbsent`（`SET … EX … NX` 相当）/ `expire` / `exists` / `ttl` / `del` / `currentDb` / `flushdb`
- 機能フラグの読み出し口: `src/lib/flags.ts:5` の `isEnabled(name)`。**呼び出しごとに `process.env` を読む**ので、テスト内で切り替えられる
- テスト環境: `vitest`（`package.json` の `test` スクリプト）。`vitest.config.ts:6` の `setupFiles` が `test/setup.ts` を読み、そこで `REDIS_DB=15` を設定している（`test/setup.ts:2`）。既存テストの書き方は `src/middleware/auth.test.ts` に倣う

## キー設計

窓とブロックを別のキーに分ける。単一キーだと TTL がカウント窓の残りになり、「10 回目からの 15 分」を表現できない。

| キー | 役割 | 生成 | TTL |
|---|---|---|---|
| `login_fail:<ip>` | 15 分窓の失敗回数 | 失敗時に `incr`。戻り値が 1 なら `expire(key, 900)` | 900 秒（初回失敗から） |
| `login_block:<ip>` | ブロック中であることの印 | 上の `incr` の戻り値が 10 以上になった時点で `setIfAbsent(key, "1", 900)` | 900 秒（10 回目の失敗から） |

`Retry-After` は `login_block:<ip>` の `ttl` から取る。`ttl` が負値（キー無しは -2、TTL 未設定は -1）の場合は 900 を返す。

## 手順

### 1. 失敗するテストを先に書く

`src/middleware/rateLimit.test.ts` を作る。以下 7 件を書き、**実装前に失敗することを確認する**。

- 失敗 9 回では通す
- 失敗 10 回目でブロックし 429 と `Retry-After` を返す
- ブロック中は、正しいパスワードでも 429 を返す（`auth` に届かない）
- `login_block:<ip>` を `del` した後は再び通す（ブロック解除の再現）
- 対象外の経路（`GET /health`）の 401 は `login_fail:<ip>` を増やさない
- `isEnabled("login_rate_limit")` が false のときは、カウントもブロックもしない
- `incr` が reject するとき（Redis 障害）は通す（フェイルオープン）

テストの足回り:

- 各テストの前に、接続先 DB が 15 であることを `getRedis().currentDb()` で確認し、**15 以外なら例外を投げて中断してから** `flushdb` する（`test/setup.ts:2` の設定が効いていない状態で開発 DB を消さないため）
- 時間の経過は `ttl` の書き換えでは再現できない（`src/lib/redis.ts:7` の `ttl` は読み取り専用）。ブロック解除は `del` で再現する
- フラグは各テスト内で `process.env.FEATURE_FLAGS` を設定して切り替える（`src/lib/flags.ts:1-3` が呼び出しごとに読むため有効）
- Redis 障害は、`getRedis` の戻り値の `incr` をテスト内で reject に差し替えて再現する

**完了の定義**: 上記 7 件が「実装が無いため失敗」で赤くなること。

### 2. ミドルウェアを実装する

`src/middleware/rateLimit.ts` に `rateLimit: Middleware` を追加する。

- 対象経路の判定は `ctx.request.path === LOGIN_PATH && ctx.request.method === LOGIN_METHOD`（`src/routes.ts:2-3` を import する。文字列リテラルを再定義しない）。対象外なら即 `next()`
- `isEnabled("login_rate_limit")` が false なら即 `next()`
- `exists("login_block:<ip>")` が真なら `429` と `Retry-After` を返し、`next()` を呼ばない
- そうでなければ `next()` を呼び、戻ってきた時点で `ctx.status === 401` なら「キー設計」の表どおりにカウントとブロックを更新する
- **Redis の呼び出しは try/catch で囲み、例外時は通す（フェイルオープン）**。認証そのものを止めないため。捕捉した例外は `console.error` に出す
- `incr` と `expire` は別呼び出しなので、`expire` が失敗すると TTL 無しのキーが残る。これを避けるため、`incr` の戻り値が 1 のときの `expire` が失敗した場合はキーを `del` して次回の失敗でやり直させる

**完了の定義**: 手順 1 の 7 件が緑になること。既存の `src/middleware/auth.test.ts` が引き続き緑であること。

### 3. 登録する

`src/middleware/index.ts:7-10` の配列に `rateLimit` を `auth` の**前**に積む。順序が逆だと認証処理が先に走り、ブロック中でもパスワード照合のコストを払う。

**完了の定義**: `src/middleware/index.test.ts` を新設し、`compose()` へ渡す配列の順序が `requestId` → `rateLimit` → `auth` であることを検証する 1 件が緑になること。合成済みの `stack` は定数（`src/middleware/index.ts:7`）で差し替えられないため、配列自体を export して検証対象にする。

### 4. フラグを有効化する

`FEATURE_FLAGS` に `login_rate_limit` を追加してデプロイする。手順 2 でフラグ判定を実装済みなので、この手順まではコードが積まれても挙動は変わらない。

**完了の定義**: フラグ追加前後で、ログインの成功経路のレスポンスが変わらないこと（ステージングで確認）。

## ロールバック

`FEATURE_FLAGS` から `login_rate_limit` を外せば、デプロイを戻さずに無効化できる。残った `login_fail:*` / `login_block:*` は TTL 900 秒で消える。`expire` の失敗でキーが残った場合の手当ては手順 2 に入れている。

## 未解決（実装前に確認したいこと）

- ブロック対象を IP 単体にするか、IP + メールアドレスの組にするか。NAT 配下の共有 IP で無関係な利用者が巻き込まれる。まず IP 単体で出し、巻き込みの報告が出たら組に変える方針で進めてよいか
- 閾値 10 回 / 15 分の値は既存の運用記録から取っていない。仮の値である。確定できるまでは、この値を 1 箇所の定数に置いて後から変えられる形にする
- 429 の発生件数・ブロック中の IP 数を可観測にする必要があるか。閾値が仮の値である以上、調整には観測が要るはずだが、既存にメトリクスの出し先が無いため本計画には含めていない
- 429 のレスポンスボディの形式。既存は `{ error: "invalid_credentials" }`（`src/middleware/auth.ts:16`）なので `{ error: "too_many_requests" }` に揃える想定でよいか
