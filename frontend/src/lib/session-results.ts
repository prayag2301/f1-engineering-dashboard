import { OPENF1, getJSON } from "./race-weekend";

// Session classifications from OpenF1 (two requests per session). OpenF1 locks
// anonymous access while a session is live, so results arrive once it ends.
const CACHE_KEY = "f1-session-results";
const KEEP_MS = 14 * 86_400_000;

export interface ResultRow {
  position: number | null;
  name: string;
  code: string;
  team: string;
  colour?: string;
  laps: number;
  // Best lap in practice, Q1–Q3 in qualifying, total time in a race.
  times: (number | null)[];
  gap: number | string | null;
  points?: number;
  status?: "DNF" | "DNS" | "DSQ";
}

export interface SessionResults {
  rows: ResultRow[];
  fetchedAt: number;
}

interface ApiResult {
  position: number | null;
  driver_number: number;
  number_of_laps: number;
  duration: number | (number | null)[] | null;
  gap_to_leader: number | string | (number | string | null)[] | null;
  points?: number;
  dnf: boolean;
  dns: boolean;
  dsq: boolean;
}
interface ApiDriver {
  driver_number: number;
  name_acronym: string;
  first_name: string;
  last_name: string;
  team_name: string;
  team_colour?: string;
}

export function parseResults(
  results: ApiResult[],
  drivers: ApiDriver[],
  fetchedAt: number,
): SessionResults {
  const rows = results.map((r): ResultRow => {
    const d = drivers.find((x) => x.driver_number === r.driver_number);
    const gap = Array.isArray(r.gap_to_leader) ? null : r.gap_to_leader;
    return {
      position: r.position,
      name: d ? `${d.first_name} ${d.last_name}` : `#${r.driver_number}`,
      code: d?.name_acronym ?? String(r.driver_number),
      team: d?.team_name ?? "",
      colour: d?.team_colour ? `#${d.team_colour}` : undefined,
      laps: r.number_of_laps,
      times: Array.isArray(r.duration) ? r.duration : [r.duration],
      gap,
      points: r.points,
      status: r.dsq ? "DSQ" : r.dns ? "DNS" : r.dnf ? "DNF" : undefined,
    };
  });
  // Unclassified drivers keep OpenF1's order after the classified ones.
  rows.sort((a, b) => (a.position ?? 99) - (b.position ?? 99));
  return { rows, fetchedAt };
}

export async function fetchResults(
  sessionKey: number,
  signal?: AbortSignal,
): Promise<SessionResults> {
  // One at a time: OpenF1 allows 3 requests a second, shared with the schedule.
  const results = await getJSON<ApiResult[]>(
    `${OPENF1}/session_result?session_key=${sessionKey}`,
    signal,
  );
  const drivers = await getJSON<ApiDriver[]>(
    `${OPENF1}/drivers?session_key=${sessionKey}`,
    signal,
  );
  if (!Array.isArray(results) || !Array.isArray(drivers))
    throw new Error("Unexpected OpenF1 response.");
  return parseResults(results, drivers, Date.now());
}

// Keyed by session start time, which OpenF1 and Jolpica share, so results
// loaded earlier still show while OpenF1 is locked and Jolpica's calendar is up.
type Cache = Record<string, SessionResults>;
function readCache(): Cache {
  try {
    return JSON.parse(localStorage.getItem(CACHE_KEY) ?? "{}") ?? {};
  } catch {
    return {};
  }
}

export function cachedResults(start: string): SessionResults | null {
  return readCache()[Date.parse(start)] ?? null;
}

export function cacheResults(start: string, results: SessionResults) {
  const cache = readCache();
  cache[Date.parse(start)] = results;
  for (const key of Object.keys(cache))
    if (Number(key) < Date.now() - KEEP_MS) delete cache[key];
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch {}
}

export function lapTime(seconds: number) {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = (seconds % 60).toFixed(3).padStart(6, "0");
  return h ? `${h}:${String(m).padStart(2, "0")}:${s}` : `${m}:${s}`;
}

export function gapLabel(gap: ResultRow["gap"]) {
  if (typeof gap === "string") return gap;
  return gap ? `+${gap.toFixed(3)}` : "";
}
