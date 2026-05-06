"use client";

import { useState, useEffect } from "react";
import { getTeams } from "@/lib/api";

export interface Team {
  id: string;
  name: string;
  liveryKey: string;
  shortName: string;
  fullName: string;
  base: string | null;
  teamPrincipal: string | null;
  powerUnit: string | null;
}

const TEAM_NAME_TO_LIVERY: Record<string, string> = {
  "Red Bull":     "red-bull",
  Ferrari:        "ferrari",
  Mercedes:       "mercedes",
  McLaren:        "mclaren",
  "Aston Martin": "aston-martin",
  Alpine:         "alpine",
  Williams:       "williams",
  RB:             "racing-bulls",
  "Kick Sauber":  "audi",
  Haas:           "haas",
};

const SHORT_NAMES: Record<string, string> = {
  "Red Bull":     "RBR",
  Ferrari:        "FER",
  Mercedes:       "MER",
  McLaren:        "MCL",
  "Aston Martin": "AMR",
  Alpine:         "ALP",
  Williams:       "WIL",
  RB:             "RB",
  "Kick Sauber":  "AUD",
  Haas:           "HAA",
};

const STATIC_TEAMS: Team[] = Object.entries(TEAM_NAME_TO_LIVERY).map(
  ([name, liveryKey], idx) => ({
    id: String(idx + 1),
    name,
    liveryKey,
    shortName: SHORT_NAMES[name] ?? name.slice(0, 3).toUpperCase(),
    fullName: name,
    base: null,
    teamPrincipal: null,
    powerUnit: null,
  })
);

export function resolveTeamLiveryKey(teamName: string): string {
  return TEAM_NAME_TO_LIVERY[teamName] ?? "red-bull";
}

export function useCarModel() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    getTeams()
      .then((data) => {
        if (cancelled) return;
        const mapped: Team[] = data.map((t) => ({
          id: t.id,
          name: t.name,
          liveryKey: resolveTeamLiveryKey(t.name),
          shortName: SHORT_NAMES[t.name] ?? t.name.slice(0, 3).toUpperCase(),
          fullName: t.full_name,
          base: t.base ?? null,
          teamPrincipal: t.team_principal ?? null,
          powerUnit: t.power_unit ?? null,
        }));
        setTeams(mapped.length > 0 ? mapped : STATIC_TEAMS);
      })
      .catch(() => {
        if (cancelled) return;
        setError("Could not reach API — using static data");
        setTeams(STATIC_TEAMS);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, []);

  return { teams, loading, error };
}

/** Reverse-lookup: livery key → Team (from a pre-fetched list) */
export function findTeamByLiveryKey(teams: Team[], liveryKey: string): Team | undefined {
  return teams.find((t) => t.liveryKey === liveryKey);
}

export function findTeamByRouteParam(teams: Team[], routeParam: string): Team | undefined {
  return teams.find((t) => t.id === routeParam || t.liveryKey === routeParam);
}

export { TEAM_NAME_TO_LIVERY, SHORT_NAMES, STATIC_TEAMS };
