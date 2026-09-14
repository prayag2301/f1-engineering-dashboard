import { test, expect, type Page } from "@playwright/test";
import { createHash } from "node:crypto";
import { fixtureGLB, pixel } from "./fixtures";

const prefix = process.env.NEXT_PUBLIC_BASE_PATH ?? "/f1-engineering-dashboard";
const errors = new WeakMap<Page, string[]>();
test.beforeEach(({ page }) => {
  const problems: string[] = [];
  errors.set(page, problems);
  page.on("pageerror", (error) => problems.push(error.message));
  page.on("request", (request) => {
    if (new URL(request.url()).pathname.includes("/api/"))
      problems.push(request.url());
  });
});
test.afterEach(({ page }) => expect(errors.get(page)).toEqual([]));

test("all public routes load directly under the repository path without an API", async ({
  page,
  request,
}) => {
  for (const route of [
    "",
    "compare/",
    "about/",
    "review/",
    "car/ferrari/",
    "car/mercedes/",
    "car/ferrari/upgrades/",
    "models/",
    "teams/",
    "analyze/",
    "evidence/",
    "performance/",
  ]) {
    const response = await page.goto(`${prefix}/${route}`);
    expect(response?.status()).toBe(200);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    await expect(page.getByLabel("Review token")).toHaveCount(0);
    const links = await page
      .locator('a[href^="/"]')
      .evaluateAll((items) => items.map((a) => a.getAttribute("href")));
    expect(
      links.every((link) => link === prefix || link?.startsWith(prefix + "/")),
    ).toBe(true);
  }
  expect((await request.get(`${prefix}/car/red-bull/`)).status()).toBe(404);
  expect(
    (await request.get(`${prefix}/api/v1/review/dashboard`)).status(),
  ).toBe(404);
  expect((await request.get(`${prefix}/.env`)).status()).toBe(404);
  await page.goto(`${prefix}/about/`);
  await page.getByRole("link", { name: "Explore the archive" }).click();
  await expect(
    page.getByRole("heading", { name: "The car. The changes." }),
  ).toBeVisible();
  await page.reload();
  await expect(
    page.getByRole("tab", { name: /Scuderia Ferrari/ }),
  ).toBeVisible();
  const archive = await (
    await request.get(`${prefix}/archive/index.json`)
  ).json();
  const releaseCount = archive.versions.ferrari.length;
  await expect(page.locator(".timeline-item")).toHaveCount(releaseCount);
  if (releaseCount === 1) {
    await expect(page.locator(".timeline-item.is-only")).toHaveCount(1);
    await expect(page.locator(".timeline-note")).toContainText(
      "First published release",
    );
    await expect(page.locator(".timeline-controls")).toHaveCount(0);
  } else {
    await expect(page.locator(".timeline-controls")).toHaveCount(
      releaseCount > 1 ? 1 : 0,
    );
  }
});

test("the exported snapshot exposes only local published assets with matching checksums", async ({
  request,
}) => {
  const snapshot = await (
    await request.get(`${prefix}/archive/index.json`)
  ).json();
  expect(snapshot.schema_version).toBe(1);
  const checked = new Set<string>();
  for (const team of ["ferrari", "mercedes"]) {
    for (const version of snapshot.versions[team]) {
      expect(version.status).toBe("published");
      expect(version.team_key).toBe(team);
      expect(Object.keys(version.manifest.assets)).toHaveLength(9);
      for (const asset of Object.values(version.manifest.assets) as any[]) {
        expect(asset.url).toMatch(/^assets\/[a-f0-9]{64}\.(png|glb)$/);
        if (checked.has(asset.url)) continue;
        checked.add(asset.url);
        const response = await request.get(`${prefix}/archive/${asset.url}`);
        expect(response.status()).toBe(200);
        const body = await response.body();
        expect(body.length).toBe(asset.bytes);
        expect(createHash("sha256").update(body).digest("hex")).toBe(
          asset.sha256,
        );
      }
    }
  }
});

