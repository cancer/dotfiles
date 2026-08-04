import type { Middleware } from "./auth";

let counter = 0;

export const requestId: Middleware = async (ctx, next) => {
  counter += 1;
  ctx.set("x-request-id", `req-${counter}`);
  await next();
};
