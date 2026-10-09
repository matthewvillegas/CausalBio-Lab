import { existsSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";

const workspace = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const defaultInterpreter =
  process.platform === "win32"
    ? join(workspace, ".venv", "Scripts", "python.exe")
    : join(workspace, ".venv", "bin", "python");
const interpreter = process.env.CAUSALBIO_PYTHON || defaultInterpreter;

if (!process.env.CAUSALBIO_PYTHON && !existsSync(interpreter)) {
  console.error(`Python environment not found at ${interpreter}. Create .venv first.`);
  process.exit(1);
}

const result = spawnSync(interpreter, process.argv.slice(2), {
  cwd: workspace,
  stdio: "inherit",
  env: process.env,
});

if (result.error) {
  console.error(result.error.message);
  process.exit(1);
}
process.exit(result.status ?? 1);
