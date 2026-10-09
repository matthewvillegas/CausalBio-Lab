import { defineConfig, devices } from "@playwright/test";

const pythonExecutable =
  process.env.CAUSALBIO_PYTHON ??
  (process.platform === "win32" ? "../../.venv/Scripts/python.exe" : "../../.venv/bin/python");

export default defineConfig({
  testDir: "./e2e",
  testMatch: "**/*.e2e.ts",
  timeout: 60_000,
  expect: { timeout: 15_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? [["line"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://127.0.0.1:3000",
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  webServer: [
    {
      command: `"${pythonExecutable}" -m uvicorn causalbio_api.main:app --host 127.0.0.1 --port 8000`,
      url: "http://127.0.0.1:8000/api/v1/health",
      reuseExistingServer: !process.env.CI,
      timeout: 60_000,
      env: {
        CAUSALBIO_WEB_ORIGIN: "http://127.0.0.1:3000",
        CAUSALBIO_ARTIFACT_DIR: "../../artifacts",
      },
    },
    {
      command:
        process.env.CAUSALBIO_E2E_PRODUCTION !== "0"
          ? "pnpm start --hostname 127.0.0.1"
          : "pnpm dev --hostname 127.0.0.1",
      url: "http://127.0.0.1:3000",
      reuseExistingServer: !process.env.CI,
      timeout: 90_000,
      env: {
        NEXT_PUBLIC_API_URL: "http://127.0.0.1:8000",
        NEXT_TELEMETRY_DISABLED: "1",
      },
    },
  ],
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
