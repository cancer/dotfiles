// テストは専用の Redis DB を使う。開発用の DB 0 を flushdb しないための唯一の設定口。
process.env.REDIS_DB = "15";
process.env.REDIS_URL = process.env.REDIS_URL ?? "redis://127.0.0.1:6379";
process.env.FEATURE_FLAGS = "";
