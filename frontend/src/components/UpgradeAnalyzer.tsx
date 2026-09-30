"use client";

import { useState } from "react";
import Link from "next/link";
import { analyzeDescription } from "@/lib/upgrade-analysis";
import { useDashboardData } from "@/hooks/useDashboardData";
import { changedComponents, teamName } from "@/lib/dashboard";
import { EmptyState, PageHeading } from "./DashboardUI";

export default function UpgradeAnalyzer() {
  const [description, setDescription] = useState("");
  const [detail, setDetail] = useState("");
  const { data } = useDashboardData();
  // Constructors with a published change to an archive component.
  const teamsChanging = (component: string) => [
    ...new Set(
      data?.versions
        .filter(
          (v) =>
            changedComponents(v).includes(component) ||
            v.manifest.changes.some((c) => c.component === component),
        )
        .map((v) => teamName(v.team_key)),
    ),
  ];
  const [result, setResult] = useState<ReturnType<
    typeof analyzeDescription
  > | null>(null);
  function edit(setter: (value: string) => void, value: string) {
    setter(value);
    setResult(null);
  }
  return (
    <div className="d-page">
      <PageHeading
        eyebrow="ANALYZE / TECHNICAL READING ROOM"
        title="Decode the upgrade."
        description="Turn a technical description into component signals, possible design intent, and questions to investigate."
      />
      <div className="d-analyzer-layout">
        <form
          className="d-panel d-analyzer-form"
          onSubmit={(e) => {
            e.preventDefault();
            if (description.trim())
              setResult(analyzeDescription(description, detail));
          }}
        >
          <div className="d-section-heading">
            <h2>The observation</h2>
            <span className="d-badge">TEXT ANALYSIS</span>
          </div>
          <label htmlFor="upgrade-description">
            Upgrade description <span className="d-required">Required</span>
            <textarea
              id="upgrade-description"
              required
              rows={5}
              maxLength={10000}
              placeholder="Describe the component and what changed…"
              value={description}
              onChange={(e) => edit(setDescription, e.target.value)}
            />
          </label>
          <button
            className="d-example"
            type="button"
            onClick={() => {
              setDescription(
                "Revised front wing endplate geometry to alter outwash and improve downstream flow consistency.",
              );
              setDetail("");
              setResult(null);
            }}
          >
            Try a front-wing example ↗
          </button>
          <label htmlFor="technical-detail">
            Technical detail <span className="d-optional">Optional</span>
            <textarea
              id="technical-detail"
              rows={3}
              maxLength={10000}
              placeholder="Geometry, observations, or supporting measurements…"
              value={detail}
              onChange={(e) => edit(setDetail, e.target.value)}
            />
          </label>
          <button
            className="button primary"
            type="submit"
            disabled={!description.trim()}
          >
            Analyze upgrade <span aria-hidden="true">↗</span>
          </button>
          <p className="d-form-note">
            Interprets keywords in your text locally. It does not validate a
            claim or save an upgrade.
          </p>
        </form>
        <section
          className="d-analysis-output"
          aria-label="Analysis results"
          aria-live="polite"
        >
          <div className="d-section-heading">
            <h2>The interpretation</h2>
          </div>
          {result === null ? (
            <div className="d-analysis-intro">
              <span className="d-analysis-glyph" aria-hidden="true">
                [ ↗ ]
              </span>
              <h2>Start with an observation.</h2>
              <p>
                Paste an upgrade description or try the example. Explore the
                component, possible intent, and the evidence needed to assess
                it.
              </p>
              <div className="d-analysis-steps">
                <span>
                  01 <b>Identify the component</b>
                </span>
                <span>
                  02 <b>Explore the design intent</b>
                </span>
                <span>
                  03 <b>Check the supporting evidence</b>
                </span>
              </div>
              <Link href="/evidence" className="text-link">
                Find a source in the library →
              </Link>
            </div>
          ) : (
            <>
              <div className="d-analysis-notice">
                Rule-based interpretation · Possible effects, not confirmed
                gains.
              </div>
              {result.length ? (
                result.map((zone, i) => (
                  <article className="d-analysis-card" key={zone.label}>
                    <div className="d-row-meta">
                      <span className="d-badge">{zone.category}</span>
                      <span className="d-small">
                        {i === 0 ? "Closest text match" : "Related text match"}
                      </span>
                    </div>
                    <h2>{zone.label}</h2>
                    <div className="d-tags">
                      {zone.signals.map((signal) => (
                        <span key={signal}>{signal}</span>
                      ))}
                    </div>
                    <h3>Possible design intent</h3>
                    <p>{zone.intent}</p>
                    <h3>What to investigate</h3>
                    <p>{zone.check}</p>
                    {zone.component && data && (
                      <>
                        <h3>In the archive</h3>
                        <p>
                          {teamsChanging(zone.component).length
                            ? `Published changes: ${teamsChanging(zone.component).join(", ")}.`
                            : "No published changes to this part yet."}{" "}
                          <Link
                            className="text-link"
                            href={`/upgrades?component=${zone.component}`}
                          >
                            See changes →
                          </Link>{" "}
                          <Link
                            className="text-link"
                            href={`/evidence?component=${zone.component}`}
                          >
                            See sources →
                          </Link>
                        </p>
                      </>
                    )}
                  </article>
                ))
              ) : (
                <EmptyState title="No clear component signals">
                  Name a specific assembly, such as the front wing, suspension,
                  or cooling inlet, and describe the visible change.
                </EmptyState>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
