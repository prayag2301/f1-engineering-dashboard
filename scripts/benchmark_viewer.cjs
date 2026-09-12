const { chromium } = require("../frontend/node_modules/playwright");
const path = require("node:path");
const fs = require("fs");
(async () => {
  const root = path.resolve(__dirname, "..");
  const base = process.env.E2E_BASE_URL || "http://127.0.0.1:3000";
  const team = process.env.TEAM || "mercedes";
  const output = path.resolve(
    process.env.BENCHMARK_OUTPUT || path.join(root, "data/releases/benchmark"),
  );
  fs.mkdirSync(output, { recursive: true });
  const token = fs
    .readFileSync(root + "/.env", "utf8")
    .split("\n")
    .find((l) => l.startsWith("ADMIN_TOKEN="))
    .slice(12);
  const browser = await chromium.launch({
    executablePath:
      process.env.PLAYWRIGHT_CHROME_PATH ||
      "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    headless: false,
    args: [
      "--use-angle=metal",
      "--enable-webgl",
      "--ignore-gpu-blocklist",
      "--window-position=-2000,-2000",
      "--disable-backgrounding-occluded-windows",
      "--disable-renderer-backgrounding",
      "--disable-background-timer-throttling",
    ],
  });
  const context = await browser.newContext({
    viewport: { width: 1920, height: 1080 },
    deviceScaleFactor: 1,
  });
  const page = await context.newPage();
  await context.request.post(base + "/api/v1/review/session", {
    headers: { "X-F1-Review": "1" },
    data: { token },
  });
  const dashboard = await (
    await context.request.get(base + "/api/v1/review/dashboard")
  ).json();
  const version =
    dashboard.versions.find(
      (v) => v.team_key === team && v.status === "ready",
    ) ||
    dashboard.versions.find(
      (v) => v.team_key === team && v.status !== "failed",
    );
  if (!version) throw new Error("No car configuration available for " + team);
  version.is_current = false;
  if (process.env.E2E_GLB_PATH) {
    version.manifest.assets = {
      ...version.manifest.assets,
      glb: { url: "/test-assets/native.glb" },
    };
    await page.route("**/test-assets/native.glb", (r) =>
      r.fulfill({
        contentType: "model/gltf-binary",
        body: fs.readFileSync(process.env.E2E_GLB_PATH),
      }),
    );
  }
  if (!version.manifest.assets.glb)
    throw new Error(
      "Wait for the draft build, or set E2E_GLB_PATH to its exported GLB.",
    );
  // Read-only browser preview. This does not change a record or publish a draft.
  await page.route("**/api/v1/cars/" + team + "/versions?*", (r) =>
    r.fulfill({ json: [version] }),
  );
  await page.goto(base + "/car/" + team);
  await page.locator(".stage-caption").waitFor({ timeout: 45000 });
  await page.evaluate(() => {
    const notice = document.createElement("div");
    notice.textContent = "LOCAL DRAFT PREVIEW · NOT PUBLISHED";
    Object.assign(notice.style, {
      padding: "12px",
      textAlign: "center",
      background: "#24332d",
      color: "#bde8d5",
    });
    document.body.prepend(notice);
  });
  await page.screenshot({
    path: path.join(output, "viewer.png"),
    fullPage: true,
  });
  await page
    .locator(".car-stage")
    .evaluate((el) =>
      Object.assign(el.style, {
        position: "fixed",
        left: "0",
        top: "0",
        width: "1920px",
        height: "1080px",
        zIndex: "9999",
      }),
    );
  await page.waitForTimeout(1500);
  await page.mouse.move(960, 540);
  await page.mouse.down();
  const result = await page.evaluate(async () => {
    const canvas = document.querySelector("canvas");
    const gl = canvas.getContext("webgl2");
    const debug = gl.getExtension("WEBGL_debug_renderer_info");
    const started = performance.now();
    const first = Number(canvas.dataset.renderFrame || 0);
    let ticks = 0;
    await new Promise((resolve) => {
      function tick() {
        const elapsed = performance.now() - started;
        canvas.dispatchEvent(
          new PointerEvent("pointermove", {
            pointerId: 1,
            pointerType: "mouse",
            buttons: 1,
            clientX: 960 + Math.sin(elapsed / 1200) * 480,
            clientY: 540 + Math.sin(elapsed / 1800) * 90,
            bubbles: true,
          }),
        );
        ticks++;
        if (elapsed < 8000) requestAnimationFrame(tick);
        else resolve();
      }
      requestAnimationFrame(tick);
    });
    const elapsed = (performance.now() - started) / 1000;
    const frames = Number(canvas.dataset.renderFrame || 0) - first;
    return {
      renderer: gl.getParameter(debug.UNMASKED_RENDERER_WEBGL),
      drawingBuffer: [gl.drawingBufferWidth, gl.drawingBufferHeight],
      frames,
      seconds: elapsed,
      fps: frames / elapsed,
      animationTicks: ticks,
    };
  });
  await page.mouse.up();
  result.team = team;
  result.version_id = version.id;
  fs.writeFileSync(
    path.join(output, "performance.json"),
    JSON.stringify(result, null, 2),
  );
  console.log(JSON.stringify(result));
  await browser.close();
})().catch((e) => {
  console.error(e.message);
  process.exit(1);
});
