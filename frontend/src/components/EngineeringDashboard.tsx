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
import {
  DataState,
  EmptyState,
  PageHeading,
  ReleaseCard,
  SectionHeading,
} from "./DashboardUI";

export default function EngineeringDashboard() {
  const { data, error, retry } = useDashboardData();
  const [team, setTeam] = useState<TeamKey>("ferrari");
  const [feedTeam, setFeedTeam] = useState("all");
  const car = data && currentVersion(data.versions, team);
  const info = data?.catalog.teams[team];
  const poster = car?.manifest.assets.preview_three_quarter;
  const feed =
    data?.versions.filter(
      (v) => feedTeam === "all" || v.team_key === feedTeam,
    ) ?? [];
  return (
    <div className="d-page">
      <PageHeading
        eyebrow="THE DEVELOPMENT DESK / 2026"
        title="Engineering dashboard."
        description="Inspect the cars. Compare the upgrades. Understand what changed."
      >
        <Link className="button" href="/compare">
          Compare cars <span aria-hidden="true">↗</span>
        </Link>
      </PageHeading>
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

          <section
            className="d-inspect-hero"
            style={{ "--car-accent": info?.accent } as React.CSSProperties}
            aria-label="Car inspection preview"
          >
            <div className="d-inspect-copy">
              <p className="eyebrow">01 / CAR EXPLORER</p>
              <h2>
                Closer to the car.
                <br />
                <span>Deeper into the detail.</span>
              </h2>
              <p>
                From the front wing to the floor edge, explore each assembly and
                the evidence behind its shape.
              </p>
              <Link className="button primary" href={`/car/${team}`}>
                Inspect {teamName(team)} in 3D{" "}
                <span aria-hidden="true">↗</span>
              </Link>
              <Link className="text-link" href="/models">
                Open car explorer →
              </Link>
              <div className="d-inspect-features">
                <span>360° inspection</span>
                <span>Component isolation</span>
                <span>Linked sources</span>
              </div>
            </div>
            <div className="d-car-preview">
              <div className="d-preview-top">
                <span className="d-badge">
                  {car ? "PUBLISHED RECONSTRUCTION" : "CAR PREVIEW"}
                </span>
                <div className="d-segmented" aria-label="Preview constructor">
                  {(Object.keys(data.catalog.teams) as TeamKey[]).map((key) => (
                    <button
                      key={key}
                      onClick={() => setTeam(key)}
                      aria-pressed={team === key}
                    >
                      {teamName(key)}
                    </button>
                  ))}
                </div>
              </div>
              {poster ? (
                <Link
                  href={`/car/${team}`}
                  className="d-poster-link"
                  aria-label={`Open ${teamName(team)} model`}
                >
                  {/* These are existing, reviewed model renders served by the archive. */}
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    key={poster.url}
                    src={poster.url}
                    alt={`${info?.car_name} exterior reconstruction, perspective view`}
                  />
                </Link>
              ) : (
                <EmptyState title="No published model yet">
                  The car will appear here when its first reviewed configuration
                  is published.
                </EmptyState>
              )}
              <div className="d-preview-bottom">
                <div>
                  <span>{info?.name}</span>
                  <strong>{info?.car_name}</strong>
                </div>
                <div>
                  <span>CONFIGURATION AS OF</span>
                  <b>{car ? dateLabel(car.as_of) : "Awaiting release"}</b>
                </div>
              </div>
            </div>
          </section>

          <div className="d-workspace-grid">
            <section>
              <SectionHeading
                number="02"
                title="Development log"
                href="/upgrades"
                action="All changes"
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
            <aside>
              <SectionHeading number="03" title="Engineering notebook" />
              <div className="d-notebook">
                <span className="d-notebook-icon" aria-hidden="true">
                  ↗
                </span>
                <p className="eyebrow">CONNECT SHAPE TO EVIDENCE</p>
                <h2>
                  What changed?
                  <br />
                  And how do we know?
                </h2>
                <p>
                  Follow a component from its visual reconstruction to the
                  original reference. Every detail has a level of certainty.
                </p>
                <Link className="text-link" href="/evidence">
                  Browse the evidence →
                </Link>
                <div className="d-notebook-rule" />
                <Link className="d-notebook-action" href="/analyze">
                  <span>
                    <strong>Decode an upgrade</strong>
                    <small>
                      Explore component signals and technical intent
                    </small>
                  </span>
                  ↗
                </Link>
                <Link className="d-notebook-action" href="/performance">
                  <span>
                    <strong>Track development</strong>
                    <small>
                      Compare activity and available performance data
                    </small>
                  </span>
                  ↗
                </Link>
              </div>
            </aside>
          </div>
          <section className="d-workflow">
            <div>
              <span className="eyebrow">YOUR NEXT QUESTION</span>
              <h2>Different shapes. Shared viewpoints.</h2>
              <p>
                Compare constructors or two configurations with synchronized
                cameras and component highlighting.
              </p>
            </div>
            <Link className="button" href="/compare">
              Start a comparison ↗
            </Link>
          </section>
        </>
      )}
    </div>
  );
}
