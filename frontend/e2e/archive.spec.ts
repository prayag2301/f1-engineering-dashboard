import { test, expect, type Page } from "@playwright/test";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { pixel, fixtureGLB } from "./fixtures";

test.beforeEach(async ({ page }) => {
  page.on("pageerror", (error) => console.log("BROWSER ERROR:", error.message));
});
async function archiveFixture(page: Page) {
  const cat = await (await page.request.get("/api/v1/cars/catalog")).json();
  function version(team: string, index: number) {
    const id = `fixture-${team}-${index}`;
    const components = Object.fromEntries(
      Object.entries(cat.components).map(([key, c]: [string, any]) => [
        key,
        {
          revision_id: key + (key === "front_wing" ? index : 0),
          label: c.label,
          anchor: c.anchor,
          source_ids: [],
          parameters: {},
          uncertainty: "Explicit synthetic browser-test fixture.",
          changed: key === "front_wing" && index === 2,
        },
      ]),
    );
    const assets: any = { glb: { url: `/test-assets/${id}.glb` } };
    for (const view of ["front", "side", "rear", "three_quarter"])
      for (const prefix of ["preview_", "render_"])
        assets[prefix + view] = {
          url: `/test-assets/${id}-${prefix}${view}.png`,
        };
    return {
      id,
      team_key: team,
      season: 2026,
      label: `Fixture ${index}`,
      configuration_event: "Synthetic browser test",
      configuration_kind: "evolution",
      as_of: `2026-03-0${index}T12:00:00Z`,
      evidence_cutoff: "2026-03-03T12:00:00Z",
      status: "published",
      parent_id: index === 2 ? `fixture-${team}-1` : null,
      is_current: index === 2,
      notes: "Test only",
      component_revisions: {},
      visual_review: {},
      manifest: {
        components,
        sources: [],
        changes: [],
        component_hashes: Object.fromEntries(
          Object.keys(components).map((c) => [
            c,
            c + (c === "front_wing" ? index : 0),
          ]),
        ),
        assets,
        no_new_modeled_change: false,
      },
    };
  }
  await page.route("**/api/v1/cars/*/versions?*", async (route) => {
    const team = route.request().url().includes("/mercedes/")
      ? "mercedes"
      : "ferrari";
    await route.fulfill({ json: [version(team, 2), version(team, 1)] });
  });
  await page.route("**/test-assets/**", (route) =>
    route.fulfill({
      contentType: route.request().url().endsWith(".glb")
        ? "model/gltf-binary"
        : "image/png",
      body: route.request().url().endsWith(".glb") ? fixtureGLB() : pixel,
    }),
  );
  return version;
}

test("private constructor comparison uses draft assets and keeps the selected counterpart on refresh", async ({
  page,
}) => {
  const fixture = await archiveFixture(page);
  const ferrari = {
    ...fixture("ferrari", 2),
    status: "ready",
    is_current: false,
  };
  const mercedes = {
    ...fixture("mercedes", 2),
    status: "ready",
    is_current: false,
  };
  let reads = 0;
  await page.route("**/api/v1/review/session", (route) =>
    route.fulfill({ json: { authenticated: true } }),
  );
  await page.route("**/api/v1/review/dashboard", (route) => {
    reads++;
    return route.fulfill({
      json: {
        versions: [ferrari, mercedes, fixture("mercedes", 1)],
        candidates: [],
        jobs: [],
        sources: [],
        audits: [],
      },
    });
  });
  await page.goto("/review");
  await page
    .getByRole("button", { name: "Compare other constructor", exact: true })
    .click();
  await expect(page.locator(".constructor-pane canvas")).toHaveCount(2);
  const stages = page.locator(".constructor-pane .car-stage");
  await expect
    .poll(async () => {
      const first = await stages.first().boundingBox();
      const second = await stages.nth(1).boundingBox();
      return Math.abs((first?.y ?? -1) - (second?.y ?? -2));
    })
    .toBeLessThan(1);
  await expect(page.locator(".constructor-pane").nth(1)).toContainText(
    "Unpublished draft",
  );
  await page
    .getByRole("button", { name: "Neutral surfaces", exact: true })
    .click();
  await expect(page.locator('[data-material-mode="shape"]')).toHaveCount(2);
  await page.getByLabel("Draft camera view").selectOption("side");
  const canvases = page.locator(".constructor-pane canvas");
  await expect(canvases.first()).toHaveAttribute(
    "data-camera-position",
    /8\.0000/,
  );
  await expect
    .poll(
      async () =>
        (await canvases.first().getAttribute("data-camera-position")) ===
        (await canvases.nth(1).getAttribute("data-camera-position")),
    )
    .toBe(true);
  await page
    .getByLabel("Other constructor release")
    .selectOption("fixture-mercedes-1");
  const before = reads;
  await expect.poll(() => reads, { timeout: 15000 }).toBeGreaterThan(before);
  await expect(page.getByLabel("Other constructor release")).toHaveValue(
    "fixture-mercedes-1",
  );
});

