"use client";

import { useState } from "react";
import { previewUpgradeIntelligence, IS_DEMO, type UpgradeIntelligencePreview } from "@/lib/api";
import ComingSoon from "@/components/ComingSoon";

export default function AnalyzePage() {
  if (IS_DEMO) {
    return (
      <>
        <h1 className="page-title">Analyze</h1>
        <p className="page-subtitle">
          Run live upgrade intelligence inference on a free-text description.
        </p>
        <ComingSoon feature="Upgrade analyzer" />
      </>
    );
  }
  return <AnalyzePageInner />;
}

function AnalyzePageInner() {
  const [description, setDescription] = useState("");
  const [technicalDetail, setTechnicalDetail] = useState("");
  const [expectedEffect, setExpectedEffect] = useState("");
  const [source, setSource] = useState("");
  const [result, setResult] = useState<UpgradeIntelligencePreview | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (!description.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const preview = await previewUpgradeIntelligence({
        description: description.trim(),
        technical_detail: technicalDetail.trim() || undefined,
        expected_effect: expectedEffect.trim() || undefined,
        source: source.trim() || undefined,
      });
      setResult(preview);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }

  const confidencePct = result ? Math.round(result.confidence * 100) : 0;

  return (
    <>
      <h1 className="page-title">Intelligence Analyzer</h1>
      <p className="page-subtitle">
        Paste any upgrade description to get instant category classification,
        component zone detection, and engineering reasoning.
      </p>

      <div className="analyze-layout">
        <form className="analyze-form" onSubmit={handleSubmit}>
          <div className="analyze-field">
            <label className="analyze-label" htmlFor="description">
              Description <span className="analyze-required">*</span>
            </label>
            <textarea
              id="description"
              className="analyze-textarea"
              rows={4}
              placeholder="e.g. Revised front wing endplate geometry to improve outwash vortex stability…"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              required
            />
          </div>

          <div className="analyze-field">
            <label className="analyze-label" htmlFor="technical-detail">
              Technical Detail <span className="analyze-optional">(optional)</span>
            </label>
            <textarea
              id="technical-detail"
              className="analyze-textarea"
              rows={3}
              placeholder="CFD data, geometry specs, material changes…"
              value={technicalDetail}
              onChange={(e) => setTechnicalDetail(e.target.value)}
            />
          </div>

          <div className="analyze-row">
            <div className="analyze-field">
              <label className="analyze-label" htmlFor="expected-effect">
                Expected Effect <span className="analyze-optional">(optional)</span>
              </label>
              <input
                id="expected-effect"
                className="analyze-input"
                type="text"
                placeholder="e.g. +0.15s/lap in high-speed corners"
                value={expectedEffect}
                onChange={(e) => setExpectedEffect(e.target.value)}
              />
            </div>
            <div className="analyze-field">
              <label className="analyze-label" htmlFor="source">
                Source <span className="analyze-optional">(optional)</span>
              </label>
              <input
                id="source"
                className="analyze-input"
                type="text"
                placeholder="e.g. autosport.com"
                value={source}
                onChange={(e) => setSource(e.target.value)}
              />
            </div>
          </div>

          <button
            type="submit"
            className="analyze-submit"
            disabled={loading || !description.trim()}
          >
            {loading ? "Analyzing…" : "Analyze Upgrade"}
          </button>
        </form>

        {error && (
          <div className="analyze-error">
            {error}
            <br />
            <small>Make sure the backend is running.</small>
          </div>
        )}

        {result && (
          <div className="analyze-result">
            <div className="analyze-result__header">
              <div className="analyze-result__badges">
                <span className="analyze-result__label">Category</span>
                <span className={`badge badge--${result.inferred_category.toLowerCase().replace(" ", "-")}`}>
                  {result.inferred_category}
                </span>
              </div>
              <div className="analyze-result__badges">
                <span className="analyze-result__label">Zone</span>
                <span className="badge badge--confidence">{result.inferred_component_zone}</span>
              </div>
              <div className="analyze-result__confidence">
                <span className="analyze-result__label">Confidence</span>
                <div className="confidence-bar">
                  <div
                    className="confidence-bar__fill"
                    style={{ width: `${confidencePct}%` }}
                  />
                </div>
                <span className="confidence-bar__value">{confidencePct}%</span>
              </div>
            </div>

            {result.signals.length > 0 && (
              <div className="analyze-result__section">
                <h3 className="analyze-result__section-title">Matched Signals</h3>
                <div className="analyze-result__signals">
                  {result.signals.map((signal) => (
                    <span key={signal} className="badge badge--confidence">
                      {signal}
                    </span>
                  ))}
                </div>
              </div>
            )}

            <div className="analyze-result__section">
              <h3 className="analyze-result__section-title">Aero Reasoning</h3>
              <p className="analyze-result__text">{result.aero_reasoning}</p>
            </div>

            <div className="analyze-result__section">
              <h3 className="analyze-result__section-title">Mechanical Reasoning</h3>
              <p className="analyze-result__text">{result.mechanical_reasoning}</p>
            </div>

            <div className="analyze-result__section">
              <h3 className="analyze-result__section-title">Performance Hypothesis</h3>
              <p className="analyze-result__text">{result.performance_hypothesis}</p>
            </div>
          </div>
        )}
      </div>
    </>
  );
}
