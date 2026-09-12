"use client";

import { useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import {
  dateLabel,
  type CarVersion,
  type Catalog,
  type TeamKey,
  type ViewName,
} from "@/lib/releases";
import { readCatalog, readVersions, staticArchive } from "@/lib/archive";
import { createCameraBus } from "./CarViewer";

const CarViewer = dynamic(() => import("./CarViewer"), {
  ssr: false,
  loading: () => (
    <div className="car-stage stage-skeleton" role="status">
      Preparing viewer…
    </div>
  ),
});
const VIEWS: [ViewName, string][] = [
  ["three_quarter", "Perspective"],
  ["front", "Front"],
  ["side", "Side"],
  ["rear", "Rear"],
];

export default function ReleaseExplorer({
  initialTeam = "ferrari",
  initialCompare = false,
}: {
  initialTeam?: TeamKey;
  initialCompare?: boolean;
}) {
  const [team, setTeam] = useState<TeamKey>(initialTeam);
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [versions, setVersions] = useState<CarVersion[]>([]);
  const [selected, setSelected] = useState("");
  const [before, setBefore] = useState("");
  const [compare, setCompare] = useState(initialCompare);
  const [preset, setPreset] = useState<ViewName>("three_quarter");
  const [resetIndex, setResetIndex] = useState(0);
  const [active, setActive] = useState<string | null>(null);
  const [focus, setFocus] = useState(false);
  const [singleCompare, setSingleCompare] = useState(false);
  const [showBefore, setShowBefore] = useState(false);
  const [highlight, setHighlight] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(0);
  // Each constructor starts with an independent orbit history.
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const bus = useMemo(() => createCameraBus(), [team]);
  useEffect(() => {
    const controller = new AbortController();
    readCatalog(controller.signal)
      .then(setCatalog)
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      });
    return () => controller.abort();
  }, [retry]);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError("");
    setVersions([]);
    setSelected("");
    setBefore("");
    setActive(null);
    setFocus(false);
    readVersions(team, controller.signal)
      .then((data) => {
        if (controller.signal.aborted) return;
        setVersions(data);
        const current = data.find((v) => v.is_current) ?? data[0];
        setSelected(current?.id ?? "");
        setBefore(current?.parent_id ?? data[1]?.id ?? current?.id ?? "");
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError(e.message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [team, retry]);
  const version =
    versions.find((v) => v.id === selected && v.team_key === team) ?? null;
  const previous =
    versions.find((v) => v.id === before && v.team_key === team) ?? null;
  const info = catalog?.teams[team];
  const changed = useMemo(() => {
    if (!version) return [];
    return Object.keys(version.manifest.components).filter((key) =>
      compare && previous
        ? version.manifest.component_hashes?.[key] !==
          previous.manifest.component_hashes?.[key]
        : version.manifest.components[key].changed,
    );
  }, [version, previous, compare]);
  const component = active ? version?.manifest.components[active] : null;
  const changes =
    version?.manifest.changes.filter(
      (c) => !active || c.component === active,
    ) ?? [];
  const sources =
    version?.manifest.sources.filter(
      (s) =>
        !component ||
        component.source_ids.includes(s.id) ||
        changes.some((c) => c.source_id === s.id),
    ) ?? [];
  return (
    <div
      className="release-explorer"
      style={
        { "--team-accent": info?.accent ?? "#e52d3a" } as React.CSSProperties
      }
    >
      <div className="explorer-heading">
        <div>
          <p className="eyebrow">2026 / PUBLIC REFERENCE ARCHIVE</p>
          <h1>
            The car. <span>The changes.</span>
          </h1>
          <p className="lede">
            Explore the surfaces. Trace the evidence. See how the car evolves.
          </p>
        </div>
        <div className="archive-mark">
          <span>F1</span>
          <small>
            ENGINEERING
            <br />
            OBSERVATORY
          </small>
        </div>
      </div>
      <div className="team-tabs" role="tablist" aria-label="Constructor">
        {(["ferrari", "mercedes"] as TeamKey[]).map((key) => (
          <button
            role="tab"
            aria-selected={team === key}
            tabIndex={team === key ? 0 : -1}
            data-team={key}
            key={key}
            onKeyDown={(event) => {
              if (
                ["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)
              ) {
                event.preventDefault();
                const next =
                  event.key === "Home"
                    ? "ferrari"
                    : event.key === "End"
                      ? "mercedes"
                      : team === "ferrari"
                        ? "mercedes"
                        : "ferrari";
                setTeam(next);
                (
                  event.currentTarget.parentElement?.querySelector(
                    `[data-team="${next}"]`,
                  ) as HTMLButtonElement | null
                )?.focus();
              }
            }}
            onClick={() => setTeam(key)}
            className={team === key ? "team-tab active" : "team-tab"}
          >
            <span className={`team-dot ${key}`} />
            <span>
              {catalog?.teams[key]?.name ??
                (key === "ferrari"
                  ? "Scuderia Ferrari"
                  : "Mercedes-AMG PETRONAS")}
            </span>
            <small>{key === "ferrari" ? "SF-26" : "W17"}</small>
          </button>
        ))}
      </div>
      {error && (
        <div className="notice error" role="alert">
          {error}
          <button onClick={() => setRetry((n) => n + 1)}>Try again</button>
        </div>
      )}
      <div className="explorer-toolbar">
        <div className="toolbar-title">
          <span
            className="team-dot"
            style={{ background: "var(--team-accent)" }}
          />
          <strong>
            {info?.car_name ?? (team === "ferrari" ? "SF-26" : "W17")}
          </strong>
          <span>
            {version
              ? dateLabel(version.as_of)
              : loading
                ? "Loading archive…"
                : "No published release"}
          </span>
          {version?.is_current && (
            <span className="status-tag">Current release</span>
          )}
        </div>
        <div className="toolbar-controls">
          <button
            className={compare ? "selected" : ""}
            aria-pressed={compare}
            disabled={versions.length < 2}
            onClick={() => setCompare((v) => !v)}
          >
            Compare releases
          </button>
          <button
            className={highlight ? "selected" : ""}
            aria-pressed={highlight}
            onClick={() => setHighlight((v) => !v)}
            disabled={!version}
          >
            Highlight changes
          </button>
        </div>
      </div>
      <div
        className={`explorer-body ${compare && versions.length > 1 ? "is-comparing" : ""}`}
      >
        <div className="viewer-column">
          {compare && versions.length > 1 ? (
            <div>
              <div className="comparison-mode">
                <button
                  aria-pressed={singleCompare}
                  onClick={() => setSingleCompare((v) => !v)}
                >
                  {singleCompare
                    ? "Show side by side"
                    : "Use before / after switch"}
                </button>
                {singleCompare && (
                  <button onClick={() => setShowBefore((v) => !v)}>
                    {showBefore
                      ? "Showing before · switch to after"
                      : "Showing after · switch to before"}
                  </button>
                )}
              </div>
              <div
                className="comparison-grid"
                style={
                  singleCompare ? { gridTemplateColumns: "1fr" } : undefined
                }
              >
                <div
                  style={
                    singleCompare && !showBefore
                      ? { display: "none" }
                      : undefined
                  }
                >
                  <label className="compare-select">
                    Before
                    <select
                      value={before}
                      onChange={(e) => setBefore(e.target.value)}
                    >
                      {versions.map((v) => (
                        <option value={v.id} key={v.id}>
                          {dateLabel(v.as_of)} — {v.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <CarViewer
                    version={previous}
                    preset={preset}
                    resetIndex={resetIndex}
                    activeComponent={active}
                    onSelectComponent={setActive}
                    highlighted={highlight ? changed : []}
                    focus={focus}
                    cameraBus={bus}
                    syncId="before"
                    height="560px"
                  />
                </div>
                <div
                  style={
                    singleCompare && showBefore
                      ? { display: "none" }
                      : undefined
                  }
                >
                  <label className="compare-select">
                    After
                    <select
                      value={selected}
                      onChange={(e) => setSelected(e.target.value)}
                    >
                      {versions.map((v) => (
                        <option value={v.id} key={v.id}>
                          {dateLabel(v.as_of)} — {v.label}
                        </option>
                      ))}
                    </select>
                  </label>
                  <CarViewer
                    version={version}
                    preset={preset}
                    resetIndex={resetIndex}
                    activeComponent={active}
                    onSelectComponent={setActive}
                    highlighted={highlight ? changed : []}
                    focus={focus}
                    cameraBus={bus}
                    syncId="after"
                    height="560px"
                  />
                </div>
              </div>
            </div>
          ) : loading ? (
            <div className="car-stage stage-skeleton" role="status">
              Loading release archive…
            </div>
          ) : (
            <CarViewer
              version={version}
              cameraBus={bus}
              syncId="single"
              preset={preset}
              resetIndex={resetIndex}
              activeComponent={active}
              onSelectComponent={setActive}
              highlighted={highlight ? changed : []}
              focus={focus}
            />
          )}
          <div className="view-bar">
            <div role="group" aria-label="Camera preset">
              {VIEWS.map(([key, label]) => (
                <button
                  key={key}
                  aria-pressed={preset === key && !focus}
                  className={preset === key && !focus ? "selected" : ""}
                  onClick={() => {
                    setPreset(key);
                    setResetIndex((index) => index + 1);
                    setFocus(false);
                  }}
                >
                  {label}
                </button>
              ))}
            </div>
            <label className="focus-toggle">
              <input
                type="checkbox"
                checked={focus}
                disabled={!active}
                onChange={(e) => setFocus(e.target.checked)}
              />{" "}
              Focus selection
            </label>
          </div>
          <div className="timeline">
            <div className="section-label">
              RELEASE HISTORY{" "}
              <span>{versions.length.toString().padStart(2, "0")}</span>
            </div>
            {versions.length === 0 ? (
              <p>
                Reviewed versions will appear here. The launch references remain
                drafts until approved.
              </p>
            ) : (
              <div className="timeline-items">
                {[...versions].reverse().map((v) => (
                  <button
                    className={
                      v.id === selected
                        ? "timeline-item active"
                        : "timeline-item"
                    }
                    key={v.id}
                    aria-pressed={v.id === selected}
                    onClick={() => {
                      setSelected(v.id);
                      setActive(null);
                    }}
                  >
                    <span className="timeline-node" />
                    <small>{dateLabel(v.as_of)}</small>
                    <strong>{v.label}</strong>
                    <span>{v.configuration_event}</span>
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
        <aside className="inspection-panel">
          <div className="section-label">
            INSPECT THE CAR <span>↗</span>
          </div>
          <label className="component-picker">
            Component
            <select
              aria-label="Component"
              value={active ?? ""}
              onChange={(e) => setActive(e.target.value || null)}
            >
              <option value="">Complete car</option>
              {Object.entries(catalog?.components ?? {}).map(([key, value]) => (
                <option key={key} value={key}>
                  {value.label}
                </option>
              ))}
            </select>
          </label>
          <h2>
            {component?.label ??
              version?.configuration_event ??
              "An archive built on evidence"}
          </h2>
          {version ? (
            <>
              <p className="muted">
                Configuration observed {dateLabel(version.as_of)}. Evidence
                cutoff {dateLabel(version.evidence_cutoff)}.
              </p>
              {component && (
                <p className="uncertainty">{component.uncertainty}</p>
              )}
              <div className="section-label">
                THIS RELEASE <span>{changes.length}</span>
              </div>
              {changes.length === 0 ? (
                <p className="empty-detail">
                  {version.parent_id
                    ? "No newly reported change for this selection."
                    : "Baseline exterior reconstruction. Individual component dimensions remain estimates unless a source specifies them."}
                </p>
              ) : (
                changes.map((change) => (
                  <article className="change-card" key={change.id}>
                    <span
                      className={`evidence-badge ${change.representation === "modeled" ? "modeled" : "reported"}`}
                    >
                      {change.representation === "modeled"
                        ? "Modeled change"
                        : "Reported · shape unavailable"}
                    </span>
                    <h3>{change.summary}</h3>
                    <p>{change.review_notes}</p>
                    <details>
                      <summary>Supporting evidence</summary>
                      <p>{change.supporting_passage}</p>
                      {change.page && <small>Source page {change.page}</small>}
                    </details>
                  </article>
                ))
              )}
              {version.manifest.no_new_modeled_change && (
                <p className="notice">
                  No new modeled change established. Geometry is carried forward
                  from the previous release.
                </p>
              )}
              <div className="section-label">
                SOURCES <span>{sources.length}</span>
              </div>
              <div className="source-list">
                {sources.map((source) => (
                  <a
                    href={source.url}
                    target="_blank"
                    rel="noreferrer"
                    key={source.id}
                  >
                    <small>
                      {source.publisher}
                      {source.published_at
                        ? ` / ${dateLabel(source.published_at)}`
                        : " / publication date unavailable"}
                    </small>
                    <span>{source.title} ↗</span>
                  </a>
                ))}
              </div>
              {version.manifest.assets[`render_${preset}`] && (
                <a
                  className="button download-button"
                  href={version.manifest.assets[`render_${preset}`].url}
                  download={`${team}-${version.as_of.slice(0, 10)}-${preset}.png`}
                  target="_blank"
                  rel="noreferrer"
                >
                  Download 4K studio render <span>↓</span>
                </a>
              )}
            </>
          ) : (
            <>
              <p className="muted">
                Every published version connects a complete car configuration to
                dated references.
              </p>
              <div className="archive-explainer">
                <span>01 / Observe</span>
                <p>
                  Team photography and technical reports establish what is
                  visible.
                </p>
                <span>02 / Reconstruct</span>
                <p>Supported shape changes become editable car components.</p>
                <span>03 / Review</span>
                <p>
                  Compare all four views before a release enters this archive.
                </p>
              </div>
              <Link
                href={staticArchive ? "/about" : "/review"}
                className="text-link"
              >
                {staticArchive
                  ? "How releases are reviewed ↗"
                  : "Open the review studio ↗"}
              </Link>
            </>
          )}
        </aside>
      </div>
      <footer className="explorer-footer">
        <span>Independent exterior reconstructions from public sources.</span>
        <span>Hidden geometry and uncited dimensions remain estimates.</span>
      </footer>
    </div>
  );
}
