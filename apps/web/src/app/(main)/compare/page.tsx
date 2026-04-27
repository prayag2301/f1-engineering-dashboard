"use client";

import { useMemo, useRef, useState } from "react";
import dynamic from "next/dynamic";
import { TEAM_LIVERIES, type HighlightMap } from "@/components/F1CarModel";
import { useCarModel, type Team } from "@/hooks/useCarModel";
import { useUpgrades } from "@/hooks/useUpgrades";
import { confidenceTier, CONFIDENCE_COLORS } from "@/lib/annotationAnchors";
import {
  createCameraSyncState,
  type CameraSyncState,
} from "@/components/CarViewer";

const CarViewer = dynamic(() => import("@/components/CarViewer"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        height: "100%",
        width: "100%",
        minHeight: 420,
        background: "#0a0a0a",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        color: "#666",
        fontFamily: "monospace",
        fontSize: "13px",
      }}
    >
      Loading 3D model…
    </div>
  ),
});

const DIFF_COLORS = {
  shared: "#8b5cf6",
  unique: "#22d3ee",
} as const;

function TeamPicker({
  teams,
  value,
  onChange,
  label,
}: {
  teams: Team[];
  value: string;
  onChange: (liveryKey: string) => void;
  label: string;
}) {
  return (
    <label
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "4px",
        fontFamily: "monospace",
        fontSize: "10px",
        color: "#888",
        letterSpacing: "1px",
        textTransform: "uppercase",
      }}
    >
      {label}
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{
          padding: "8px 10px",
          background: "#111",
          border: "1px solid #2a2a2a",
          borderRadius: "5px",
          color: "#e5e5e5",
          fontFamily: "monospace",
          fontSize: "12px",
          minWidth: "180px",
        }}
      >
        {teams.map((t) => (
          <option key={t.liveryKey} value={t.liveryKey}>
            {t.fullName}
          </option>
        ))}
      </select>
    </label>
  );
}