test("loads the selected release, selects components, and synchronizes cameras", async ({
  page,
}) => {
  await archiveFixture(page);
  await page.goto("/");
  await expect(page.locator(".loading-pill")).toHaveCount(0, {
    timeout: 30000,
  });
  await page
    .getByLabel("Component", { exact: true })
    .selectOption("front_wing");
  await expect(page.locator(".inspection-panel h2")).toHaveText("Front wing");
  await page
    .getByRole("button", { name: "Compare releases", exact: true })
    .click();
  await expect(page.locator("canvas")).toHaveCount(2);
  await expect(page.locator(".loading-pill")).toHaveCount(0, {
    timeout: 30000,
  });
  await page.getByRole("button", { name: "Side", exact: true }).click();
  const first = page.locator("canvas").first();
  const second = page.locator("canvas").nth(1);
  await expect(first).toHaveAttribute("data-camera-position", /8\.0000/);
  await first.focus();
  await page.keyboard.press("ArrowLeft");
  await expect
    .poll(
      async () =>
        (await first.getAttribute("data-camera-position")) ===
        (await second.getAttribute("data-camera-position")),
    )
    .toBe(true);
  await page.getByRole("button", { name: "Use before / after switch" }).click();
  await expect(second).toBeVisible();
  await expect(first).not.toBeVisible();
  await page
    .getByRole("button", { name: "Showing after · switch to before" })
    .click();
  await expect(first).toBeVisible();
  await expect(second).not.toBeVisible();
});

test("failed GLB shows its release still and retry succeeds", async ({
  page,
}) => {
  await archiveFixture(page);
  let failed = true;
  await page.route("**/test-assets/fixture-ferrari-2.glb", (route) =>
    failed
      ? route.abort("failed")
      : route.fulfill({ contentType: "model/gltf-binary", body: fixtureGLB() }),
  );
  await page.goto("/");
  await expect(page.getByRole("button", { name: "Retry 3D" })).toBeVisible({
    timeout: 30000,
  });
  await expect(page.locator(".car-stage__poster")).toHaveAttribute(
    "src",
    /fixture-ferrari-2/,
  );
  failed = false;
  await page.getByRole("button", { name: "Retry 3D" }).click();
  await expect(page.locator(".stage-caption")).toBeVisible({ timeout: 30000 });
});

test("rapid team switching cannot display the previous team asset", async ({
  page,
}) => {
  await archiveFixture(page);
  await page.goto("/");
  const ferrari = page.getByRole("tab", { name: /Scuderia Ferrari/ });
  const mercedes = page.getByRole("tab", { name: /Mercedes-AMG/ });
  await mercedes.click();
  await ferrari.click();
  await mercedes.click();
  await expect(mercedes).toHaveAttribute("aria-selected", "true");
  await expect(page.locator(".car-stage")).toHaveAttribute(
    "aria-label",
    /^mercedes /,
  );
  await expect(page.locator(".loading-pill")).toHaveCount(0, {
    timeout: 30000,
  });
  await expect(page.locator('.car-stage[aria-label^="ferrari"]')).toHaveCount(
    0,
  );
});

test("mobile layout and keyboard controls remain usable", async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await archiveFixture(page);
  await page.goto("/");
  await page.getByRole("tab", { name: /Mercedes-AMG/ }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator(".car-stage")).toHaveAttribute(
    "aria-label",
    /^mercedes /,
  );
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= window.innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Front", exact: true }).focus();
  await page.keyboard.press("Enter");
  await expect(
    page.getByRole("button", { name: "Front", exact: true }),
  ).toHaveAttribute("aria-pressed", "true");
});

test("maintainer can sign in, inspect drafts, and sign out", async ({
  page,
}) => {
  const token =
    process.env.E2E_ADMIN_TOKEN ||
    readFileSync(resolve(__dirname, "../../.env"), "utf8")
      .split("\n")
      .find((l) => l.startsWith("ADMIN_TOKEN="))
      ?.slice(12);
  test.skip(
    !token,
    "A local review token is needed for this authenticated smoke check.",
  );
  await page.goto("/review");
  await page.getByLabel("Review token").fill(token!);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.locator(".draft-item").first()).toBeVisible();
  await page.getByRole("button", { name: "Sign out", exact: true }).click();
  await expect(
    page.getByRole("button", { name: "Sign in", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".notice.error")).toHaveCount(0);
});
