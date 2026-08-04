export type ActivateResult = { ok: boolean; sessionId: string };
export type StatusResult = { state: "idle" | "running"; sessionId: string | null };

export type ControlServerDeps = {
  activate: (sessionId: string) => Promise<ActivateResult>;
  deactivate: (sessionId: string) => Promise<void>;
  status: () => Promise<StatusResult>;
};

export type ControlRequest = {
  method: string;
  path: string;
  body: unknown;
};

export type ControlResponse = {
  status: number;
  body: unknown;
};

// 依存はすべて引数で注入される。ここでの処理は method / path / body から
// status / body を導く値の変換であり、I/O は持たない。
export function createControlServer(deps: ControlServerDeps) {
  return async function handle(req: ControlRequest): Promise<ControlResponse> {
    if (req.method !== "POST" && req.method !== "GET") {
      return { status: 405, body: { error: "method_not_allowed" } };
    }

    if (req.method === "GET" && req.path === "/status") {
      const result = await deps.status();
      return { status: 200, body: result };
    }

    if (req.method === "POST" && req.path === "/activate") {
      const sessionId = readSessionId(req.body);
      if (sessionId === null) {
        return { status: 400, body: { error: "session_id_required" } };
      }
      const result = await deps.activate(sessionId);
      if (!result.ok) {
        return { status: 409, body: { error: "already_active" } };
      }
      return { status: 201, body: { sessionId: result.sessionId } };
    }

    if (req.method === "POST" && req.path === "/deactivate") {
      const sessionId = readSessionId(req.body);
      if (sessionId === null) {
        return { status: 400, body: { error: "session_id_required" } };
      }
      await deps.deactivate(sessionId);
      return { status: 204, body: null };
    }

    return { status: 404, body: { error: "not_found" } };
  };
}

function readSessionId(body: unknown): string | null {
  if (typeof body !== "object" || body === null) return null;
  const value = (body as Record<string, unknown>).sessionId;
  return typeof value === "string" && value.length > 0 ? value : null;
}
