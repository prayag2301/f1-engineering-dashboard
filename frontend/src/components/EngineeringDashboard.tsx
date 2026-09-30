"use client";

import { useState } from "react";
import Link from "next/link";
import { useDashboardData } from "@/hooks/useDashboardData";
import {
  collectEvidence,
  currentVersion,
  teamName,
  upgradeCount,
} from "@/lib/dashboard";
import { dateLabel, type TeamKey } from "@/lib/releases";
import RaceWeekend from "./RaceWeekend";
import Standings from "./Standings";
import {
  DataState,
  EmptyState,
  PageHeading,
  ReleaseCard,
  SectionHeading,
} from "./DashboardUI";

export default function EngineeringDashboard() {
  const { data, error, retry } = useDashboardData();
  const [feedTeam, setFeedTeam] = useState("all");
  const [meetings, setMeetings] = useState<string[]>([]);
  // Configurations observed at the current or previous Grand Prix.
  const fromWeekend = meetings
    .map((name) => ({
      name,
      versions:
        data?.versions.filter(
          (v) => v.configuration_event.split(" / ")[0] === name,
        ) ?? [],
    }))
    .find((m) => m.versions.length);
  const feed =
    data?.versions.filter(
      (v) => feedTeam === "all" || v.team_key === feedTeam,
    ) ?? [];
  return (
    <div className="d-page">
      <PageHeading
        eyebrow="RACE WEEK / 2026"
        title="Race week."
        description="Session times for the current Grand Prix, every car on the grid and the latest published changes."
      >
        <Link className="button" href="/compare">
          Compare cars <span aria-hidden="true">↗</span>
        </Link>
      </PageHeading>
      <RaceWeekend onMeetings={setMeetings} />
      <Standings
        accents={Object.fromEntries(
          Object.entries(data?.catalog.teams ?? {}).map(([key, info]) => [
            key,
            info.accent,
          ]),
        )}
      />
      {!data ? (
        <DataState error={error} retry={retry} />
      ) : (
        <>
          <div className="d-stats" aria-label="Dashboard summary">
            {[
              [
                (Object.keys(data.catalog.teams) as TeamKey[]).filter((key) =>
                  currentVersion(data.versions, key),
                ).length,
                "Cars to inspect",
                "Published reconstructions",
                "/teams",
              ],
              [
                data.versions.length,
                "Car configurations",
                "Trace the development history",
                "/upgrades",
              ],
              [
                upgradeCount(data.versions),
                "Upgrade reports",
                "Linked to published releases",
                "/upgrades?type=reports",
              ],
              [
                collectEvidence(data.versions).length,
                "Source references",
                "Explore the supporting evidence",
                "/evidence",
              ],
            ].map(([value, label, note, href]) => (
              <Link key={label} className="d-stat" href={String(href)}>
                <span className="d-stat-top">
                  {label}
                  <span aria-hidden="true">↗</span>
                </span>
                <strong>{String(value).padStart(2, "0")}</strong>
                <small>{note}</small>
              </Link>
            ))}
          </div>

          <section aria-label="The grid">
            <SectionHeading title="The grid" href="/teams" action="All teams" />
            <div className="d-grid-cars">
              {(Object.keys(data.catalog.teams) as TeamKey[]).map((key) => {
                const info = data.catalog.teams[key];
                const car = currentVersion(data.versions, key);
                const poster = car?.manifest.assets.preview_three_quarter;
                return (
                  <Link
                    key={key}
                    href={`/car/${key}`}
                    className="d-grid-car"
                    style={
                      { "--car-accent": info.accent } as React.CSSProperties
                    }
                    aria-label={`Inspect ${teamName(key)} ${info.car_name} in 3D`}
                  >
                    {poster ? (
                      // Existing, reviewed model renders served by the archive.
                      // eslint-disable-next-line @next/next/no-img-element
                      <img src={poster.url} alt="" loading="lazy" />
                    ) : (
                      <span className="d-grid-car-empty">Awaiting model</span>
                    )}
                    <span className="d-team-label">
                      <i />
                      {teamName(key)}
                    </span>
                    <strong>{info.car_name}</strong>
                    <small>
                      {car ? `As of ${dateLabel(car.as_of)}` : "No release yet"}
                    </small>
                  </Link>
                );
              })}
            </div>
          </section>

          {fromWeekend && (
            <section
              className="d-log"
              aria-label={`Changes from the ${fromWeekend.name}`}
            >
              <SectionHeading
                title={`From the ${fromWeekend.name}`}
                href={`/upgrades?event=${encodeURIComponent(fromWeekend.versions[0].configuration_event)}`}
                action={`All ${fromWeekend.versions.length}`}
              />
              <div className="d-panel">
                {fromWeekend.versions.slice(0, 3).map((version) => (
                  <ReleaseCard
                    key={version.id}
                    version={version}
                    catalog={data.catalog}
                  />
                ))}
              </div>
            </section>
          )}

          <div className="d-log">
            <section>
              <SectionHeading
                title="Latest changes"
                href="/upgrades"
                action="Full change log"
              />
              <div className="d-panel">
                <div className="d-panel-toolbar">
                  <p>Latest published configurations</p>
                  <label className="d-inline-filter">
                    <span className="d-sr-only">
                      Filter development log by team
                    </span>
                    <select
                      value={feedTeam}
                      onChange={(e) => setFeedTeam(e.target.value)}
                    >
                      <option value="all">All constructors</option>
                      {(Object.keys(data.catalog.teams) as TeamKey[]).map(
                        (key) => (
                          <option key={key} value={key}>
                            {teamName(key)}
                          </option>
                        ),
                      )}
                    </select>
                  </label>
                </div>
                {feed.slice(0, 3).map((version) => (
                  <ReleaseCard
                    key={version.id}
                    version={version}
                    catalog={data.catalog}
                  />
                ))}
                {!feed.length && (
                  <EmptyState title="The development log is empty">
                    Published configurations will appear here with their
                    component notes and sources.
                  </EmptyState>
                )}
                <div className="d-panel-foot">
                  Configuration dates describe the observed car. Publication
                  dates track updates to its reconstruction.
                </div>
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}
