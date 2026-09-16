"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useDashboardData } from "@/hooks/useDashboardData";
import { changedComponents, teamName } from "@/lib/dashboard";
import type { TeamKey } from "@/lib/releases";
import { DataState, EmptyState, PageHeading, ReleaseCard } from "./DashboardUI";

export default function UpgradeBrowser() {
  const { data, error, retry } = useDashboardData();
  const [team, setTeam] = useState("all");
  const [component, setComponent] = useState("all");
  const [event, setEvent] = useState("all");
  const [kind, setKind] = useState("all");
  useEffect(() => {
    if (new URLSearchParams(window.location.search).get("type") === "reports")
      setKind("reports");
  }, []);
  const events = [
    ...new Set(
      data?.versions
        .filter((v) => team === "all" || v.team_key === team)
        .map((v) => v.configuration_event),
    ),
  ];
  const releases =
    data?.versions.filter(
      (v) =>
        (team === "all" || v.team_key === team) &&
        (event === "all" || v.configuration_event === event) &&
        (kind === "all" ||
          (kind === "reports"
            ? v.manifest.changes.length > 0
            : v.configuration_kind === kind)) &&
        (component === "all" ||
          changedComponents(v).includes(component) ||
          v.manifest.changes.some((c) => c.component === component)),
    ) ?? [];
  function reset() {
    setTeam("all");
    setComponent("all");
    setEvent("all");
    setKind("all");
  }
  return (
    <div className="d-page">
      <PageHeading
        eyebrow="DEVELOPMENT / CONFIGURATIONS & UPGRADES"
        title="Follow the changes."
        description="Trace component revisions, explore upgrade reports, and compare the car across configurations."
      >
        <Link href="/compare" className="button">
          Compare configurations ↗
        </Link>
      </PageHeading>
      {!data ? (
        <DataState error={error} retry={retry} />
      ) : (
        <>
          <div className="d-filter-bar">
            <label>
              Constructor
              <select
                value={team}
                onChange={(e) => {
                  setTeam(e.target.value);
                  setEvent("all");
                }}
              >
                <option value="all">All constructors</option>
                {(Object.keys(data.catalog.teams) as TeamKey[]).map((key) => (
                  <option key={key} value={key}>
                    {teamName(key)}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Component
              <select
                value={component}
                onChange={(e) => setComponent(e.target.value)}
              >
                <option value="all">All components</option>
                {Object.entries(data.catalog.components).map(([key, c]) => (
                  <option key={key} value={key}>
                    {c.label}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Event / configuration
              <select value={event} onChange={(e) => setEvent(e.target.value)}>
                <option value="all">All events</option>
                {events.map((name) => (
                  <option key={name}>{name}</option>
                ))}
              </select>
            </label>
            <label>
              Record type
              <select value={kind} onChange={(e) => setKind(e.target.value)}>
                <option value="all">All records</option>
                <option value="reports">With upgrade reports</option>
                <option value="reconstruction">Reconstruction updates</option>
                <option value="baseline">Launch references</option>
              </select>
            </label>
          </div>
          <div className="d-results-heading">
            <span role="status">{releases.length} configurations</span>
            <button onClick={reset}>Reset filters</button>
          </div>
          <div className="d-panel">
            {releases.length ? (
              releases.map((v) => (
                <ReleaseCard key={v.id} version={v} catalog={data.catalog} />
              ))
            ) : (
              <EmptyState title="No matching changes">
                {kind === "reports"
                  ? "No upgrade reports match these filters. Reconstruction updates remain available in the development log."
                  : "Try another constructor, component, or event to explore the available configurations."}
              </EmptyState>
            )}
          </div>
        </>
      )}
    </div>
  );
}
