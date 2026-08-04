import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    include: ["src/**/*.test.ts"],
    setupFiles: ["test/setup.ts"],
    // Redis を共有するため、テストファイル間の並行実行はしない
    fileParallelism: false,
  },
});