async function populatedSnapshot(page: Page) {
  const snapshot = await (
    await page.request.get(`${prefix}/archive/index.json`)
  ).json();
  // Explicit synthetic fixtures test populated behavior even before visual approval.
  // They only intercept this browser context; no generated site files are changed.
  for (const team of ["ferrari", "mercedes"]) {
    snapshot.versions[team] = [2, 1].map((index) => {
      const digest = createHash("sha256")
        .update(team + index)
        .digest("hex");
      const components = Object.fromEntries(
        Object.entries(snapshot.catalog.components).map(
          ([key, c]: [string, any]) => [
            key,
            {
              label: c.label,
              anchor: c.anchor,
              revision_id: key + index,
              parameters: {},
              source_ids: [],
              changed: key === "front_wing" && index === 2,
              uncertainty: "Synthetic test geometry.",
            },
          ],
        ),
      );
      const assets: any = { glb: { url: `assets/${digest}.glb` } };
      for (const view of ["front", "side", "rear", "three_quarter"]) {
        for (const kind of ["preview", "render"])
          assets[`${kind}_${view}`] = { url: `assets/${digest}.png` };
      }
      return {
        id: `${team}-${index}`,
        team_key: team,
        season: 2026,
        label: `Synthetic test ${index}`,
        as_of: `2026-03-0${index}T12:00:00Z`,
        evidence_cutoff: "2026-03-03T12:00:00Z",
        status: "published",
        published_at: "2026-03-04T12:00:00Z",
        parent_id: index === 2 ? `${team}-1` : null,
        is_current: index === 2,
        configuration_event: "Browser test fixture",
        configuration_kind: "evolution",
        notes: "Fixture only",
        component_revisions: {},
        visual_review: {},
        manifest: {
          components,
          assets,
          changes: [],
          sources: [],
          no_new_modeled_change: false,
          component_hashes: Object.fromEntries(
            Object.keys(components).map((key) => [
              key,
              key + (key === "front_wing" ? index : 0),
            ]),
          ),
        },
      };
    });
  }
  await page.route(`**${prefix}/archive/index.json`, (route) =>
    route.fulfill({ json: snapshot }),
  );
  await page.route(`**${prefix}/archive/assets/*`, (route) =>
    route.fulfill({
      contentType: route.request().url().endsWith(".glb")
        ? "model/gltf-binary"
        : "image/png",
      body: route.request().url().endsWith(".glb") ? fixtureGLB() : pixel,
    }),
  );
}

test("static releases support selection, synchronized comparison and rapid team switching", async ({
  page,
}) => {
  await populatedSnapshot(page);
  await page.goto(`${prefix}/`);
  await expect(page.locator(".stage-caption")).toBeVisible({ timeout: 45000 });
  await page
    .getByLabel("Component", { exact: true })
    .selectOption("front_wing");
  await expect(page.locator(".inspection-panel h2")).toHaveText("Front wing");
  await page
    .getByRole("button", { name: "Compare releases", exact: true })
    .click();
  await expect(page.locator(".stage-caption")).toHaveCount(2);
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
  await page
    .getByRole("button", { name: "Compare releases", exact: true })
    .click();
  for (const name of [/Mercedes-AMG/, /Scuderia Ferrari/, /Mercedes-AMG/])
    await page.getByRole("tab", { name }).click();
  await expect(page.locator(".car-stage")).toHaveAttribute(
    "aria-label",
    /^mercedes /,
  );
  await expect(page.locator(".stage-caption")).toBeVisible();
  await expect(page.getByRole("link", { name: /Download 4K/ })).toHaveAttribute(
    "href",
    new RegExp(`^${prefix}/archive/assets/`),
  );
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await expect(page.locator(".timeline-controls")).toBeVisible();
  const timeline = page.locator(".timeline-items");
  await page.getByRole("button", { name: "Scroll to later releases" }).click();
  await expect
    .poll(() => timeline.evaluate((node) => node.scrollLeft))
    .toBeGreaterThan(0);
  const history = page.locator(".timeline-item");
  await history.first().focus();
  await page.keyboard.press("ArrowRight");
  await expect(history.nth(1)).toHaveAttribute("aria-pressed", "true");
  await page.getByRole("tab", { name: /Mercedes-AMG/ }).focus();
  await page.keyboard.press("Home");
  await expect(
    page.getByRole("tab", { name: /Scuderia Ferrari/ }),
  ).toHaveAttribute("aria-selected", "true");
});

