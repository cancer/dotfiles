import { verifyPassword } from "../lib/passwords";

export type Ctx = {
  request: { ip: string; path: string; method: string; body: unknown };
  status: number;
  body: unknown;
  set(header: string, value: string): void;
};
export type Middleware = (ctx: Ctx, next: () => Promise<void>) => Promise<void>;

/** 認証情報の欠落・不一致はいずれも 401 を立てる */
export const auth: Middleware = async (ctx, next) => {
  const creds = ctx.request.body as { email?: string; password?: string } | null;
  if (!creds?.email || !creds.password) {
    ctx.status = 401;
    ctx.body = { error: "invalid_credentials" };
    return;
  }
  if (!(await verifyPassword(creds.email, creds.password))) {
    ctx.status = 401;
    ctx.body = { error: "invalid_credentials" };
    return;
  }
  await next();
};
