"use client";

import { useEffect, useState } from "react";
import { getUpgrades, type Upgrade } from "@/lib/api";

export function useUpgrades(params: { teamId?: string; raceId?: string } = {}) {
  const [upgrades, setUpgrades] = useState<Upgrade[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const { teamId, raceId } = params;

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    getUpgrades({ team_id: teamId, race_id: raceId })
      .then((data) => {
        if (cancelled) return;
        setUpgrades(data);
      })
      .catch((e) => {
        if (cancelled) return;
        setError(e instanceof Error ? e.message : "Failed to load upgrades");
        setUpgrades([]);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => { cancelled = true; };
  }, [teamId, raceId]);

  return { upgrades, loading, error };
}
