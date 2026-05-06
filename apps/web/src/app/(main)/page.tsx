"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { TEAM_LIVERIES } from "@/components/F1CarModel";
import { useCarModel } from "@/hooks/useCarModel";
import TeamSelector from "@/components/TeamSelector";

const CarViewer = dynamic(() => import("@/components/CarViewer"), {
  ssr: false,
  loading: () => (
    <div style={{
      height: "600px",
      background: "#0a0a0a",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      color: "#444",
      fontFamily: "monospace",
      fontSize: "13px",
      borderRadius: "8px",
      border: "1px solid #1a1a1a",
    }}>
      Initialising 3D renderer…
    </div>
  ),
});

export default function Home() {
  const [activeTeamId, setActiveTeamId] = useState("red-bull");
  const { teams, loading, error } = useCarModel();

  const activeLivery = TEAM_LIVERIES[activeTeamId] ?? TEAM_LIVERIES["red-bull"];
  const activeTeam = teams.find((t) => t.liveryKey === activeTeamId);

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 className="page-title">3D Car Viewer</h1>
        <p className="page-subtitle">
          Procedural F1 car models — 2026 regulations. Select a constructor below.
        </p>
        {error && (
          <p style={{
            fontFamily: "monospace", fontSize: "11px", color: "#f59e0b",
            marginTop: "8px", padding: "6px 12px",
            background: "#f59e0b18", border: "1px solid #f59e0b33", borderRadius: "4px",
          }}>
            {error}
          </p>
        )}
      </div>

      {/* 3D Viewer */}
      <div style={{ marginBottom: "20px", borderRadius: "8px", overflow: "hidden", border: "1px solid #1a1a1a" }}>
        <CarViewer teamId={activeTeamId} height="600px" />
      </div>

      {/* Active team banner */}
      <div style={{
        display: "flex",
        alignItems: "center",
        gap: "16px",
        marginBottom: "28px",
        padding: "14px 20px",
        background: "#111",
        border: "1px solid #1a1a1a",
        borderRadius: "8px",
        borderLeft: `3px solid ${activeLivery.primary}`,
      }}>
        <div style={{ display: "flex", gap: "6px" }}>
          {[activeLivery.primary, activeLivery.secondary, activeLivery.accent].map((col, i) => (
            <div key={i} style={{
              width: "18px", height: "18px", borderRadius: "50%",
              background: col, border: "1px solid #2a2a2a",
            }} />
          ))}
        </div>
        <div style={{ flex: 1 }}>
          <span style={{ fontFamily: "monospace", fontSize: "14px", fontWeight: 600, color: "#e5e5e5" }}>
            {activeTeam?.fullName ?? activeTeamId}
          </span>
          {activeTeam?.base && (
            <span style={{ fontFamily: "monospace", fontSize: "11px", color: "#555", marginLeft: "12px" }}>
              {activeTeam.base}
            </span>
          )}
        </div>
        <Link href={`/car/${activeTeam?.id ?? activeTeamId}`} style={{
          padding: "6px 14px",
          background: "#1a1a1a",
          border: "1px solid #2a2a2a",
          borderRadius: "5px",
          color: "#e5e5e5",
          fontFamily: "monospace",
          fontSize: "11px",
          letterSpacing: "1px",
          textTransform: "uppercase",
          textDecoration: "none",
        }}>
          Full Screen →
        </Link>
      </div>

      {/* Team selector */}
      <TeamSelector
        teams={teams}
        loading={loading}
        error={error}
        activeTeamId={activeTeamId}
        onTeamHover={(team) => setActiveTeamId(team.liveryKey)}
      />
    </div>
  );
}
