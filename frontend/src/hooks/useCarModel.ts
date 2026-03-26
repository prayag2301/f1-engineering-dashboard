"use client";

import { useState, useEffect } from "react";

export interface Team {
  id: number;
  name: string;
  liveryKey: string;
  shortName: string;
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
    id: idx + 1,
    name,
    liveryKey,
    shortName: SHORT_NAMES[name] ?? name.slice(0, 3).toUpperCase(),
  })
);

export function useCarModel() {
  const [teams, setTeams] = useState<Team[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/v1/teams/", { signal: controller.signal })
      .then((r) => r.json())
      .then((data: Array<{ id: number; name: string }>) => {
        const mapped = data.map((t) => ({
          id: t.id,
          name: t.name,
          liveryKey: TEAM_NAME_TO_LIVERY[t.name] ?? "red-bull",
          shortName: SHORT_NAMES[t.name] ?? t.name.slice(0, 3).toUpperCase(),
        }));
        setTeams(mapped.length > 0 ? mapped : STATIC_TEAMS);
      })
      .catch(() => setTeams(STATIC_TEAMS))
      .finally(() => setLoading(false));
    return () => controller.abort();
  }, []);

  return { teams, loading };
}
