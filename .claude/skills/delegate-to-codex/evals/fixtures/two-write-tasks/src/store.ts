type Record_ = { id: string } & Record<string, unknown>;

function makeStore() {
  const rows = new Map<string, Record_>();
  return {
    async find(id: string) { return rows.get(id) ?? null; },
    async create(data: Record<string, unknown>) {
      const id = String(rows.size + 1);
      const row = { id, ...data };
      rows.set(id, row);
      return row;
    },
  };
}

export const userStore = makeStore();
export const orderStore = makeStore();
