import { describe, expect, it } from "vitest";
import { auth } from "./auth";
import { buildCtx } from "../server";

const post = (body: unknown) =>
  buildCtx({ remoteAddress: "203.0.113.7", path: "/auth/login", method: "POST", body });

describe("auth", () => {
  it("認証情報が欠けていれば 401 を立て、下流を呼ばない", async () => {
    const ctx = post({ email: "user@example.com" });
    let reached = false;
    await auth(ctx, async () => {
      reached = true;
    });
    expect(ctx.status).toBe(401);
    expect(ctx.body).toEqual({ error: "invalid_credentials" });
    expect(reached).toBe(false);
  });

  it("パスワードが一致しなければ 401 を立てる", async () => {
    const ctx = post({ email: "user@example.com", password: "wrong" });
    await auth(ctx, async () => {});
    expect(ctx.status).toBe(401);
    expect(ctx.body).toEqual({ error: "invalid_credentials" });
  });

  it("一致すれば下流を呼び、401 を立てない", async () => {
    const ctx = post({ email: "user@example.com", password: "hunter2" });
    let reached = false;
    await auth(ctx, async () => {
      reached = true;
    });
    expect(reached).toBe(true);
    expect(ctx.status).toBe(200);
  });
});
