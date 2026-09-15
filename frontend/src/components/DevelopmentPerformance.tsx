"use client";

import { useState } from "react";
import Link from "next/link";
import { useDashboardData } from "@/hooks/useDashboardData";
import {
  changedComponents,
  currentVersion,
  teamName,
  upgradeCount,
} from "@/lib/dashboard";
import { dateLabel, type TeamKey } from "@/lib/releases";
import { DataState, PageHeading, SectionHeading } from "./DashboardUI";

export default function DevelopmentPerformance() {
  const { data, error, retry } = useDashboardData();
  const [metric, setMetric] = useState("releases");
  const teams = data ? (Object.keys(data.catalog.teams) as TeamKey[]) : [];
  const rows = teams.map((key) => {
    const releases = data!.versions.filter((v) => v.team_key === key);
    return {
      key,
      releases: releases.length,
      revisions: releases.reduce((n, v) => n + changedComponents(v).length, 0),
      reports: upgradeCount(releases),
    };
  });
  const value = (row: (typeof rows)[number]) =>
    metric === "releases" ? row.releases : row.revisions;
  const max = Math.max(1, ...rows.map(value));
  return (
    <div className="d-page">
      <PageHeading
        eyebrow="PERFORMANCE / DEVELOPMENT CONTEXT"
        title="Measure what the data supports."
        description="Compare development activity and keep observed changes separate from measured lap-time impact."
      />
      {!data ? (
        <DataState error={error} retry={retry} />
      ) : (
        <>
          <div className="d-performance-grid">
            <section>
              <SectionHeading number="01" title="Development activity" />
              <div className="d-panel d-chart-panel">
                <div className="d-segmented">
                  <button
                    aria-pressed={metric === "releases"}
                    onClick={() => setMetric("releases")}
                  >
                    Published releases
                  </button>
                  <button
                    aria-pressed={metric === "revisions"}
                    onClick={() => setMetric("revisions")}
                  >
                    Component revisions
                  </button>
                </div>
                <div
                  className="d-bar-chart"
                  role="img"
                  aria-label={`${metric === "releases" ? "Published releases" : "Component revisions"}: ${rows.map((row) => `${teamName(row.key)} ${value(row)}`).join(", ")}`}
                >
                  {rows.map((row) => (
                    <div className="d-chart-row" key={row.key}>
                      <div>
                        <span>{teamName(row.key)}</span>
                        <strong>{value(row)}</strong>
                      </div>
                      <div className="d-chart-track">
                        <span
                          style={{
                            width: `${(value(row) / max) * 100}%`,
                            background: data.catalog.teams[row.key].accent,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
                <p className="d-small">
                  {metric === "releases"
                    ? "Counts published car configurations, including launch references and reconstruction refinements."
                    : "Counts components marked as changed in each release. A component revised in two releases counts twice."}{" "}
                  This measures archive activity; it is not a ranking of
                  on-track development.
                </p>
              </div>
            </section>
            <section>
              <SectionHeading number="02" title="Lap-time impact" />
              <div className="d-timing-panel">
                <span className="d-badge">TIMING DATA UNAVAILABLE</span>
                <h2>
                  From a new shape
                  <br />
                  to a faster lap?
                </h2>
                <p>
                  The published archive does not include session timing or
                  controlled before-and-after measurements.
                </p>
                <div className="d-timing-values">
                  {["Practice delta", "Qualifying delta", "Race delta"].map(
                    (label) => (
                      <div key={label}>
                        <strong>
                          —<small>s / lap</small>
                        </strong>
                        <span>{label}</span>
                      </div>
                    ),
                  )}
                </div>
                <p className="d-small">
                  A lap-time claim needs comparable tyre, fuel, circuit and
                  weather conditions. Model geometry alone cannot establish a
                  performance gain.
                </p>
              </div>
            </section>
          </div>
          <SectionHeading
            number="03"
            title="Constructor comparison"
            href="/compare"
            action="Inspect differences"
          />
          <div className="d-table-wrap">
            <table className="d-table">
              <caption className="d-sr-only">
                Published development activity by constructor
              </caption>
              <thead>
                <tr>
                  <th>Constructor</th>
                  <th>Current reference date</th>
                  <th>Releases</th>
                  <th>Component revisions</th>
                  <th>Upgrade reports</th>
                  <th>Measured gain</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((row) => {
                  const current = currentVersion(data.versions, row.key);
                  return (
                    <tr key={row.key}>
                      <th>
                        <Link href={`/car/${row.key}`}>
                          {teamName(row.key)} ↗
                        </Link>
                      </th>
                      <td>
                        {current ? dateLabel(current.as_of) : "No release"}
                      </td>
                      <td>{row.releases}</td>
                      <td>{row.revisions}</td>
                      <td>{row.reports}</td>
                      <td className="d-small">Not measured</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
