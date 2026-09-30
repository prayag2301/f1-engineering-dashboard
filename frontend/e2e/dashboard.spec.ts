import { test, expect, type Page } from "@playwright/test";
import { analyzeDescription } from "../src/lib/upgrade-analysis";
import {
  currentWeekend,
  nextPollDelay,
  sessionStatus,
  IDLE_POLL_MS,
  RACE_WEEK_POLL_MS,
} from "../src/lib/race-weekend";

const prefix = process.env.NEXT_PUBLIC_BASE_PATH ?? "/f1-engineering-dashboard";

const meeting = (
  key: number,
  name: string,
  start: string,
  end: string,
  cancelled = false,
) => ({
  meeting_key: key,
  meeting_name: name,
  location: "Baku",
  country_name: "Azerbaijan",
  circuit_short_name: "Baku",
  gmt_offset: "04:00:00",
  date_start: start,
  date_end: end,
  is_cancelled: cancelled,
});
const session = (
  key: number,
  meeting_key: number,
  name: string,
  start: string,
  end: string,
) => ({
  session_key: key,
  meeting_key,
  session_name: name,
  date_start: start,
  date_end: end,
  gmt_offset: "04:00:00",
  is_cancelled: false,
});
const openF1 = {
  meetings: [
    meeting(
      1,
      "Pre-Season Testing",
      "2026-02-11T07:00:00Z",
      "2026-02-13T16:00:00Z",
    ),
    meeting(
      2,
      "Australian Grand Prix",
      "2026-03-06T01:30:00Z",
      "2026-03-08T06:00:00Z",
    ),
    meeting(
      3,
      "Bahrain Grand Prix",
      "2026-04-10T11:30:00Z",
      "2026-04-12T17:00:00Z",
      true,
    ),
    meeting(
      4,
      "Azerbaijan Grand Prix",
      "2026-09-24T08:30:00Z",
      "2026-09-26T13:00:00Z",
    ),
  ],
  sessions: [
    session(
      40,
      4,
      "Practice 1",
      "2026-09-24T08:30:00Z",
      "2026-09-24T09:30:00Z",
    ),
    session(
      41,
      4,
      "Sprint Qualifying",
      "2026-09-24T12:30:00Z",
      "2026-09-24T13:14:00Z",
    ),
    session(42, 4, "Sprint", "2026-09-25T08:30:00Z", "2026-09-25T09:30:00Z"),
    session(
      43,
      4,
      "Qualifying",
      "2026-09-25T12:00:00Z",
      "2026-09-25T13:00:00Z",
    ),
    session(44, 4, "Race", "2026-09-26T11:00:00Z", "2026-09-26T13:00:00Z"),
  ],
};

test.beforeEach(async ({ page }) => {
  await page.route("https://api.openf1.org/v1/*", (route) =>
    route.fulfill({
      json: route.request().url().includes("/meetings")
        ? openF1.meetings
        : openF1.sessions,
    }),
  );
  page.on("pageerror", (error) => {
    throw error;
  });
  page.on("request", (request) => {
    expect(
      new URL(request.url()).pathname,
      "Public workflows must work without API access",
    ).not.toContain("/api/");
  });
});

async function snapshot(page: Page) {
  return (await page.request.get(`${prefix}/archive/index.json`)).json();
}

test("dashboard uses published counts, switches car previews and retains section navigation", async ({
  page,
}) => {
  const data = await snapshot(page);
  await page.goto(`${prefix}/`);
  await expect(
    page.getByRole("heading", { name: "Engineering dashboard." }),
  ).toBeVisible();
  await expect(page.locator(".d-stat").nth(1).locator("strong")).toHaveText(
    String(Object.values(data.versions).flat().length).padStart(2, "0"),
  );
  await page.getByRole("button", { name: "Mercedes", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Inspect Mercedes in 3D" }),
  ).toHaveAttribute("href", `${prefix}/car/mercedes/`);
  await expect(page.locator(".d-poster-link img")).toHaveAttribute(
    "alt",
    /W17/,
  );
  await page
    .getByLabel("Filter development log by team")
    .selectOption("mercedes");
  for (const row of await page.locator(".d-release-row").all())
    await expect(row.locator(".d-team-label")).toHaveText("Mercedes");
  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  for (const section of [
    "Dashboard",
    "Cars",
    "Teams",
    "Upgrades",
    "Compare",
    "Performance",
    "Evidence",
    "Analyze",
  ])
    await expect(
      navigation.getByRole("link", { name: section, exact: true }),
    ).toBeVisible();
  await navigation.getByRole("link", { name: "Cars", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "The car. The changes." }),
  ).toBeVisible();
  await expect(
    navigation.getByRole("link", { name: "Cars", exact: true }),
  ).toHaveAttribute("aria-current", "page");
});

