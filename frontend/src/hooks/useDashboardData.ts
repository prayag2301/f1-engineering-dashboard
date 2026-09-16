"use client";

import { useEffect, useState } from "react";
import { readCatalog, readVersions } from "@/lib/archive";
import type { TeamKey } from "@/lib/releases";
import type { DashboardData } from "@/lib/dashboard";

export function useDashboardData() {
  const [data, setData] = useState<DashboardData | null>(null);
  const [error, setError] = useState("");
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setData(null);
    setError("");
    async function load() {
      const catalog = await readCatalog(controller.signal);
      const teams = Object.keys(catalog.teams) as TeamKey[];
      const releases = await Promise.all(
        teams.map((team) => readVersions(team, controller.signal)),
      );
      if (controller.signal.aborted) return;
      setData({
        catalog,
        versions: releases
          .flat()
          .filter((v) => v.status === "published")
          .sort((a, b) =>
            (b.published_at ?? b.as_of).localeCompare(
              a.published_at ?? a.as_of,
            ),
          ),
      });
    }
    load().catch((e) => {
      if (!controller.signal.aborted)
        setError(
          e instanceof Error ? e.message : "Unable to load dashboard data.",
        );
    });
    return () => controller.abort();
  }, [attempt]);
  return { data, error, retry: () => setAttempt((n) => n + 1) };
}
