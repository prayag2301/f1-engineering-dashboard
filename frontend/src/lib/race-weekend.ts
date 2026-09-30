// Race-weekend schedule from OpenF1's free, CORS-enabled REST API.
// Free tier: 30 requests/minute and 3/second per client. One refresh costs two
// requests, so the fastest cadence (60 s) stays well inside that budget.
const API = "https://api.openf1.org/v1";
const CACHE_KEY = "f1-race-weekend";
export const SEASON = 2026;
export const RACE_WEEK_POLL_MS = 60_000;
export const IDLE_POLL_MS = 30 * 60_000;

export interface Meeting {
  meeting_key: number;
  meeting_name: string;
  location: string;
  country_name: string;
  circuit_short_name: string;
  gmt_offset: string;
  date_start: string;
  date_end: string;
  is_cancelled?: boolean;
}

export interface Session {
  session_key: number;
  session_name: string;
  meeting_key: number;
  date_start: string;
  date_end: string;
  gmt_offset: string;
  is_cancelled?: boolean;
}

export interface Schedule {
  meetings: Meeting[];
  sessions: Session[];
  fetchedAt: number;
}

export type SessionStatus = "upcoming" | "live" | "finished" | "cancelled";

export interface Weekend {
  meeting: Meeting;
  round: number;
  sprint: boolean;
  sessions: Session[];
  raceWeek: boolean;
}

export class RateLimited extends Error {
  constructor(public retryAfterMs: number) {
    super("OpenF1 rate limit reached.");
  }
}

const time = (iso: string) => new Date(iso).getTime();

export function sessionStatus(session: Session, now: number): SessionStatus {
  if (session.is_cancelled) return "cancelled";
  if (now < time(session.date_start)) return "upcoming";
  return now < time(session.date_end) ? "live" : "finished";
}

// The weekend stays current until 12 hours after its last session, then the
// next scheduled Grand Prix takes over. Testing and cancelled rounds are skipped.
export function currentWeekend(
  schedule: Pick<Schedule, "meetings" | "sessions">,
  now: number,
): Weekend | null {
  const races = schedule.meetings
    .filter((m) => !m.is_cancelled && !/testing/i.test(m.meeting_name))
    .sort((a, b) => time(a.date_start) - time(b.date_start));
  const index = races.findIndex((m) => time(m.date_end) + 12 * 3_600_000 > now);
  if (index < 0) return null;
  const meeting = races[index];
  const sessions = schedule.sessions
    .filter((s) => s.meeting_key === meeting.meeting_key)
    .sort((a, b) => time(a.date_start) - time(b.date_start));
  return {
    meeting,
    round: index + 1,
    sprint: sessions.some((s) => s.session_name === "Sprint"),
    sessions,
    // Race week runs from the Monday before the first session.
    raceWeek: now >= time(meeting.date_start) - 4 * 86_400_000,
  };
}

export function nextPollDelay(weekend: Weekend | null, now: number) {
  if (!weekend) return IDLE_POLL_MS;
  const start = time(weekend.meeting.date_start) - 86_400_000;
  return now >= start ? RACE_WEEK_POLL_MS : IDLE_POLL_MS;
}

async function getJSON<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API}/${path}`, { signal });
  if (response.status === 429) {
    const seconds = Number(response.headers.get("Retry-After"));
    throw new RateLimited(seconds > 0 ? seconds * 1000 : RACE_WEEK_POLL_MS * 2);
  }
  if (!response.ok) throw new Error(`OpenF1 responded ${response.status}.`);
  return response.json();
}

export async function fetchSchedule(signal?: AbortSignal): Promise<Schedule> {
  const [meetings, sessions] = await Promise.all([
    getJSON<Meeting[]>(`meetings?year=${SEASON}`, signal),
    getJSON<Session[]>(`sessions?year=${SEASON}`, signal),
  ]);
  if (!Array.isArray(meetings) || !Array.isArray(sessions))
    throw new Error("Unexpected OpenF1 response.");
  const schedule = { meetings, sessions, fetchedAt: Date.now() };
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(schedule));
  } catch {}
  return schedule;
}

// The schedule rarely changes, so the last good copy keeps the panel useful
// when OpenF1 is unreachable or rate-limited.
export function cachedSchedule(): Schedule | null {
  try {
    const value = JSON.parse(localStorage.getItem(CACHE_KEY) ?? "null");
    return value?.meetings && value?.sessions ? value : null;
  } catch {
    return null;
  }
}

function offsetMs(gmtOffset: string) {
  const [h, m] = gmtOffset.replace("-", "").split(":").map(Number);
  return (gmtOffset.startsWith("-") ? -1 : 1) * (h * 60 + (m || 0)) * 60_000;
}

export function localTime(iso: string) {
  return new Date(iso).toLocaleString(undefined, {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function trackTime(iso: string, gmtOffset: string) {
  return new Date(time(iso) + offsetMs(gmtOffset)).toLocaleString(undefined, {
    weekday: "short",
    hour: "2-digit",
    minute: "2-digit",
    timeZone: "UTC",
  });
}

export function countdown(ms: number) {
  const s = Math.max(0, Math.floor(ms / 1000));
  const d = Math.floor(s / 86_400);
  const h = Math.floor((s % 86_400) / 3600);
  const m = Math.floor((s % 3600) / 60);
  const pad = (n: number) => String(n).padStart(2, "0");
  const clock = `${pad(h)}:${pad(m)}:${pad(s % 60)}`;
  return d ? `${d}d ${clock}` : clock;
}

// Race day is the race's calendar date at the circuit, not in the viewer's zone.
export function isRaceDay(race: Session | undefined, now: number) {
  if (!race) return false;
  const day = (ms: number) =>
    new Date(ms + offsetMs(race.gmt_offset)).toISOString().slice(0, 10);
  return day(now) === day(time(race.date_start));
}
