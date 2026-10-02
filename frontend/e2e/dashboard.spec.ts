import { test, expect, type Page } from "@playwright/test";
import { analyzeDescription } from "../src/lib/upgrade-analysis";
import { parseStandings } from "../src/lib/standings";
import { gapLabel, lapTime, parseResults } from "../src/lib/session-results";
import {
  countdown,
  isRaceDay,
  currentWeekend,
  nextPollDelay,
  parseJolpicaSchedule,
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

const driver = (
  position: number,
  given: string,
  family: string,
  points: number,
  wins: number,
  ...teams: [string, string][]
) => ({
  position: String(position),
  points: String(points),
  wins: String(wins),
  Driver: { givenName: given, familyName: family, code: family.slice(0, 3) },
  Constructors: teams.map(([constructorId, name]) => ({ constructorId, name })),
});
const jolpica = {
  drivers: {
    MRData: {
      StandingsTable: {
        season: "2026",
        StandingsLists: [
          {
            round: "15",
            DriverStandings: Array.from({ length: 12 }, (_, i) =>
              i === 0
                ? driver(1, "Andrea Kimi", "Antonelli", 302, 8, [
                    "mercedes",
                    "Mercedes",
                  ])
                : i === 1
                  ? driver(
                      2,
                      "Liam",
                      "Lawson",
                      120,
                      0,
                      ["red_bull", "Red Bull"],
                      ["rb", "RB F1 Team"],
                    )
                  : driver(i + 1, "Driver", `Number${i + 1}`, 100 - i, 0, [
                      "haas",
                      "Haas F1 Team",
                    ]),
            ),
          },
        ],
      },
    },
  },
  constructors: {
    MRData: {
      StandingsTable: {
        season: "2026",
        StandingsLists: [
          {
            round: "15",
            ConstructorStandings: [
              {
                position: "1",
                points: "538",
                wins: "9",
                Constructor: { constructorId: "mercedes", name: "Mercedes" },
              },
              {
                position: "2",
                points: "83",
                wins: "0",
                Constructor: { constructorId: "rb", name: "RB F1 Team" },
              },
            ],
          },
        ],
      },
    },
  },
};

const result = (
  position: number | null,
  driver_number: number,
  duration: number | (number | null)[] | null,
  gap_to_leader: number | null,
  extra = {},
) => ({
  position,
  driver_number,
  number_of_laps: 51,
  duration,
  gap_to_leader,
  dnf: false,
  dns: false,
  dsq: false,
  ...extra,
});
const drivers = [
  [63, "RUS", "George", "Russell", "Mercedes", "00D7B6"],
  [16, "LEC", "Charles", "Leclerc", "Ferrari", "ED1131"],
  [3, "VER", "Max", "Verstappen", "Red Bull Racing", "4781D7"],
].map(
  ([number, name_acronym, first_name, last_name, team_name, team_colour]) => ({
    driver_number: Number(number),
    name_acronym: String(name_acronym),
    first_name: String(first_name),
    last_name: String(last_name),
    team_name: String(team_name),
    team_colour: String(team_colour),
  }),
);
const results: Record<string, unknown[]> = {
  // Practice 1: best laps.
  "40": [result(1, 16, 97.528, 0), result(2, 63, 97.627, 0.099)],
  // Qualifying: Q1–Q3.
  "43": [
    result(1, 63, [103.615, 103.462, 102.526], null),
    result(2, 16, [104.36, 103.78, 103.363], null),
    result(3, 3, [106.658, null, null], null),
  ],
};

test.beforeEach(async ({ page }) => {
  await page.route("https://api.jolpi.ca/**", (route) =>
    route.fulfill({
      json: route.request().url().includes("driverstandings")
        ? jolpica.drivers
        : jolpica.constructors,
    }),
  );
  await page.route("https://api.openf1.org/v1/*", (route) => {
    const url = new URL(route.request().url());
    const key = url.searchParams.get("session_key") ?? "";
    return route.fulfill({
      json: url.pathname.endsWith("/meetings")
        ? openF1.meetings
        : url.pathname.endsWith("/session_result")
          ? (results[key] ?? [])
          : url.pathname.endsWith("/drivers")
            ? drivers
            : openF1.sessions,
    });
  });
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

test("race week home lists every car, and four tabs group the sections", async ({
  page,
}) => {
  const data = await snapshot(page);
  await page.goto(`${prefix}/`);
  await expect(page.getByRole("heading", { name: "Race week." })).toBeVisible();
  await expect(page.locator(".d-stat").nth(1).locator("strong")).toHaveText(
    String(Object.values(data.versions).flat().length).padStart(2, "0"),
  );
  await expect(page.locator(".d-grid-car")).toHaveCount(
    Object.keys(data.catalog.teams).length,
  );
  await expect(
    page.getByRole("link", { name: /^Inspect Mercedes W17 in 3D/ }),
  ).toHaveAttribute("href", `${prefix}/car/mercedes/`);
  await page
    .getByLabel("Filter development log by team")
    .selectOption("mercedes");
  for (const row of await page.locator(".d-release-row").all())
    await expect(row.locator(".d-team-label")).toHaveText("Mercedes");

  const navigation = page.getByRole("navigation", { name: "Main navigation" });
  await expect(navigation.getByRole("link")).toHaveText([
    "Race Week",
    "Cars",
    "Compare",
    "Development",
  ]);
  await navigation.getByRole("link", { name: "Development" }).click();
  await expect(
    page.getByRole("heading", { name: "Follow the changes." }),
  ).toBeVisible();
  const development = page.getByRole("navigation", {
    name: "Development pages",
  });
  await expect(development.getByRole("link")).toHaveText([
    "Change log",
    "Performance",
    "Sources",
    "Analyze",
  ]);
  await development.getByRole("link", { name: "Sources" }).click();
  await expect(
    navigation.getByRole("link", { name: "Development" }),
  ).toHaveAttribute("aria-current", "page");
  await expect(
    development.getByRole("link", { name: "Sources" }),
  ).toHaveAttribute("aria-current", "page");

  // The car page keeps the main navigation and the team follows the URL.
  await page.goto(`${prefix}/car/ferrari/`);
  await expect(navigation.getByRole("link", { name: "Cars" })).toHaveAttribute(
    "aria-current",
    "page",
  );
  await page.getByRole("tab", { name: /Mercedes/ }).click();
  await expect(page).toHaveURL(new RegExp(`${prefix}/car/mercedes/$`));
  await page.goto(`${prefix}/models/?team=mercedes`);
  await expect(page.getByRole("tab", { name: /Mercedes/ })).toHaveAttribute(
    "aria-selected",
    "true",
  );
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
  // Hyphenated spellings and 2026 vocabulary.
  expect(analyzeDescription("New front-wing flaps", "")[0].label).toBe(
    "Front wing",
  );
  expect(analyzeDescription("Revised MGU-K deployment", "")[0].label).toBe(
    "Power unit",
  );
  expect(
    analyzeDescription("New X-mode rear wing flap", "").map((x) => x.label),
  ).toEqual(expect.arrayContaining(["Active aero", "Rear wing"]));
  expect(analyzeDescription("Revised halo fairing", "")[0].label).toBe(
    "Halo & mirrors",
  );
  expect(analyzeDescription("Lower DRS drag", "")).toHaveLength(0);
});

test("analyzer links matched components to archive changes and sources", async ({
  page,
}) => {
  await page.goto(`${prefix}/analyze/`);
  await expect(page.getByLabel("Claimed effect")).toHaveCount(0);
  await page
    .getByLabel("Upgrade description", { exact: false })
    .fill("Revised floor edge");
  await page.getByRole("button", { name: "Analyze upgrade" }).click();
  const card = page.locator(".d-analysis-card").first();
  await expect(card).toContainText("Published changes:");
  await card.getByRole("link", { name: "See changes" }).click();
  await expect(
    page.getByRole("combobox", { name: "Component", exact: true }),
  ).toHaveValue("floor");
  await expect(page.locator(".d-release-row").first()).toBeVisible();
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
  await expect(page.locator(".d-grid-car").first()).toContainText(
    "No release yet",
  );
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
  expect(weekend.previous?.meeting_name).toBe("Australian Grand Prix");
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
  await expect(panel).toContainText("Baku · Azerbaijan");
  await expect(panel).toContainText("SPRINT");
  await expect(panel).toContainText("LIVE · Qualifying");
  await expect(panel.locator('[data-status="live"]')).toContainText(
    "Qualifying",
  );

  await page.evaluate(() => localStorage.clear());
  await page.route("https://api.openf1.org/v1/*", (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await page.route(isJolpicaSchedule, (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await page.reload();
  await expect(panel).toContainText("Still updating the race calendar");
  await expect(panel.getByRole("button", { name: "Retry" })).toBeVisible();
  await expect(panel.getByRole("alert")).toHaveCount(0);
});

const isJolpicaSchedule = (url: URL) =>
  url.host === "api.jolpi.ca" && url.pathname.endsWith("/2026.json");
const malaysia = {
  round: "16",
  raceName: "Bahrain Grand Prix in Malaysia",
  Circuit: { Location: { locality: "Kuala Lumpur", country: "Malaysia" } },
  date: "2026-10-04",
  time: "07:00:00Z",
  FirstPractice: { date: "2026-10-02", time: "04:30:00Z" },
  SecondPractice: { date: "2026-10-02", time: "08:00:00Z" },
  ThirdPractice: { date: "2026-10-03", time: "04:30:00Z" },
  Qualifying: { date: "2026-10-03", time: "08:00:00Z" },
};

test("race weekend falls back to Jolpica while OpenF1 is locked for a live session", async ({
  page,
}) => {
  const at = Date.parse("2026-10-02T08:15:00Z");
  const schedule = parseJolpicaSchedule([malaysia], at);
  const weekend = currentWeekend(schedule, at)!;
  expect(weekend.sessions.map((s) => [s.session_name, s.date_start])).toEqual([
    ["Practice 1", "2026-10-02T04:30:00.000Z"],
    ["Practice 2", "2026-10-02T08:00:00.000Z"],
    ["Practice 3", "2026-10-03T04:30:00.000Z"],
    ["Qualifying", "2026-10-03T08:00:00.000Z"],
    ["Race", "2026-10-04T07:00:00.000Z"],
  ]);
  // Waits out the live session instead of polling the locked API.
  expect(nextPollDelay(weekend, at, "jolpica")).toBe(45 * 60_000);
  expect(nextPollDelay(weekend, at, "openf1")).toBe(RACE_WEEK_POLL_MS);

  await page.route("https://api.openf1.org/v1/*", (route) =>
    route.fulfill({
      status: 401,
      json: { detail: "Live F1 session in progress." },
    }),
  );
  await page.route(isJolpicaSchedule, (route) =>
    route.fulfill({ json: { MRData: { RaceTable: { Races: [malaysia] } } } }),
  );
  await page.clock.setFixedTime(new Date(at));
  await page.goto(`${prefix}/`);
  const panel = page.getByRole("region", { name: "Race weekend" });
  await expect(
    panel.getByRole("heading", { name: "Bahrain Grand Prix in Malaysia" }),
  ).toBeVisible();
  await expect(panel).toContainText("Kuala Lumpur · Malaysia");
  // Practice 1 is over but OpenF1 is locked and nothing was cached.
  const results = panel.getByRole("region", { name: "Session results" });
  await expect(results).toContainText("OpenF1 locks timing");
  await expect(
    results.getByRole("button", { name: "Practice 2 · Live" }),
  ).toHaveAttribute("aria-pressed", "true");
  await expect(panel).toContainText("LIVE · Practice 2");
  await expect(panel).toContainText("Estimated end");
  await expect(panel.locator('[data-status="finished"]')).toContainText(
    "Practice 1",
  );
  await expect(panel.locator(".d-weekend-sessions li")).toHaveCount(5);
  await expect(panel).not.toContainText("track");
  await expect(panel).toContainText("times are from Jolpica");
  await expect(panel).not.toContainText("Still updating");
});

test("session results parse OpenF1 classifications", () => {
  const race = parseResults(
    [
      result(null, 3, null, null, { dnf: true }),
      result(2, 16, 5882.339, 0.196, { points: 18 }),
      result(1, 63, 5882.143, 0, { points: 25 }),
      result(3, 99, 5892.847, "+1 LAP" as unknown as number),
    ],
    drivers,
    1,
  );
  expect(race.rows.map((r) => [r.position, r.code, r.status])).toEqual([
    [1, "RUS", undefined],
    [2, "LEC", undefined],
    [3, "99", undefined],
    [null, "VER", "DNF"],
  ]);
  expect(race.rows[0]).toMatchObject({
    name: "George Russell",
    colour: "#00D7B6",
    points: 25,
  });
  expect(lapTime(97.528)).toBe("1:37.528");
  expect(lapTime(5882.143)).toBe("1:38:02.143");
  expect(gapLabel(0.196)).toBe("+0.196");
  expect(gapLabel("+1 LAP")).toBe("+1 LAP");
  expect(gapLabel(0)).toBe("");
});

test("race weekend shows the classification of each completed session", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-09-25T14:00:00Z"));
  await page.goto(`${prefix}/`);
  const results = page.getByRole("region", { name: "Session results" });
  await expect(results.getByRole("button")).toHaveText([
    "Practice 1",
    "Sprint Qualifying",
    "Sprint",
    "Qualifying",
  ]);
  const quali = results.getByRole("table", {
    name: "Qualifying classification",
  });
  await expect(quali.locator("thead th")).toHaveText([
    "Pos",
    "Driver",
    "Q1",
    "Q2",
    "Q3",
    "Laps",
  ]);
  await expect(quali.locator("tbody tr").first()).toContainText(
    "George Russell",
  );
  await expect(quali.locator("tbody tr").first()).toContainText("1:42.526");
  await expect(results).toContainText("Classification from OpenF1");

  await results.getByRole("button", { name: "Practice 1" }).click();
  const practice = results.getByRole("table", {
    name: "Practice 1 classification",
  });
  await expect(practice.locator("tbody tr").nth(1)).toContainText("1:37.627");
  await expect(practice.locator("tbody tr").nth(1)).toContainText("+0.099");

  await results.getByRole("button", { name: "Sprint", exact: true }).click();
  await expect(results).toContainText("Waiting for OpenF1");
});

test("countdown keeps seconds and race day follows the circuit's date", () => {
  expect(countdown(93_784_000)).toBe("1d 02:03:04");
  expect(countdown(3_723_000)).toBe("01:02:03");
  expect(countdown(-5)).toBe("00:00:00");
  const race = openF1.sessions.find((s) => s.session_name === "Race")!;
  // Race: 26 Sept 11:00 UTC at UTC+4. 21:00 UTC on the 25th is already the 26th in Baku.
  expect(isRaceDay(race, Date.parse("2026-09-25T21:00:00Z"))).toBe(true);
  expect(isRaceDay(race, Date.parse("2026-09-25T19:00:00Z"))).toBe(false);
  expect(isRaceDay(undefined, Date.now())).toBe(false);
});

test("race day shows a live lights-out countdown", async ({ page }) => {
  await page.clock.setFixedTime(new Date("2026-09-26T08:00:00Z"));
  await page.goto(`${prefix}/`);
  const clock = page.locator(".d-weekend-clock");
  await expect(clock).toContainText("RACE DAY · Lights out in");
  await expect(clock.locator("strong")).toHaveText("03:00:00");
  await page.clock.setFixedTime(new Date("2026-09-26T08:00:05Z"));
  await expect(clock.locator("strong")).toHaveText("02:59:55");
});

test("standings map Jolpica teams and use each driver's latest team", () => {
  const standings = parseStandings(jolpica.drivers, jolpica.constructors, 1);
  expect(standings.round).toBe(15);
  expect(standings.drivers[0]).toMatchObject({
    name: "Andrea Kimi Antonelli",
    points: 302,
    wins: 8,
    teamKey: "mercedes",
  });
  expect(standings.drivers[1]).toMatchObject({
    team: "RB F1 Team",
    teamKey: "racing_bulls",
  });
  expect(standings.constructors[1].teamKey).toBe("racing_bulls");
});

test("dashboard shows both championships and keeps retrying quietly", async ({
  page,
}) => {
  await page.goto(`${prefix}/`);
  const section = page.getByRole("region", { name: "Championship standings" });
  await expect(section).toContainText("2026 · after round 15");
  const drivers = section.getByRole("table", { name: "Drivers' championship" });
  await expect(drivers.locator("tbody tr")).toHaveCount(10);
  await expect(drivers.locator("tbody tr").first()).toContainText(
    "Andrea Kimi Antonelli",
  );
  await section.getByText("Show all 12 drivers").click();
  await expect(
    section.getByRole("table", { name: "Drivers' championship, continued" }),
  ).toBeVisible();
  await expect(
    section.getByRole("table", { name: "Constructors' championship" }),
  ).toContainText("538");

  await page.evaluate(() => localStorage.clear());
  await page.route("https://api.jolpi.ca/**", (route) =>
    route.fulfill({ status: 503, body: "Unavailable" }),
  );
  await page.reload();
  await expect(section).toContainText("Still updating the standings");
  await expect(section.getByRole("button", { name: "Retry" })).toBeVisible();
});

test("home highlights configurations from the current or previous Grand Prix", async ({
  page,
}) => {
  const data = await snapshot(page);
  const madrid = (
    Object.values(data.versions).flat() as { configuration_event: string }[]
  ).filter((v) => v.configuration_event.startsWith("Spanish Grand Prix"));
  await page.route("https://api.openf1.org/v1/*", (route) =>
    route.fulfill({
      json: route.request().url().includes("/meetings")
        ? [
            {
              ...openF1.meetings[3],
              meeting_key: 9,
              meeting_name: "Spanish Grand Prix",
              date_start: "2026-09-11T11:30:00Z",
              date_end: "2026-09-13T15:00:00Z",
            },
            openF1.meetings[3],
          ]
        : openF1.sessions,
    }),
  );
  await page.clock.setFixedTime(new Date("2026-09-22T12:00:00Z"));
  await page.goto(`${prefix}/`);
  const block = page.getByRole("region", {
    name: "Changes from the Spanish Grand Prix",
  });
  await expect(
    block.getByRole("heading", { name: "From the Spanish Grand Prix" }),
  ).toBeVisible();
  await expect(block.locator(".d-release-row")).toHaveCount(
    Math.min(3, madrid.length),
  );
  await block.getByRole("link", { name: `All ${madrid.length}` }).click();
  await expect(page.getByLabel("Event / configuration")).toHaveValue(
    "Spanish Grand Prix / Madrid Friday practice",
  );
  await expect(page.locator(".d-release-row")).toHaveCount(madrid.length);
});

test("home hides the Grand Prix block when nothing matches", async ({
  page,
}) => {
  await page.clock.setFixedTime(new Date("2026-09-25T12:30:00Z"));
  await page.goto(`${prefix}/`);
  await expect(
    page.getByRole("heading", { name: "Azerbaijan Grand Prix" }),
  ).toBeVisible();
  await expect(page.getByRole("heading", { name: /^From the / })).toHaveCount(
    0,
  );
});
