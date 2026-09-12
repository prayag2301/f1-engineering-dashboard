import { defineConfig } from "@playwright/test";
import { existsSync } from "node:fs";
const macChrome =
  "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const nativeMacGpu =
  process.env.E2E_NATIVE_GPU === "1" && existsSync(macChrome);
export default defineConfig({
  testDir: "./e2e",
  testMatch: "archive.spec.ts",
  // Software WebGL can contend with the CPU Blender worker on a local stack.
  timeout: 120000,
  expect: { timeout: 15000 },
  workers: 1,
  reporter: "list",
  use: {
    headless: !nativeMacGpu,
    baseURL: process.env.E2E_BASE_URL || "http://127.0.0.1:3000",
    viewport: { width: 1440, height: 1000 },
    launchOptions: {
      args: nativeMacGpu
        ? [
            "--use-angle=metal",
            "--enable-webgl",
            "--ignore-gpu-blocklist",
            "--window-position=-2000,-2000",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
          ]
        : [
            "--use-angle=swiftshader",
            "--enable-unsafe-swiftshader",
            "--enable-webgl",
            "--ignore-gpu-blocklist",
          ],
      executablePath:
        process.env.PLAYWRIGHT_CHROME_PATH ||
        (existsSync(macChrome) ? macChrome : undefined),
    },
    screenshot: "only-on-failure",
  },
});