export default function ComparePage() {
  const { teams } = useCarModel();
  const [leftLivery, setLeftLivery] = useState("red-bull");
  const [rightLivery, setRightLivery] = useState("mercedes");
  const [showUpgrades, setShowUpgrades] = useState(true);
  const [diffMode, setDiffMode] = useState(true);
  const [drsOpen, setDrsOpen] = useState(false);

  const syncRef = useRef<CameraSyncState>(createCameraSyncState());

  const leftTeam = teams.find((t) => t.liveryKey === leftLivery);
  const rightTeam = teams.find((t) => t.liveryKey === rightLivery);

  const leftUpgrades = useUpgrades({ teamId: leftTeam?.id });
  const rightUpgrades = useUpgrades({ teamId: rightTeam?.id });

  const leftZones = useMemo(
    () =>
      new Set(
        leftUpgrades.upgrades
          .map((u) => u.component?.zone)
          .filter((z): z is string => Boolean(z)),
      ),
    [leftUpgrades.upgrades],
  );
  const rightZones = useMemo(
    () =>
      new Set(
        rightUpgrades.upgrades
          .map((u) => u.component?.zone)
          .filter((z): z is string => Boolean(z)),
      ),
    [rightUpgrades.upgrades],
  );

  const buildHighlights = (
    own: Set<string>,
    other: Set<string>,
    ownUpgrades: typeof leftUpgrades.upgrades,
  ): HighlightMap => {
    if (!showUpgrades) return {};
    const map: HighlightMap = {};
    for (const u of ownUpgrades) {
      const zone = u.component?.zone;
      if (!zone) continue;
      if (diffMode) {
        map[zone] = other.has(zone) ? DIFF_COLORS.shared : DIFF_COLORS.unique;
      } else {
        const tier = confidenceTier(u.confidence);
        const existing = map[zone];
        if (!existing || tier === "high") map[zone] = CONFIDENCE_COLORS[tier];
      }
    }
    return map;
  };

  const leftHighlights = useMemo(
    () => buildHighlights(leftZones, rightZones, leftUpgrades.upgrades),
    [leftZones, rightZones, leftUpgrades.upgrades, showUpgrades, diffMode],
  );
  const rightHighlights = useMemo(
    () => buildHighlights(rightZones, leftZones, rightUpgrades.upgrades),
    [leftZones, rightZones, rightUpgrades.upgrades, showUpgrades, diffMode],
  );

  const sharedZones = useMemo(
    () => Array.from(leftZones).filter((z) => rightZones.has(z)),
    [leftZones, rightZones],
  );
  const leftOnly = useMemo(
    () => Array.from(leftZones).filter((z) => !rightZones.has(z)),
    [leftZones, rightZones],
  );
  const rightOnly = useMemo(
    () => Array.from(rightZones).filter((z) => !leftZones.has(z)),
    [leftZones, rightZones],
  );

  const toggleStyle = (active: boolean): React.CSSProperties => ({
    padding: "6px 14px",
    background: active ? "#1f2937" : "#111",
    border: `1px solid ${active ? "#3b82f6" : "#2a2a2a"}`,
    borderRadius: "5px",
    color: active ? "#dbeafe" : "#aaa",
    fontFamily: "monospace",
    fontSize: "11px",
    letterSpacing: "1px",
    textTransform: "uppercase",
    cursor: "pointer",
  });

  return (
    <div>
      <div style={{ marginBottom: "20px" }}>
        <h1 className="page-title">Compare Cars</h1>
        <p className="page-subtitle">
          Side-by-side car comparison with synced camera. Upgrade zones are highlighted —
          shared vs unique colored differently in diff mode.
        </p>
      </div>

      <div
        style={{
          display: "flex",
          gap: "16px",
          flexWrap: "wrap",
          marginBottom: "16px",
          padding: "12px 16px",
          background: "#0d0d0d",
          border: "1px solid #1a1a1a",
          borderRadius: "8px",
          alignItems: "flex-end",
        }}
      >
        <TeamPicker teams={teams} value={leftLivery} onChange={setLeftLivery} label="Left car" />
        <TeamPicker teams={teams} value={rightLivery} onChange={setRightLivery} label="Right car" />
        <div style={{ display: "flex", gap: "8px", marginLeft: "auto", flexWrap: "wrap" }}>
          <button
            type="button"
            style={toggleStyle(showUpgrades)}
            onClick={() => setShowUpgrades((v) => !v)}
          >
            {showUpgrades ? "Upgrades on" : "Upgrades off"}
          </button>
          <button
            type="button"
            style={toggleStyle(diffMode)}
            onClick={() => setDiffMode((v) => !v)}
            disabled={!showUpgrades}
          >
            {diffMode ? "Diff colors" : "Confidence colors"}
          </button>
          <button
            type="button"
            style={toggleStyle(drsOpen)}
            onClick={() => setDrsOpen((v) => !v)}
          >
            DRS {drsOpen ? "open" : "closed"}
          </button>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: "12px",
          marginBottom: "16px",
        }}
      >
        {[
          { team: leftTeam, livery: leftLivery, highlights: leftHighlights, syncId: "left" },
          { team: rightTeam, livery: rightLivery, highlights: rightHighlights, syncId: "right" },
        ].map((side) => {
          const livery = TEAM_LIVERIES[side.livery] ?? TEAM_LIVERIES["red-bull"];
          return (
            <div
              key={side.syncId}
              style={{
                borderRadius: "8px",
                overflow: "hidden",
                border: "1px solid #1a1a1a",
                borderLeft: `3px solid ${livery.primary}`,
              }}
            >
              <div
                style={{
                  padding: "10px 14px",
                  background: "#0d0d0d",
                  borderBottom: "1px solid #1a1a1a",
                  fontFamily: "monospace",
                  fontSize: "12px",
                  color: "#e5e5e5",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                }}
              >
                <span>{side.team?.fullName ?? side.livery}</span>
                <span style={{ color: "#666", fontSize: "10px", letterSpacing: "1px", textTransform: "uppercase" }}>
                  {side.syncId}
                </span>
              </div>
              <CarViewer
                teamId={side.livery}
                height="540px"
                quality="medium"
                drsOpen={drsOpen}
                highlightedZones={side.highlights}
                syncRef={syncRef}
                syncId={side.syncId}
              />
            </div>
          );
        })}
      </div>

      {showUpgrades && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
            gap: "12px",
          }}
        >
          <DiffPanel title="Shared zones" zones={sharedZones} color={DIFF_COLORS.shared} emptyLabel="No overlapping upgrade zones" />
          <DiffPanel title={`${leftTeam?.shortName ?? "Left"} only`} zones={leftOnly} color={DIFF_COLORS.unique} emptyLabel="No unique upgrades" />
          <DiffPanel title={`${rightTeam?.shortName ?? "Right"} only`} zones={rightOnly} color={DIFF_COLORS.unique} emptyLabel="No unique upgrades" />
        </div>
      )}
    </div>
  );
}

function DiffPanel({
  title,
  zones,
  color,
  emptyLabel,
}: {
  title: string;
  zones: string[];
  color: string;
  emptyLabel: string;
}) {
  return (
    <div
      style={{
        padding: "12px 16px",
        background: "#0d0d0d",
        border: "1px solid #1a1a1a",
        borderRadius: "8px",
      }}
    >
      <div
        style={{
          fontFamily: "monospace",
          fontSize: "10px",
          letterSpacing: "1px",
          textTransform: "uppercase",
          color: "#888",
          marginBottom: "8px",
        }}
      >
        {title}
      </div>
      {zones.length === 0 ? (
        <div style={{ fontFamily: "monospace", fontSize: "11px", color: "#555" }}>{emptyLabel}</div>
      ) : (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
          {zones.map((z) => (
            <span
              key={z}
              style={{
                padding: "3px 8px",
                background: `${color}22`,
                border: `1px solid ${color}55`,
                borderRadius: "4px",
                color: "#e5e5e5",
                fontFamily: "monospace",
                fontSize: "11px",
              }}
            >
              {z}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
