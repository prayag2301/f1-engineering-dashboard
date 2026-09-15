"use client";

import { useState } from "react";
import Link from "next/link";
import { useDashboardData } from "@/hooks/useDashboardData";
import { currentVersion } from "@/lib/dashboard";
import { dateLabel, type TeamKey } from "@/lib/releases";
import {
  DataState,
  EmptyState,
  PageHeading,
  SectionHeading,
} from "./DashboardUI";

// Retain the constructor directory from main; model availability comes from the catalog.
const directory = [
  "Alpine",
  "Aston Martin",
  "Audi",
  "Cadillac",
  "Haas",
  "McLaren",
  "Racing Bulls",
  "Red Bull Racing",
  "Williams",
];

export default function TeamsDirectory() {
  const { data, error, retry } = useDashboardData();
  const [query, setQuery] = useState("");
  const [availableOnly, setAvailableOnly] = useState(false);
  const matches = (name: string) =>
    name.toLowerCase().includes(query.trim().toLowerCase());
  const teams = data
    ? (
        Object.entries(data.catalog.teams) as [
          TeamKey,
          (typeof data.catalog.teams)[TeamKey],
        ][]
      ).filter(
        ([key, info]) =>
          matches(info.name) &&
          (!availableOnly || currentVersion(data.versions, key)),
      )
    : [];
  const otherTeams = availableOnly ? [] : directory.filter(matches);
  return (
    <div className="d-page">
      <PageHeading
        eyebrow="CONSTRUCTOR DIRECTORY / 2026"
        title="Different teams. Different ideas."
        description="Explore the constructor grid and inspect the cars with published technical reconstructions."
      />
      <div className="d-filter-bar d-filter-bar-compact">
        <label>
          Find a constructor
          <input
            type="search"
            placeholder="Search teams…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </label>
        <label className="d-checkbox">
          <input
            type="checkbox"
            checked={availableOnly}
            onChange={(e) => setAvailableOnly(e.target.checked)}
          />
          Published models only
        </label>
      </div>
      {!data ? (
        <DataState error={error} retry={retry} />
      ) : (
        <>
          {teams.length > 0 && (
            <>
              <SectionHeading
                number="01"
                title="Ready to inspect"
                href="/compare"
                action="Compare cars"
              />
              <div className="d-team-grid">
                {teams.map(([key, info]) => {
                  const car = currentVersion(data.versions, key);
                  const poster = car?.manifest.assets.preview_side;
                  return (
                    <article
                      key={key}
                      className="d-team-card"
                      style={
                        { "--car-accent": info.accent } as React.CSSProperties
                      }
                    >
                      <div className="d-team-card-top">
                        <span className="d-team-label">
                          <i />
                          {info.name}
                        </span>
                        <span className="d-badge">
                          {car ? "MODEL AVAILABLE" : "AWAITING RELEASE"}
                        </span>
                      </div>
                      <Link
                        className="d-team-image"
                        href={`/car/${key}`}
                        aria-label={`Inspect ${info.name}`}
                      >
                        {poster ? (
                          <>
                            {/* eslint-disable-next-line @next/next/no-img-element */}
                            <img
                              src={poster.url}
                              alt={`${info.car_name} side profile`}
                              loading="lazy"
                            />
                          </>
                        ) : (
                          <span>No published render</span>
                        )}
                      </Link>
                      <div className="d-team-card-body">
                        <h2>{info.car_name}</h2>
                        <p>{info.notes}</p>
                        <dl className="d-key-values">
                          <div>
                            <dt>Configuration</dt>
                            <dd>
                              {car ? dateLabel(car.as_of) : "Not published"}
                            </dd>
                          </div>
                          <div>
                            <dt>Published releases</dt>
                            <dd>
                              {
                                data.versions.filter((v) => v.team_key === key)
                                  .length
                              }
                            </dd>
                          </div>
                        </dl>
                        <Link className="button" href={`/car/${key}`}>
                          Inspect car ↗
                        </Link>
                        <a
                          className="text-link"
                          href={info.source_url}
                          target="_blank"
                          rel="noreferrer"
                        >
                          Launch reference ↗
                        </a>
                      </div>
                    </article>
                  );
                })}
              </div>
            </>
          )}
          {otherTeams.length > 0 && (
            <>
              <SectionHeading number="02" title="Constructor directory" />
              <p className="d-section-note">
                These constructors are retained from the original dashboard
                directory. A reviewed 3D reconstruction is not yet available.
              </p>
              <div className="d-directory-grid">
                {otherTeams.map((name) => (
                  <article key={name}>
                    <span className="d-directory-monogram" aria-hidden="true">
                      {name
                        .replace(/[^A-Za-z]/g, "")
                        .slice(0, 3)
                        .toUpperCase()}
                    </span>
                    <h3>{name}</h3>
                    <span className="d-small">No published model</span>
                  </article>
                ))}
              </div>
            </>
          )}
          {!teams.length && !otherTeams.length && (
            <EmptyState title="No constructors found">
              Try a different team name or include constructors without
              published models.
            </EmptyState>
          )}
        </>
      )}
    </div>
  );
}
