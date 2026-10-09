import { spawnSync } from "node:child_process";
import { copyFile, lstat, mkdir, mkdtemp, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { dirname, isAbsolute, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const workspace = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const listed = spawnSync("git", ["ls-files", "-z", "--cached", "--others", "--exclude-standard"], {
  cwd: workspace,
  encoding: "utf8",
});
if (listed.error || listed.status !== 0) {
  throw new Error("Run this script from a Git checkout; it copies the current public file candidates.");
}
const files = [...new Set(listed.stdout.split("\0").filter(Boolean))].sort();
const destination = await mkdtemp(join(tmpdir(), "causalbio-release-"));

for (const file of files) {
  const parts = file.replaceAll("\\", "/").split("/");
  if (
    isAbsolute(file) ||
    parts.includes("..") ||
    parts.some((part) => [".git", ".venv", "node_modules", ".next"].includes(part)) ||
    (parts.includes("artifacts") && file !== "artifacts/.gitkeep") ||
    parts.some((part) => part.startsWith(".env") && part !== ".env.example") ||
    /\.(?:sqlite3?|db)(?:-(?:shm|wal|journal))?$/i.test(file)
  ) {
    // Git can include tracked ignored files; fail instead of copying private local state.
    throw new Error(`Refusing a local-only publication candidate: ${file}`);
  }
  const source = resolve(workspace, file);
  const target = resolve(destination, file);
  if (relative(destination, target).startsWith(`..${sep}`) || !(await lstat(source)).isFile()) {
    throw new Error(`Expected a regular public source file: ${file}`);
  }
  await mkdir(dirname(target), { recursive: true });
  await copyFile(source, target);
}

await mkdir(join(destination, "artifacts"), { recursive: true });
await writeFile(join(destination, "artifacts", "public-file-manifest.json"), `${JSON.stringify(files, null, 2)}\n`);
await mkdir(join(workspace, "artifacts"), { recursive: true });
await writeFile(join(workspace, "artifacts", "public-file-manifest.json"), `${JSON.stringify(files, null, 2)}\n`);
console.log(`Copied ${files.length} publication candidates into a fresh source directory.`);
console.log(destination);
console.log("No dependencies, virtual environment, private configuration, databases, or build outputs were copied.");
