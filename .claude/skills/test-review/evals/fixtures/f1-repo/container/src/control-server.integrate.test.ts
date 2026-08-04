import { createServer } from "node:http";
import type { AddressInfo } from "node:net";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { createControlServer, type ControlServerDeps } from "./control-server";

// このテストは実 server を立てて実 HTTP で叩く。
// 応答タイミングは応答が返るまでの挙動でしか観測できないため、
// モックした transport では意図した検証にならない。
// したがって統合テストとして配置している（ファイル名の .integrate も同じ意図）。

let baseUrl = "";
let close: () => Promise<void> = async () => {};

function deps(overrides: Partial<ControlServerDeps> = {}): ControlServerDeps {
  return {
    activate: async (sessionId) => ({ ok: true, sessionId }),
    deactivate: async () => {},
    status: async () => ({ state: "idle", sessionId: null }),
    ...overrides,
  };
}

async function listen(d: ControlServerDeps) {
  const handle = createControlServer(d);
  const server = createServer((req, res) => {
    const chunks: Buffer[] = [];
    req.on("data", (c) => chunks.push(c));
    req.on("end", async () => {
      const raw = Buffer.concat(chunks).toString("utf8");
      const result = await handle({
        method: req.method ?? "GET",
        path: req.url ?? "/",
        body: raw.length > 0 ? JSON.parse(raw) : null,
      });
      res.statusCode = result.status;
      res.setHeader("content-type", "application/json");
      res.end(result.body === null ? "" : JSON.stringify(result.body));
    });
  });
  await new Promise<void>((resolve) => server.listen(0, "127.0.0.1", resolve));
  const { port } = server.address() as AddressInfo;
  baseUrl = `http://127.0.0.1:${port}`;
  close = () =>
    new Promise<void>((resolve, reject) =>
      server.close((err) => (err ? reject(err) : resolve())),
    );
}

describe("control server over real HTTP", () => {
  beforeEach(async () => {
    await listen(deps());
  });

  afterEach(async () => {
    await close();
  });

  it("returns 200 and the current state for GET /status", async () => {
    const res = await fetch(`${baseUrl}/status`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ state: "idle", sessionId: null });
  });

  it("returns 201 with the session id for POST /activate", async () => {
    const res = await fetch(`${baseUrl}/activate`, {
      method: "POST",
      body: JSON.stringify({ sessionId: "s-1" }),
    });
    expect(res.status).toBe(201);
    expect(await res.json()).toEqual({ sessionId: "s-1" });
  });

  it("returns 400 when POST /activate has no session id", async () => {
    const res = await fetch(`${baseUrl}/activate`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(400);
    expect(await res.json()).toEqual({ error: "session_id_required" });
  });

  it("returns 400 when POST /activate has an empty session id", async () => {
    const res = await fetch(`${baseUrl}/activate`, {
      method: "POST",
      body: JSON.stringify({ sessionId: "" }),
    });
    expect(res.status).toBe(400);
  });

  it("returns 204 for POST /deactivate", async () => {
    const res = await fetch(`${baseUrl}/deactivate`, {
      method: "POST",
      body: JSON.stringify({ sessionId: "s-1" }),
    });
    expect(res.status).toBe(204);
  });

  it("returns 400 when POST /deactivate has no session id", async () => {
    const res = await fetch(`${baseUrl}/deactivate`, {
      method: "POST",
      body: JSON.stringify({}),
    });
    expect(res.status).toBe(400);
  });

  it("returns 404 for an unknown path", async () => {
    const res = await fetch(`${baseUrl}/unknown`);
    expect(res.status).toBe(404);
    expect(await res.json()).toEqual({ error: "not_found" });
  });

  it("returns 405 for DELETE", async () => {
    const res = await fetch(`${baseUrl}/status`, { method: "DELETE" });
    expect(res.status).toBe(405);
  });

  it("returns 409 when activate reports an existing session", async () => {
    await close();
    await listen(deps({ activate: async () => ({ ok: false, sessionId: "s-0" }) }));
    const res = await fetch(`${baseUrl}/activate`, {
      method: "POST",
      body: JSON.stringify({ sessionId: "s-2" }),
    });
    expect(res.status).toBe(409);
    expect(await res.json()).toEqual({ error: "already_active" });
  });

  it("returns 200 and the running state while a session is active", async () => {
    await close();
    await listen(deps({ status: async () => ({ state: "running", sessionId: "s-3" }) }));
    const res = await fetch(`${baseUrl}/status`);
    expect(res.status).toBe(200);
    expect(await res.json()).toEqual({ state: "running", sessionId: "s-3" });
  });
});
