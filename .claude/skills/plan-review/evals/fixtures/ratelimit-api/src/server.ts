import { stack } from "./middleware";
import type { Ctx } from "./middleware/auth";

/**
 * ctx.request.ip は TCP のリモートアドレスから作る。
 * X-Forwarded-For は信用しない（このサービスはプロキシの後段に置かない）。
 */
export function buildCtx(raw: {
  remoteAddress: string;
  path: string;
  method: string;
  body: unknown;
}): Ctx {
  const headers = new Map<string, string>();
  return {
    request: {
      ip: raw.remoteAddress,
      path: raw.path,
      method: raw.method,
      body: raw.body,
    },
    status: 200,
    body: null,
    set(header, value) {
      headers.set(header.toLowerCase(), value);
    },
  };
}

export async function handle(raw: Parameters<typeof buildCtx>[0]): Promise<Ctx> {
  const ctx = buildCtx(raw);
  await stack(ctx, async () => {});
  return ctx;
}