test("constructor comparison exposes shapes, matches detail cameras and stays usable on mobile", async ({
  page,
}) => {
  await page.goto(`${prefix}/`);
  await expect(page.locator(".stage-caption")).toBeVisible({ timeout: 45000 });
  await page
    .getByRole("button", { name: "Compare teams", exact: true })
    .click();
  await expect(page.locator(".team-comparison .stage-caption")).toHaveCount(2);
  await expect(page.locator(".constructor-label").first()).toContainText(
    "Ferrari",
  );
  await expect(page.locator(".constructor-label").nth(1)).toContainText(
    "Mercedes",
  );
  await page
    .getByRole("button", { name: "Show neutral surfaces", exact: true })
    .click();
  for (const stage of await page.locator(".car-stage").all())
    await expect(stage).toHaveAttribute("data-material-mode", "shape");
  await page.getByRole("button", { name: "Inlets & undercut" }).click();
  await expect(page.getByLabel("Component", { exact: true })).toHaveValue(
    "sidepods",
  );
  await page.getByLabel("Isolate component", { exact: true }).check();
  for (const stage of await page.locator(".car-stage").all())
    await expect(stage).toHaveAttribute("data-isolated-component", "sidepods");
  const cameras = page.locator("canvas");
  await expect
    .poll(
      async () =>
        (await cameras.first().getAttribute("data-camera-position")) ===
        (await cameras.nth(1).getAttribute("data-camera-position")),
    )
    .toBe(true);
  await cameras.first().focus();
  await page.keyboard.press("ArrowLeft");
  await expect
    .poll(
      async () =>
        (await cameras.first().getAttribute("data-camera-position")) ===
        (await cameras.nth(1).getAttribute("data-camera-position")),
    )
    .toBe(true);
  await expect(
    page.getByRole("link", { name: "View Ferrari reference" }).first(),
  ).toHaveAttribute("href", /^https:\/\//);
  await expect(
    page.getByRole("link", { name: "View Mercedes reference" }).first(),
  ).toHaveAttribute("href", /^https:\/\//);
  await page.getByRole("button", { name: "Airbox & spine" }).click();
  await expect(page.getByLabel("Component", { exact: true })).toHaveValue(
    "engine_cover",
  );
  await page
    .getByRole("button", { name: "Neutral surfaces", exact: true })
    .click();
  for (const stage of await page.locator(".car-stage").all())
    await expect(stage).toHaveAttribute("data-material-mode", "livery");
  await page.setViewportSize({ width: 390, height: 844 });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("tab", { name: /Mercedes-AMG/ }).click();
  await expect(
    page.locator(".constructor-pane").first().locator(".car-stage"),
  ).toHaveAttribute("aria-label", /^mercedes /);
  await expect(
    page.locator(".constructor-pane").nth(1).locator(".car-stage"),
  ).toHaveAttribute("aria-label", /^ferrari /);
  await expect(page.locator(".team-comparison .stage-caption")).toHaveCount(2);
});

test("a failed archive request can be retried without a backend", async ({
  page,
}) => {
  let fail = true;
  await page.route(`**${prefix}/archive/index.json`, (route) =>
    fail
      ? route.fulfill({ status: 503, body: "Temporary failure" })
      : route.continue(),
  );
  await page.goto(`${prefix}/`);
  await expect(page.locator(".notice.error")).toContainText(
    "could not be loaded",
  );
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(page.locator(".notice.error")).toHaveCount(0);
  await expect(
    page.getByRole("tab", { name: /Scuderia Ferrari/ }),
  ).toBeVisible();
});
