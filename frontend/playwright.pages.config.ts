import { defineConfig } from "@playwright/test";
import shared from "./playwright.config";

const basePath =
  process.env.NEXT_PUBLIC_BASE_PATH ?? "/f1-engineering-dashboard";
export default defineConfig(shared, {
  testMatch: ["pages.spec.ts", "dashboard.spec.ts"],
  use: {
    ...shared.use,
    baseURL: `http://127.0.0.1:4173${basePath}/`,
  },
  webServer: {
    command: `python3 ../scripts/serve_pages.py --port 4173 --base-path=${basePath}`,
    url: `http://127.0.0.1:4173${basePath}/`,
    reuseExistingServer: false,
    timeout: 60000,
  },
});
