import Link from "next/link";
import type { ReactNode } from "react";
import type { CarVersion, Catalog } from "@/lib/releases";
import { dateLabel } from "@/lib/releases";
import { changedComponents, releaseKind, teamName } from "@/lib/dashboard";

export function PageHeading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="d-page-heading">
      <div>
        <p className="eyebrow">{eyebrow}</p>
        <h1>{title}</h1>
        <p className="lede">{description}</p>
      </div>
      {children}
    </div>
  );
}

export function DataState({
  error,
  retry,
}: {
  error: string;
  retry: () => void;
}) {
  return error ? (
    <div className="notice error" role="alert">
      <span>{error}</span>
      <button onClick={retry}>Try again</button>
    </div>
  ) : (
    <div className="d-loading" role="status">
      <span className="d-loading-bar" />
      Loading engineering data…
    </div>
  );
}

export function EmptyState({
  title,
  children,
}: {
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="d-empty">
      <span className="d-empty-mark" aria-hidden="true">
        —
      </span>
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}

export function SectionHeading({
  number,
  title,
  href,
  action,
}: {
  number: string;
  title: string;
  href?: string;
  action?: string;
}) {
  return (
    <div className="d-section-heading">
      <h2>
        <span>{number}</span>
        {title}
      </h2>
      {href && (
        <Link className="text-link" href={href}>
          {action ?? "Explore"} ↗
        </Link>
      )}
    </div>
  );
}

export function ReleaseCard({
  version,
  catalog,
}: {
  version: CarVersion;
  catalog: Catalog;
}) {
  const components = changedComponents(version);
  return (
    <article
      className="d-release-row"
      style={
        {
          "--car-accent": catalog.teams[version.team_key].accent,
        } as React.CSSProperties
      }
    >
      <div className="d-release-date">
        <span>{version.published_at ? "PUBLISHED" : "CONFIGURATION"}</span>
        <time dateTime={version.published_at ?? version.as_of}>
          {dateLabel(version.published_at ?? version.as_of)}
        </time>
      </div>
      <div className="d-release-content">
        <div className="d-row-meta">
          <span className="d-team-label">
            <i />
            {teamName(version.team_key)}
          </span>
          <span className="d-badge">{releaseKind(version)}</span>
        </div>
        <h3>{version.label}</h3>
        <p className="d-small">
          {version.configuration_event} · Configuration of{" "}
          {dateLabel(version.as_of)}
        </p>
        <div className="d-tags">
          {components.map((key) => (
            <span key={key}>{version.manifest.components[key].label}</span>
          ))}
        </div>
        <details className="d-release-details">
          <summary>What changed &amp; supporting evidence</summary>
          <p>
            {version.notes ||
              "See the component notes and linked sources for this configuration."}
          </p>
          {version.manifest.changes.map((change) => (
            <div key={change.id} className="d-note">
              <span className="d-badge">
                {change.evidence_status} ·{" "}
                {change.representation === "modeled"
                  ? "Modeled"
                  : "Annotation only"}
              </span>
              <p>{change.summary}</p>
            </div>
          ))}
          {components.map((key) => (
            <div className="d-note" key={key}>
              <h4>{version.manifest.components[key].label}</h4>
              <p>{version.manifest.components[key].uncertainty}</p>
            </div>
          ))}
          <div className="d-inline-links">
            {version.manifest.sources.map((source) => (
              <a
                className="text-link"
                key={source.id}
                href={source.url}
                target="_blank"
                rel="noreferrer"
              >
                {source.title} ↗
              </a>
            ))}
          </div>
        </details>
      </div>
      <Link
        className="d-arrow-link"
        href={`/car/${version.team_key}`}
        aria-label={`Inspect ${teamName(version.team_key)} car`}
      >
        ↗
      </Link>
    </article>
  );
}
