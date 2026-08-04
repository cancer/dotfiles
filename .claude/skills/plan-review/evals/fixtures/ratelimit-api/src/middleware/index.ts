import type { Middleware } from "./auth";
import { auth } from "./auth";
import { requestId } from "./requestId";
import { compose } from "./compose";

// アプリに積むミドルウェア。配列の上から順に実行される
export const stack = compose([
  requestId,
  auth,
]);

export { compose };
export type { Middleware };
