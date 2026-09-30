"use client";

import { useEffect, useState } from "react";
import {
  IDLE_POLL_MS,
  RACE_WEEK_POLL_MS,
  RateLimited,
  cachedSchedule,
  countdown,
  currentWeekend,
  fetchSchedule,
  localTime,
  nextPollDelay,
  sessionStatus,
  trackTime,
  type Schedule,
} from "@/lib/race-weekend";

const RETRY_COOLDOWN_MS = 10_000;

export default function RaceWeekend() {
  const [schedule, setSchedule] = useState<Schedule | null>(null);
  const [updating, setUpdating] = useState(false);
  const [now, setNow] = useState<number | null>(null);
  const [lastFetch, setLastFetch] = useState(0);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    setSchedule(cachedSchedule());
    setNow(Date.now());
    const tick = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(tick);
  }, []);

  useEffect(() => {
    const controller = new AbortController();
    let timer = 0;
    let failures = 0;
    let fetchedAt = 0;
    async function refresh() {
      clearTimeout(timer);
      fetchedAt = Date.now();
      setLastFetch(fetchedAt);
      let delay: number;
      try {
        const next = await fetchSchedule(controller.signal);
        setSchedule(next);
        setUpdating(false);
        failures = 0;
        delay = nextPollDelay(currentWeekend(next, Date.now()), Date.now());
      } catch (error) {
        if (controller.signal.aborted) return;
        setUpdating(true);
        failures += 1;
        delay = Math.min(
          IDLE_POLL_MS,
          error instanceof RateLimited
            ? error.retryAfterMs
            : RACE_WEEK_POLL_MS * 2 ** failures,
        );
      }
      // Hidden tabs skip polling; becoming visible catches up once.
      timer = window.setTimeout(() => {
        if (!document.hidden) refresh();
      }, delay);
    }
    function onVisible() {
      if (!document.hidden && Date.now() - fetchedAt > RACE_WEEK_POLL_MS)
        refresh();
    }
    refresh();
    document.addEventListener("visibilitychange", onVisible);
    return () => {
      controller.abort();
      clearTimeout(timer);
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, [attempt]);

  if (now === null) return null;
  const weekend = schedule && currentWeekend(schedule, now);
  const retry = (
    <button
      type="button"
      onClick={() => setAttempt((n) => n + 1)}
      disabled={now - lastFetch < RETRY_COOLDOWN_MS}
    >
      Retry
    </button>
  );

  if (!weekend)
    return (
      <section className="d-weekend" aria-label="Race weekend">
        <div className="d-weekend-updating" role="status">
          <span>
            {schedule
              ? "The 2026 season is complete."
              : "Still updating the race calendar…"}
          </span>
          {!schedule && retry}
        </div>
      </section>
    );

  const { meeting, sessions } = weekend;
  const live = sessions.find((s) => sessionStatus(s, now) === "live");
  const next = sessions.find((s) => sessionStatus(s, now) === "upcoming");
  return (
    <section className="d-weekend" aria-label="Race weekend">
      <div className="d-weekend-head">
        <div>
          <p className="eyebrow">
            {weekend.raceWeek ? "RACE WEEK" : "NEXT RACE"} · ROUND{" "}
            {String(weekend.round).padStart(2, "0")}
            {weekend.sprint && <span className="d-badge">SPRINT</span>}
          </p>
          <h2>{meeting.meeting_name}</h2>
          <p className="d-small">
            {meeting.circuit_short_name} · {meeting.country_name}
          </p>
        </div>
        <div className={`d-weekend-clock${live ? " is-live" : ""}`}>
          {live ? (
            <>
              <span>
                <i aria-hidden="true" /> LIVE · {live.session_name}
              </span>
              <strong>{countdown(Date.parse(live.date_end) - now)}</strong>
              <small>Scheduled to end</small>
            </>
          ) : next ? (
            <>
              <span>{next.session_name} starts in</span>
              <strong>{countdown(Date.parse(next.date_start) - now)}</strong>
              <small>{localTime(next.date_start)} your time</small>
            </>
          ) : (
            <>
              <span>Weekend complete</span>
              <strong>—</strong>
              <small>Next round appears after the race day</small>
            </>
          )}
        </div>
      </div>
      <ol className="d-weekend-sessions">
        {sessions.map((session) => {
          const status = sessionStatus(session, now);
          return (
            <li key={session.session_key} data-status={status}>
              <b>{session.session_name}</b>
              <span>
                {localTime(session.date_start)}
                <small>
                  {" "}
                  · {trackTime(session.date_start, session.gmt_offset)} track
                </small>
              </span>
              <em>{status}</em>
            </li>
          );
        })}
      </ol>
      <div className="d-weekend-foot">
        {updating ? (
          <span role="status">Still updating session times… {retry}</span>
        ) : (
          <span>
            Times from OpenF1 · refreshed{" "}
            {new Date(schedule.fetchedAt).toLocaleTimeString(undefined, {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        )}
      </div>
    </section>
  );
}
