"use client";

import { useEffect, useState } from "react";
import CarViewer, { type CameraBus } from "./CarViewer";
import { readVersions, readCatalog } from "@/lib/archive";
import {
  dateLabel,
  TEAM_NAMES,
  type CarVersion,
  type ViewName,
  type TeamKey,
} from "@/lib/releases";

export default function TeamComparison({
  version,
  preset,
  resetIndex,
  active,
  onSelect,
  focus,
  bus,
  neutral,
  isolate,
  comparisons,
}: {
  version: CarVersion | null;
  preset: ViewName;
  resetIndex: number;
  active: string | null;
  onSelect: (key: string) => void;
  focus: boolean;
  bus: CameraBus;
  neutral: boolean;
  isolate: boolean;
  comparisons?: CarVersion[];
}) {
  const primaryTeam = version?.team_key;
  const [releases, setReleases] = useState<CarVersion[]>([]);
  const [selected, setSelected] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [retry, setRetry] = useState(0);
  useEffect(() => {
    if (comparisons) {
      const available = comparisons.filter(
        (v) =>
          v.team_key !== primaryTeam &&
          ["building", "ready", "published"].includes(v.status) &&
          v.manifest.assets.glb,
      );
      setReleases(available);
      setSelected((previous) =>
        available.some((v) => v.id === previous)
          ? previous
          : ((
              available.find((v) => ["building", "ready"].includes(v.status)) ??
              available.find((v) => v.is_current) ??
              available[0]
            )?.id ?? ""),
      );
      setError("");
      setLoading(false);
      return;
    }
    const controller = new AbortController();
    setReleases([]);
    setSelected("");
    setLoading(true);
    setError("");
    readCatalog(controller.signal)
      .then((catalog) =>
        Promise.all(
          (Object.keys(catalog.teams) as TeamKey[])
            .filter((team) => team !== primaryTeam)
            .map((team) => readVersions(team, controller.signal)),
        ),
      )
      .then((groups) => groups.flat())
      .then((data) => {
        if (controller.signal.aborted) return;
        setReleases(data);
        setSelected((data.find((v) => v.is_current) ?? data[0])?.id ?? "");
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [primaryTeam, retry, comparisons]);
  const other =
    releases.find((v) => v.id === selected && v.team_key !== primaryTeam) ??
    null;
  return (
    <section
      className="team-comparison"
      aria-label="Constructor shape comparison"
    >
      <div className="comparison-intro">
        <strong>Two constructors. The same viewpoint.</strong>
        <p>
          Orbit either car to move both cameras. Select a detail below to
          inspect matching assemblies. Dates are shown separately; these are the
          selected reference configurations.
        </p>
      </div>
      <div className="comparison-grid">
        {[version, other].map((car, index) => (
          <div
            className="constructor-pane"
            key={index === 0 ? "primary" : "comparison"}
          >
            <div className="constructor-label">
              <strong>
                {car ? TEAM_NAMES[car.team_key] : "Choose a constructor"}
              </strong>
              {index === 1 && releases.length > 1 ? (
                <select
                  aria-label="Other constructor release"
                  value={selected}
                  onChange={(e) => setSelected(e.target.value)}
                >
                  {releases.map((v) => (
                    <option key={v.id} value={v.id}>
                      {TEAM_NAMES[v.team_key]} · {dateLabel(v.as_of)} —{" "}
                      {v.label}
                      {v.status !== "published" ? " (unpublished draft)" : ""}
                    </option>
                  ))}
                </select>
              ) : (
                <span>
                  {car ? `${dateLabel(car.as_of)} · ${car.label}` : ""}
                </span>
              )}
              {car && car.status !== "published" && (
                <small>Unpublished draft</small>
              )}
            </div>
            {index === 1 && (loading || error) ? (
              <div
                className="car-stage stage-skeleton"
                role={error ? "alert" : "status"}
              >
                {error ? (
                  <div>
                    {error}
                    <button onClick={() => setRetry((n) => n + 1)}>
                      Retry comparison
                    </button>
                  </div>
                ) : (
                  "Loading other constructor…"
                )}
              </div>
            ) : (
              <CarViewer
                version={car}
                preset={preset}
                resetIndex={resetIndex}
                activeComponent={active}
                onSelectComponent={onSelect}
                focus={focus}
                cameraBus={bus}
                syncId={`constructor-${index}`}
                neutral={neutral}
                isolate={isolate}
                height="490px"
              />
            )}
            {car && active && car.manifest.components[active] && (
              <div className="compared-detail">
                <strong>{car.manifest.components[active].label}</strong>
                <p>{car.manifest.components[active].uncertainty}</p>
                {car.manifest.sources
                  .filter((s) =>
                    car.manifest.components[active].source_ids.includes(s.id),
                  )
                  .map((s) => (
                    <a href={s.url} target="_blank" rel="noreferrer" key={s.id}>
                      View {TEAM_NAMES[car.team_key]} reference ↗
                    </a>
                  ))}
                <small>Evidence cutoff {dateLabel(car.evidence_cutoff)}</small>
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}
