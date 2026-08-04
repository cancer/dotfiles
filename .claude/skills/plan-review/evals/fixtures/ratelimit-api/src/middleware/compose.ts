import type { Middleware } from "./auth";

export function compose(middlewares: Middleware[]): Middleware {
  return async (ctx, next) => {
    let called = -1;
    const dispatch = async (n: number): Promise<void> => {
      if (n <= called) throw new Error("next() called multiple times");
      called = n;
      const fn = middlewares[n];
      if (!fn) return next();
      await fn(ctx, () => dispatch(n + 1));
    };
    await dispatch(0);
  };
}
