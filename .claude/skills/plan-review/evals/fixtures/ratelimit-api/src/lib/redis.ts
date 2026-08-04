export type RedisLike = {
  incr(key: string): Promise<number>;
  /** SET key value EX <seconds> NX。既に在ればセットせず false */
  setIfAbsent(key: string, value: string, seconds: number): Promise<boolean>;
  expire(key: string, seconds: number): Promise<number>;
  exists(key: string): Promise<boolean>;
  ttl(key: string): Promise<number>;
  del(key: string): Promise<number>;
  currentDb(): number;
  flushdb(): Promise<void>;
};

let client: RedisLike | null = null;

/** 接続は最初の呼び出し時に張る（import 時には張らない） */
export function getRedis(): RedisLike {
  client ??= createClient({
    url: process.env.REDIS_URL ?? "redis://127.0.0.1:6379",
    db: Number(process.env.REDIS_DB ?? "0"),
  });
  return client;
}

function createClient(_opts: { url: string; db: number }): RedisLike {
  throw new Error("not implemented in fixture");
}
