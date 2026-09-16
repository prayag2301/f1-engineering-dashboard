"use client";

import { useState } from "react";
import Link from "next/link";
import { analyzeDescription } from "@/lib/upgrade-analysis";
import { EmptyState, PageHeading } from "./DashboardUI";

export default function UpgradeAnalyzer() {
  const [description, setDescription] = useState("");
  const [detail, setDetail] = useState("");
  const [effect, setEffect] = useState("");
  const [source, setSource] = useState("");
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
            <h2>
              <span>01</span>The observation
            </h2>
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
              setEffect("");
              setSource("");
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
          <div className="d-form-row">
            <label htmlFor="expected-effect">
              Claimed effect <span className="d-optional">Optional</span>
              <input
                id="expected-effect"
                placeholder="e.g. More stable front balance"
                value={effect}
                onChange={(e) => edit(setEffect, e.target.value)}
              />
            </label>
            <label htmlFor="source-reference">
              Source <span className="d-optional">Optional</span>
              <input
                id="source-reference"
                placeholder="Publisher or reference URL"
                value={source}
                onChange={(e) => edit(setSource, e.target.value)}
              />
            </label>
          </div>
          <button
            className="button primary"
            type="submit"
            disabled={!description.trim()}
          >
            Analyze upgrade <span aria-hidden="true">↗</span>
          </button>
          <p className="d-form-note">
            Interprets keywords in your text locally. It does not fetch the
            source, validate a claim, or save an upgrade.
          </p>
        </form>
        <section
          className="d-analysis-output"
          aria-label="Analysis results"
          aria-live="polite"
        >
          <div className="d-section-heading">
            <h2>
              <span>02</span>The interpretation
            </h2>
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
                  </article>
                ))
              ) : (
                <EmptyState title="No clear component signals">
                  Name a specific assembly, such as the front wing, suspension,
                  or cooling inlet, and describe the visible change.
                </EmptyState>
              )}
              {(effect || source) && (
                <div className="d-analysis-card">
                  <h3>Your context</h3>
                  {effect && (
                    <p>
                      <span className="d-small">
                        CLAIMED EFFECT · UNVERIFIED
                      </span>
                      <br />
                      {effect}
                    </p>
                  )}
                  {source && (
                    <p>
                      <span className="d-small">
                        SOURCE PROVIDED · NOT CHECKED
                      </span>
                      <br />
                      {source}
                    </p>
                  )}
                </div>
              )}
            </>
          )}
        </section>
      </div>
    </div>
  );
}
