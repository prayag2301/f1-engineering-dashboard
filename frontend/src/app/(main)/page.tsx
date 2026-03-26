"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import Link from "next/link";
import { TEAM_LIVERIES } from "@/components/F1CarModel";

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

const TEAMS = [
  { id: "red-bull",     name: "Red Bull Racing",   short: "RBR" },
  { id: "ferrari",      name: "Ferrari",            short: "FER" },
  { id: "mercedes",     name: "Mercedes",           short: "MER" },
  { id: "mclaren",      name: "McLaren",            short: "MCL" },
  { id: "aston-martin", name: "Aston Martin",       short: "AMR" },
  { id: "alpine",       name: "Alpine",             short: "ALP" },
  { id: "williams",     name: "Williams",           short: "WIL" },
  { id: "racing-bulls", name: "Racing Bulls",       short: "RB"  },
  { id: "haas",         name: "Haas",               short: "HAA" },
  { id: "audi",         name: "Audi F1",            short: "AUD" },
  { id: "cadillac",     name: "Cadillac",           short: "CAD" },
];

export default function Home() {
  const [activeTeam, setActiveTeam] = useState("red-bull");
  const activeLivery = TEAM_LIVERIES[activeTeam] ?? TEAM_LIVERIES["red-bull"];
  const activeTeamName = TEAMS.find((t) => t.id === activeTeam)?.name ?? activeTeam;

  return (
    <div>
      <div style={{ marginBottom: "24px" }}>
        <h1 className="page-title">3D Car Viewer</h1>
        <p className="page-subtitle">
          Procedural F1 car models — 2026 regulations. Select a constructor below.
        </p>
      </div>

      {/* 3D Viewer */}
      <div style={{ marginBottom: "20px", borderRadius: "8px", overflow: "hidden", border: "1px solid #1a1a1a" }}>
        <CarViewer teamId={activeTeam} height="600px" />
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
        <span style={{ fontFamily: "monospace", fontSize: "14px", fontWeight: 600, color: "#e5e5e5" }}>
          {activeTeamName}
        </span>
        <Link href={`/car/${activeTeam}`} style={{
          marginLeft: "auto",
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
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "12px" }}>
        {TEAMS.map((team) => {
          const livery = TEAM_LIVERIES[team.id] ?? TEAM_LIVERIES["red-bull"];
          const isActive = activeTeam === team.id;
          return (
            <div
              key={team.id}
              className="card card--interactive"
              onClick={() => setActiveTeam(team.id)}
              style={{
                padding: "16px",
                borderColor: isActive ? livery.primary : undefined,
                background: isActive ? `${livery.primary}18` : undefined,
              }}
            >
              <div style={{ display: "flex", gap: "5px", marginBottom: "10px" }}>
                {[livery.primary, livery.secondary, livery.accent].map((col, i) => (
                  <div key={i} style={{
                    width: "12px", height: "12px", borderRadius: "50%",
                    background: col, border: "1px solid #2a2a2a", flexShrink: 0,
                  }} />
                ))}
              </div>
              <div style={{ fontFamily: "monospace", fontSize: "10px", color: "#666", letterSpacing: "1px", textTransform: "uppercase", marginBottom: "4px" }}>
                {team.short}
              </div>
              <div style={{ fontSize: "13px", fontWeight: 600, color: isActive ? "#e5e5e5" : "#aaa", marginBottom: "10px" }}>
                {team.name}
              </div>
              <Link
                href={`/car/${team.id}`}
                onClick={(e) => e.stopPropagation()}
                style={{
                  display: "block", textAlign: "center", padding: "5px 0",
                  background: "#1a1a1a", border: "1px solid #2a2a2a", borderRadius: "4px",
                  color: "#888", fontFamily: "monospace", fontSize: "10px",
                  letterSpacing: "1px", textTransform: "uppercase", textDecoration: "none",
                }}
              >
                View Car →
              </Link>
            </div>
          );
        })}
      </div>
    </div>
  );
}
