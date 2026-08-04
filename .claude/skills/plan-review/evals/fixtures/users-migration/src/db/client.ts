export async function query<T>(sql: string, params: unknown[] = []): Promise<T[]> {
  throw new Error(`not implemented (sql=${sql}, params=${params.length})`);
}