test("development filters distinguish reconstructions from upgrade reports", async ({
  page,
}) => {
  await page.goto(`${prefix}/upgrades/`);
  await expect(page.locator(".d-release-row").first()).toBeVisible();
  await page
    .getByRole("combobox", { name: "Constructor", exact: true })
    .selectOption("ferrari");
  await page
    .getByRole("combobox", { name: "Component", exact: true })
    .selectOption("suspension");
  await page.getByLabel("Record type").selectOption("reconstruction");
  for (const row of await page.locator(".d-release-row").all()) {
    await expect(row.locator(".d-team-label")).toHaveText("Ferrari");
    await expect(row.locator(".d-tags")).toContainText("Suspension");
  }
  await page
    .locator(".d-release-row")
    .first()
    .getByText("What changed & supporting evidence", { exact: true })
    .click();
  await expect(
    page.locator(".d-release-row").first().locator("details a").first(),
  ).toHaveAttribute("href", /^https:\/\//);
  await page.getByLabel("Record type").selectOption("reports");
  const data = await snapshot(page);
  const reports = data.versions.ferrari.filter(
    (v: any) =>
      v.manifest.changes.length &&
      (v.manifest.components.suspension?.changed ||
        v.manifest.changes.some((c: any) => c.component === "suspension")),
  );
  await expect(page.locator(".d-release-row")).toHaveCount(reports.length);
  if (!reports.length)
    await expect(
      page.getByRole("heading", { name: "No matching changes" }),
    ).toBeVisible();
  await page.getByRole("button", { name: "Reset filters" }).click();
  await expect(page.locator(".d-release-row")).toHaveCount(
    Object.values(data.versions).flat().length,
  );
});

test("evidence search retains source dates, provenance and component links", async ({
  page,
}) => {
  await page.goto(`${prefix}/evidence/`);
  await page
    .getByRole("combobox", { name: "Constructor", exact: true })
    .selectOption("mercedes");
  await page
    .getByRole("combobox", { name: "Component", exact: true })
    .selectOption("sidepods");
  await expect(page.locator(".d-evidence-card").first()).toBeVisible();
  for (const card of await page.locator(".d-evidence-card").all()) {
    await expect(
      card.getByRole("link", { name: "Mercedes ↗", exact: true }),
    ).toBeVisible();
    await expect(card.locator("h2 a")).toHaveAttribute("href", /^https:\/\//);
    await expect(card.locator(".d-key-values")).toContainText("Published");
  }
  await page.getByRole("searchbox").fill("no-matching-reference-xyz");
  await expect(
    page.getByRole("heading", { name: "No matching evidence" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Reset filters" }).click();
  await page.locator(".d-evidence-card").first().locator("summary").click();
  await expect(page.locator(".d-reference-versions").first()).toBeVisible();
});

test("teams preserve the directory and filter model availability", async ({
  page,
}) => {
  await page.goto(`${prefix}/teams/`);
  const data = await snapshot(page);
  const count = Object.keys(data.catalog.teams).length;
  await expect(page.locator(".d-team-card")).toHaveCount(count);
  await expect(page.locator(".d-directory-grid article")).toHaveCount(
    11 - count,
  );
  await page.getByLabel("Published models only").check();
  await expect(page.locator(".d-directory-grid article")).toHaveCount(0);
  await page.getByRole("searchbox").fill("Ferrari");
  await expect(page.locator(".d-team-card")).toHaveCount(1);
  await page.getByRole("searchbox").fill("unknown constructor");
  await expect(
    page.getByRole("heading", { name: "No constructors found" }),
  ).toBeVisible();
});

test("analyzer handles unknown text, component signals and stale input without saving data", async ({
  page,
}) => {
  await page.goto(`${prefix}/analyze/`);
  const submit = page.getByRole("button", {
    name: "Analyze upgrade",
    exact: false,
  });
  await expect(submit).toBeDisabled();
  await page
    .getByLabel("Upgrade description", { exact: false })
    .fill("No technical terms here");
  await submit.click();
  await expect(
    page.getByRole("heading", { name: "No clear component signals" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Try a front-wing example" }).click();
  await submit.click();
  await expect(
    page.getByRole("heading", { name: "Front wing", exact: true }),
  ).toBeVisible();
  await expect(page.locator(".d-analysis-notice")).toContainText(
    "not confirmed gains",
  );
  await page
    .getByLabel("Upgrade description", { exact: false })
    .fill("Revised rear wing");
  await expect(
    page.getByRole("heading", { name: "Front wing", exact: true }),
  ).toHaveCount(0);
  await submit.click();
  await expect(
    page.getByRole("heading", { name: "Rear wing", exact: true }),
  ).toBeVisible();
});

test("analyzer matches complete technical terms without spurious ERS matches", () => {
  expect(
    analyzeDescription("Drivers and engineers prepared the car", ""),
  ).toHaveLength(0);
  expect(analyzeDescription("Revised rear wing endplates", "")[0].label).toBe(
    "Rear wing",
  );
  expect(
    analyzeDescription("Changed front wing", "New suspension fairing").map(
      (x) => x.label,
    ),
  ).toContain("Suspension");
  expect(analyzeDescription("Revised floor edge", "")[0].label).toBe(
    "Floor edge",
  );
});

test("performance charts describe activity and never invent measured gains", async ({
  page,
}) => {
  await page.goto(`${prefix}/performance/`);
  await expect(
    page.getByRole("img", { name: /^Published releases:/ }),
  ).toBeVisible();
  await page
    .getByRole("button", { name: "Component revisions", exact: true })
    .click();
  await expect(
    page.getByRole("img", { name: /^Component revisions:/ }),
  ).toBeVisible();
  await expect(page.locator(".d-timing-panel")).toContainText(
    "TIMING DATA UNAVAILABLE",
  );
  await expect(page.locator(".d-table tbody")).toContainText("Not measured");
});

test("dashboard recovers from a failed snapshot and handles an empty archive", async ({
  page,
}) => {
  let fail = true;
  const data = await snapshot(page);
  data.versions = { ferrari: [], mercedes: [] };
  await page.route(`**${prefix}/archive/index.json`, (route) =>
    fail ? route.fulfill({ status: 503 }) : route.fulfill({ json: data }),
  );
  await page.goto(`${prefix}/`);
  await expect(page.locator('.notice[role="alert"]')).toContainText(
    "could not be loaded",
  );
  fail = false;
  await page.getByRole("button", { name: "Try again" }).click();
  await expect(
    page.getByRole("heading", { name: "No published model yet" }),
  ).toBeVisible();
  await expect(
    page.getByRole("heading", { name: "The development log is empty" }),
  ).toBeVisible();
  await expect(page.locator(".d-stat").first().locator("strong")).toHaveText(
    "00",
  );
});

test("dashboard sections remain usable on mobile with no page overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of [
    "",
    "teams/",
    "upgrades/",
    "performance/",
    "evidence/",
    "analyze/",
  ]) {
    await page.goto(`${prefix}/${path}`);
    await expect(page.locator(".d-loading")).toHaveCount(0);
    await expect(page.getByRole("heading", { level: 1 })).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
      path,
    ).toBe(true);
  }
  const link = page
    .getByRole("navigation")
    .getByRole("link", { name: "Analyze", exact: true });
  await link.focus();
  await expect(link).toBeFocused();
});

test("race weekend skips testing and cancelled rounds and derives session status", () => {
  const at = (iso: string) => Date.parse(iso);
  const weekend = currentWeekend(openF1, at("2026-09-25T12:30:00Z"))!;
  expect(weekend.meeting.meeting_name).toBe("Azerbaijan Grand Prix");
  expect(weekend.round).toBe(2);
  expect(weekend.sprint).toBe(true);
  expect(weekend.raceWeek).toBe(true);
  expect(
    weekend.sessions.map((s) => sessionStatus(s, at("2026-09-25T12:30:00Z"))),
  ).toEqual(["finished", "finished", "finished", "live", "upcoming"]);
  expect(nextPollDelay(weekend, at("2026-09-25T12:30:00Z"))).toBe(
    RACE_WEEK_POLL_MS,
  );
  const early = currentWeekend(openF1, at("2026-09-01T00:00:00Z"))!;
  expect(early.raceWeek).toBe(false);
  expect(nextPollDelay(early, at("2026-09-01T00:00:00Z"))).toBe(IDLE_POLL_MS);
  // Still current on race evening, gone the day after.
  expect(currentWeekend(openF1, at("2026-09-26T20:00:00Z"))).not.toBeNull();
  expect(currentWeekend(openF1, at("2026-09-27T12:00:00Z"))).toBeNull();
});

test("race weekend panel shows the live session and keeps retrying quietly", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-09-25T12:30:00Z"));
  await page.goto(`${prefix}/`);
  const panel = page.getByRole("region", { name: "Race weekend" });
  await expect(
    panel.getByRole("heading", { name: "Azerbaijan Grand Prix" }),
  ).toBeVisible();
  await expect(panel).toContainText("RACE WEEK · ROUND 02");
  await expect(panel).toContainText("SPRINT");
  await expect(panel).toContainText("LIVE · Qualifying");
  await expect(panel.locator('[data-status="live"]')).toContainText(
    "Qualifying",
  );

  await page.evaluate(() => localStorage.clear());
  await page.route("https://api.openf1.org/v1/*", (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await page.reload();
  await expect(panel).toContainText("Still updating the race calendar");
  await expect(panel.getByRole("button", { name: "Retry" })).toBeVisible();
  await expect(panel.getByRole("alert")).toHaveCount(0);
});
