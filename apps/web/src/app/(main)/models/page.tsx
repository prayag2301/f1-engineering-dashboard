"use client";

import dynamic from "next/dynamic";
import { useState } from "react";

const ModelViewer = dynamic(
  () => import("@/components/ModelViewer").then((m) => m.ModelViewer),
  { ssr: false, loading: () => <div className="loading">Loading viewer…</div> }
);

const COMPONENTS = [
  {
    id: "front_wing",
    label: "Front Wing",
    season: 2026,
    meshes: ["mainplane", "flap_1", "flap_2", "endplate × 2"],
    description:
      "Parametric front wing generated from FIA 2026 regulation constraints. " +
      "Mainplane spans the full 1.8 m width allowance; two flap elements are " +
      "stacked within the 400 mm height envelope. Each element is a named mesh " +
      "node for annotation targeting in Phase 3.",
  },
];

export default function ModelsPage() {
  const [selected, setSelected] = useState(COMPONENTS[0]);
  const [viewerKey, setViewerKey] = useState(0);
  const [regenerating, setRegenerating] = useState(false);

  const glbUrl = `/api/v1/models/${selected.id}/${selected.season}.glb`;

  async function handleRegenerate() {
    setRegenerating(true);
    await fetch(
      `/api/v1/models/${selected.id}/${selected.season}/generate`,
      { method: "POST" }
    );
    // Give the background task ~2 s then reload the viewer
    setTimeout(() => {
      setViewerKey((k) => k + 1);
      setRegenerating(false);
    }, 2000);
  }

  return (
    <>
      <h1 className="page-title">Parametric Models</h1>
      <p className="page-subtitle">
        3D car components generated directly from FIA {selected.season} regulation
        constraints stored in the database.
      </p>

      <div className="filters-row">
        {COMPONENTS.map((c) => (
          <button
            key={c.id}
            className={`filter-btn${selected.id === c.id ? " filter-btn--active" : ""}`}
            onClick={() => setSelected(c)}
          >
            {c.label}
          </button>
        ))}
        <button
          className="filter-btn"
          onClick={handleRegenerate}
          disabled={regenerating}
          style={{ marginLeft: "auto", opacity: regenerating ? 0.5 : 1 }}
        >
          {regenerating ? "Regenerating…" : "Regenerate"}
        </button>
      </div>

      <div style={{ marginTop: 24 }}>
        <ModelViewer key={viewerKey} url={glbUrl} height={520} />
      </div>

      <div className="card" style={{ marginTop: 16 }}>
        <div className="card__header">
          <span className="card__team">{selected.label}</span>
          <span className="card__race">Season {selected.season}</span>
        </div>
        <p className="card__description">{selected.description}</p>
        <div className="card__meta">
          {selected.meshes.map((m) => (
            <span key={m} className="badge badge--confidence">
              {m}
            </span>
          ))}
        </div>
        <div className="card__meta" style={{ marginTop: 8 }}>
          <a
            className="filter-btn"
            href={glbUrl}
            target="_blank"
            rel="noreferrer"
          >
            Download .glb
          </a>
        </div>
      </div>
    </>
  );
}
