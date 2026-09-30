import { TEAM_NAMES, type TeamKey } from "./releases";

// Championship standings from Jolpica (the Ergast successor): free, CORS-enabled,
// 500 requests/hour per client. Standings only change after a sprint or race, so
// one refresh (two requests) per hour keeps them current within the hour.
const API = "https://api.jolpi.ca/ergast/f1";
const CACHE_KEY = "f1-standings";
export const STANDINGS_TTL_MS = 60 * 60_000;

export interface Standing {
  position: number;
  points: number;
  wins: number;
  name: string;
  team: string;
  teamKey?: TeamKey;
  code?: string;
}

export interface Standings {
  season: string;
  round: number;
  drivers: Standing[];
  constructors: Standing[];
  fetchedAt: number;
}

interface Constructor {
  constructorId: string;
  name: string;
}
interface StandingsTable<T> {
  MRData: {
    StandingsTable: {
      season: string;
      StandingsLists: ({ round: string } & T)[];
    };
  };
}
type DriverTable = StandingsTable<{
  DriverStandings: {
    position?: string;
    points: string;
    wins: string;
    Driver: { givenName: string; familyName: string; code?: string };
    Constructors: Constructor[];
  }[];
}>;
type ConstructorTable = StandingsTable<{
  ConstructorStandings: {
    position?: string;
    points: string;
    wins: string;
    Constructor: Constructor;
  }[];
}>;

function teamKey(id: string): TeamKey | undefined {
  const key = id === "rb" ? "racing_bulls" : id;
  return key in TEAM_NAMES ? (key as TeamKey) : undefined;
}

export function parseStandings(
  drivers: DriverTable,
  constructors: ConstructorTable,
  fetchedAt: number,
): Standings {
  const d = drivers.MRData.StandingsTable;
  const c = constructors.MRData.StandingsTable;
  const dList = d.StandingsLists[0];
  const cList = c.StandingsLists[0];
  return {
    season: d.season,
    round: Number(dList?.round ?? 0),
    drivers: (dList?.DriverStandings ?? []).map((s, i) => {
      // A driver who changed teams is listed with their latest constructor.
      const team = s.Constructors[s.Constructors.length - 1];
      return {
        position: Number(s.position ?? i + 1),
        points: Number(s.points),
        wins: Number(s.wins),
        name: `${s.Driver.givenName} ${s.Driver.familyName}`,
        code: s.Driver.code,
        team: team?.name ?? "",
        teamKey: team && teamKey(team.constructorId),
      };
    }),
    constructors: (cList?.ConstructorStandings ?? []).map((s, i) => ({
      position: Number(s.position ?? i + 1),
      points: Number(s.points),
      wins: Number(s.wins),
      name: s.Constructor.name,
      team: s.Constructor.name,
      teamKey: teamKey(s.Constructor.constructorId),
    })),
    fetchedAt,
  };
}

async function getJSON<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`${API}/${path}`, { signal });
  if (!response.ok) throw new Error(`Jolpica responded ${response.status}.`);
  return response.json();
}

export async function fetchStandings(
  season: number,
  signal?: AbortSignal,
): Promise<Standings> {
  const [drivers, constructors] = await Promise.all([
    getJSON<DriverTable>(`${season}/driverstandings/`, signal),
    getJSON<ConstructorTable>(`${season}/constructorstandings/`, signal),
  ]);
  const standings = parseStandings(drivers, constructors, Date.now());
  try {
    localStorage.setItem(CACHE_KEY, JSON.stringify(standings));
  } catch {}
  return standings;
}

export function cachedStandings(): Standings | null {
  try {
    const value = JSON.parse(localStorage.getItem(CACHE_KEY) ?? "null");
    return value?.drivers && value?.constructors ? value : null;
  } catch {
    return null;
  }
}
