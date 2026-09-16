import { spawnSync } from "node:child_process";
import { writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const python = process.env.PYTHON || "python3";
function run(command, args, cwd, env = process.env) {
  const result = spawnSync(command, args, { cwd, env, stdio: "inherit" });
  if (result.error) throw result.error;
  if (result.status !== 0) process.exit(result.status || 1);
}
const args = ["scripts/pages.py", "prepare"];
if (process.env.PAGES_ARCHIVE) args.push("--bundle", path.resolve(process.env.PAGES_ARCHIVE));
run(python, args, root);
const env = {
  ...process.env,
  NEXT_PUBLIC_STATIC_ARCHIVE: "true",
  NEXT_PUBLIC_BASE_PATH: process.env.NEXT_PUBLIC_BASE_PATH ?? "/f1-engineering-dashboard",
};
run(process.execPath, ["node_modules/next/dist/bin/next", "build"], path.join(root, "frontend"), env);
run(python, ["scripts/pages.py", "validate", "frontend/out/archive"], root);
writeFileSync(path.join(root, "frontend/out/.nojekyll"), "");
writeFileSync(path.join(root, "frontend/out/deployment.json"), JSON.stringify({
  commit: process.env.GITHUB_SHA || "local-preview",
  repository: process.env.GITHUB_REPOSITORY || "prayag2301/f1-engineering-dashboard",
  base_path: env.NEXT_PUBLIC_BASE_PATH,
  built_at: new Date().toISOString(),
}, null, 2) + "\n");
