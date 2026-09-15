"use client";

import { useState } from "react";
import Link from "next/link";
import { useDashboardData } from "@/hooks/useDashboardData";
import { collectEvidence, teamName } from "@/lib/dashboard";
import { dateLabel, type TeamKey } from "@/lib/releases";
import { DataState, EmptyState, PageHeading } from "./DashboardUI";

export default function EvidenceBrowser() {
  const { data, error, retry } = useDashboardData();
  const [team, setTeam] = useState("all");
  const [component, setComponent] = useState("all");
  const [type, setType] = useState("all");
  const [query, setQuery] = useState("");
  const evidence = data ? collectEvidence(data.versions) : [];
  const types = [...new Set(evidence.map((e) => e.source.source_type))];
  // Apply constructor and component filters to the same release relationship.
  const filtered = evidence.filter(
    (entry) =>
      entry.versions.some(
        (version) =>
          (team === "all" || version.team_key === team) &&
          (component === "all" ||
            version.manifest.components[component]?.source_ids.includes(
              entry.source.id,
            ) ||
            version.manifest.changes.some(
              (c) =>
                c.component === component && c.source_id === entry.source.id,
            )),
      ) &&
      (type === "all" || entry.source.source_type === type) &&
      `${entry.source.title} ${entry.source.publisher}`
        .toLowerCase()
        .includes(query.trim().toLowerCase()),
  );
  function reset() {
    setTeam("all");
    setComponent("all");
    setType("all");
    setQuery("");
  }
  return (
    <div className="d-page">
      <PageHeading
        eyebrow="RESEARCH / SOURCE LIBRARY"
        title="Every detail has a source."
        description="Follow technical observations back to their references, component links, and dated configurations."
      />
      {!data ? (
        <DataState error={error} retry={retry} />
      ) : (
        <>
          <div className="d-filter-bar">
            <label>
              Search references
              <input
                type="search"
                placeholder="Title or publisher…"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
              />
            </label>
            <label>
              Constructor
              <select value={team} onChange={(e) => setTeam(e.target.value)}>
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
              Source type
              <select value={type} onChange={(e) => setType(e.target.value)}>
                <option value="all">All sources</option>
                {types.map((t) => (
                  <option key={t} value={t}>
                    {t.replaceAll("_", " ")}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <div className="d-results-heading">
            <span role="status">
              {filtered.length} of {evidence.length} references
            </span>
            <button onClick={reset}>Reset filters</button>
          </div>
          <div className="d-evidence-grid">
            {filtered.map((entry, index) => (
              <article className="d-evidence-card" key={entry.source.id}>
                <div className="d-row-meta">
                  <span className="d-reference-number">
                    REF / {String(index + 1).padStart(2, "0")}
                  </span>
                  <span className="d-badge">
                    {entry.source.source_type.replaceAll("_", " ")}
                  </span>
                </div>
                <h2>
                  <a href={entry.source.url} target="_blank" rel="noreferrer">
                    {entry.source.title} <span aria-hidden="true">↗</span>
                  </a>
                </h2>
                <p className="d-publisher">{entry.source.publisher}</p>
                <dl className="d-key-values">
                  <div>
                    <dt>Published</dt>
                    <dd>
                      {entry.source.published_at
                        ? dateLabel(entry.source.published_at)
                        : "Date not supplied"}
                    </dd>
                  </div>
                  <div>
                    <dt>Retrieved</dt>
                    <dd>{dateLabel(entry.source.retrieved_at)}</dd>
                  </div>
                </dl>
                <div className="d-tags">
                  {[...entry.teams].map((key) => (
                    <Link key={key} href={`/car/${key}`}>
                      {teamName(key)} ↗
                    </Link>
                  ))}
                  {[...entry.components].map((key) => (
                    <span key={key}>
                      {data.catalog.components[key]?.label ?? key}
                    </span>
                  ))}
                </div>
                <details>
                  <summary>Linked configurations &amp; media</summary>
                  <ul className="d-reference-versions">
                    {entry.versions.map((v) => (
                      <li key={v.id}>
                        {v.label}
                        <small>Configuration of {dateLabel(v.as_of)}</small>
                      </li>
                    ))}
                  </ul>
                  <div className="d-inline-links">
                    {entry.source.image_urls.map((url, i) => (
                      <a
                        key={`${url}-${i}`}
                        className="text-link"
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Reference image {i + 1} ↗
                      </a>
                    ))}
                  </div>
                  <p className="d-small">{entry.source.rights}</p>
                </details>
              </article>
            ))}
          </div>
          {!filtered.length && (
            <EmptyState title="No matching evidence">
              Try a broader search or reset the filters to see every published
              reference.
            </EmptyState>
          )}
        </>
      )}
    </div>
  );
}
