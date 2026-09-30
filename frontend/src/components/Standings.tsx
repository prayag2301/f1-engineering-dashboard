"use client";

import { useEffect, useState } from "react";
import { SEASON } from "@/lib/race-weekend";
import {
  STANDINGS_TTL_MS,
  cachedStandings,
  fetchStandings,
  type Standing,
  type Standings as StandingsData,
} from "@/lib/standings";
import type { TeamKey } from "@/lib/releases";

const CHECK_MS = 5 * 60_000;
const TOP = 10;

export default function Standings({
  accents = {},
}: {
  accents?: Partial<Record<TeamKey, string>>;
}) {
  const [standings, setStandings] = useState<StandingsData | null>(null);
  const [updating, setUpdating] = useState(false);
  const [loading, setLoading] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const cached = cachedStandings();
    let fetchedAt = cached?.fetchedAt ?? 0;
    if (cached) setStandings(cached);
    async function refresh() {
      fetchedAt = Date.now();
      setLoading(true);
      try {
        setStandings(await fetchStandings(SEASON, controller.signal));
        setUpdating(false);
      } catch {
        if (controller.signal.aborted) return;
        setUpdating(true);
        // Try again at the next check rather than waiting a full hour.
        fetchedAt = Date.now() - STANDINGS_TTL_MS + CHECK_MS;
      } finally {
        if (!controller.signal.aborted) setLoading(false);
      }
    }
    // Refresh when the copy is over an hour old; hidden tabs wait until shown.
    function check() {
      if (!document.hidden && Date.now() - fetchedAt >= STANDINGS_TTL_MS)
        refresh();
    }
    if (attempt) refresh();
    else check();
    const timer = setInterval(check, CHECK_MS);
    document.addEventListener("visibilitychange", check);
    return () => {
      controller.abort();
      clearInterval(timer);
      document.removeEventListener("visibilitychange", check);
    };
  }, [attempt]);

  const retry = (
    <button
      type="button"
      onClick={() => setAttempt((n) => n + 1)}
      disabled={loading}
    >
      Retry
    </button>
  );
  const table = (rows: Standing[], label: string, driver: boolean) => (
    <table className="d-table d-standings-table">
      <caption className="d-sr-only">{label}</caption>
      <thead>
        <tr>
          <th scope="col">Pos</th>
          <th scope="col">{driver ? "Driver" : "Team"}</th>
          <th scope="col">Wins</th>
          <th scope="col">Pts</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => (
          <tr key={`${row.position}-${row.name}`}>
            <td>{row.position}</td>
            <td
              style={
                {
                  "--car-accent": row.teamKey && accents[row.teamKey],
                } as React.CSSProperties
              }
            >
              <span className="d-team-label">
                <i />
                {row.name}
              </span>
              {driver && <small>{row.team}</small>}
            </td>
            <td>{row.wins}</td>
            <td>
              <b>{row.points}</b>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );

  return (
    <section className="d-standings" aria-label="Championship standings">
      <div className="d-section-heading">
        <h2>Championship</h2>
        {standings && (
          <span className="d-small">
            {standings.season} · after round{" "}
            {String(standings.round).padStart(2, "0")}
          </span>
        )}
      </div>
      {!standings ? (
        <div className="d-weekend d-weekend-updating" role="status">
          <span>Still updating the standings…</span>
          {!loading && retry}
        </div>
      ) : (
        <>
          <div className="d-standings-grid">
            <div className="d-table-wrap">
              {table(
                standings.drivers.slice(0, TOP),
                "Drivers' championship",
                true,
              )}
              {standings.drivers.length > TOP && (
                <details>
                  <summary>Show all {standings.drivers.length} drivers</summary>
                  {table(
                    standings.drivers.slice(TOP),
                    "Drivers' championship, continued",
                    true,
                  )}
                </details>
              )}
            </div>
            <div className="d-table-wrap">
              {table(
                standings.constructors,
                "Constructors' championship",
                false,
              )}
            </div>
          </div>
          <p className="d-standings-foot">
            {updating ? (
              <span role="status">Still updating the standings… {retry}</span>
            ) : (
              <span>
                Standings from Jolpica · refreshed{" "}
                {new Date(standings.fetchedAt).toLocaleTimeString(undefined, {
                  hour: "2-digit",
                  minute: "2-digit",
                })}
              </span>
            )}
          </p>
        </>
      )}
    </section>
  );
}
