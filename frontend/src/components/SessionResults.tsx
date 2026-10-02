"use client";

import { useEffect, useState } from "react";
import {
  RACE_WEEK_POLL_MS,
  sessionStatus,
  type Session,
} from "@/lib/race-weekend";
import {
  cacheResults,
  cachedResults,
  fetchResults,
  gapLabel,
  lapTime,
  type SessionResults as Results,
} from "@/lib/session-results";

// Provisional classifications and penalties land in the hour after the flag.
const SETTLE_MS = 60 * 60_000;
// Sessions are matched on start time: Jolpica's fallback keys are not OpenF1's.
const id = (s: Session) => Date.parse(s.date_start);

export default function SessionResults({
  sessions,
  now,
  locked,
}: {
  sessions: Session[];
  now: number;
  // The schedule came from Jolpica because OpenF1 is locked for a live session.
  locked: boolean;
}) {
  const started = sessions.filter((s) =>
    ["live", "finished"].includes(sessionStatus(s, now)),
  );
  const [picked, setPicked] = useState<number | null>(null);
  const [results, setResults] = useState<Results | null>(null);
  const [failed, setFailed] = useState(false);
  const selected =
    started.find((s) => id(s) === picked) ?? started[started.length - 1];
  const key = selected?.session_key;
  const start = selected?.date_start;
  const settling =
    !!selected && now < Date.parse(selected.date_end) + SETTLE_MS;

  useEffect(() => {
    if (!start) return;
    setResults(cachedResults(start));
    setFailed(false);
    if (locked) return;
    const controller = new AbortController();
    let failures = 0;
    let timer = 0;
    async function load() {
      let delay = settling ? RACE_WEEK_POLL_MS : 0;
      try {
        const next = await fetchResults(key!, controller.signal);
        if (next.rows.length) {
          setResults(next);
          cacheResults(start!, next);
        }
        setFailed(false);
        failures = 0;
      } catch {
        if (controller.signal.aborted) return;
        setFailed(true);
        // Rate limits clear within seconds; a locked live session takes longer.
        delay = Math.min(RACE_WEEK_POLL_MS, 2000 * 2 ** failures++);
      }
      if (delay) timer = window.setTimeout(load, delay);
    }
    // ponytail: fixed stagger behind the schedule's requests; retries cover collisions.
    timer = window.setTimeout(load, 1500);
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [key, start, locked, settling]);

  if (!selected) return null;
  const live = sessionStatus(selected, now) === "live";
  const quali = results?.rows.some((r) => r.times.length > 1);
  const race = /^(Race|Sprint)$/.test(selected.session_name);
  const q = selected.session_name.startsWith("Sprint") ? "SQ" : "Q";
  return (
    <div className="d-results" role="region" aria-label="Session results">
      <div className="d-results-tabs">
        {started.map((s) => (
          <button
            type="button"
            key={id(s)}
            aria-pressed={s === selected}
            onClick={() => setPicked(id(s))}
          >
            {s.session_name}
            {sessionStatus(s, now) === "live" && " · Live"}
          </button>
        ))}
      </div>
      {!results ? (
        <p role="status">
          {locked || (live && failed)
            ? "OpenF1 locks timing to subscribers while a session is live. The classification appears here when it ends."
            : failed
              ? "Still updating the classification…"
              : "Waiting for OpenF1 to publish the classification…"}
        </p>
      ) : (
        <>
          <div className="d-table-wrap">
            <table className="d-table d-standings-table">
              <caption className="d-sr-only">
                {selected.session_name} classification
              </caption>
              <thead>
                <tr>
                  <th scope="col">Pos</th>
                  <th scope="col">Driver</th>
                  {quali ? (
                    [1, 2, 3].map((n) => (
                      <th scope="col" key={n}>
                        {q}
                        {n}
                      </th>
                    ))
                  ) : (
                    <th scope="col">{race ? "Time" : "Best lap"}</th>
                  )}
                  {!quali && !race && <th scope="col">Gap</th>}
                  <th scope="col">Laps</th>
                  {race && <th scope="col">Pts</th>}
                </tr>
              </thead>
              <tbody>
                {results.rows.map((row) => (
                  <tr key={row.code}>
                    <td>{row.position ?? "—"}</td>
                    <td
                      style={
                        { "--car-accent": row.colour } as React.CSSProperties
                      }
                    >
                      <span className="d-team-label">
                        <i />
                        {row.name}
                      </span>
                      <small>{row.team}</small>
                    </td>
                    {quali ? (
                      [0, 1, 2].map((n) => (
                        <td key={n}>
                          {row.times[n] ? lapTime(row.times[n]!) : ""}
                        </td>
                      ))
                    ) : (
                      <td>
                        {row.status ??
                          (race && row.position !== 1
                            ? gapLabel(row.gap)
                            : row.times[0]
                              ? lapTime(row.times[0])
                              : "")}
                      </td>
                    )}
                    {!quali && !race && <td>{gapLabel(row.gap)}</td>}
                    <td>{row.laps}</td>
                    {race && <td>{row.points ?? ""}</td>}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p>
            {locked
              ? "OpenF1 is locked while a session is live, so this is the last classification loaded"
              : failed
                ? "Still updating the classification"
                : live
                  ? "Live from OpenF1"
                  : "Classification from OpenF1"}{" "}
            · refreshed{" "}
            {new Date(results.fetchedAt).toLocaleTimeString(undefined, {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </p>
        </>
      )}
    </div>
  );
}
