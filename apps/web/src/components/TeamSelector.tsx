"use client";

import Link from "next/link";
import { TEAM_LIVERIES } from "@/components/F1CarModel";
import type { Team } from "@/hooks/useCarModel";

interface TeamSelectorProps {
  teams: Team[];
  loading?: boolean;
  error?: string | null;
  activeTeamId?: string;
  onTeamHover?: (team: Team) => void;
}

export default function TeamSelector({
  teams,
  loading = false,
  error = null,
  activeTeamId,
  onTeamHover,
}: TeamSelectorProps) {
  if (loading) {
    return (
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))",
          gap: "12px",
        }}
      >
        {Array.from({ length: 10 }).map((_, i) => (
          <div
            key={i}
            style={{
              height: "120px",
              background: "#111",
              border: "1px solid #1a1a1a",
              borderRadius: "8px",
              animation: "pulse 1.5s ease-in-out infinite",
            }}
          />
        ))}
      </div>
    );
  }

  if (teams.length === 0) {
    return (
      <div
        style={{
          padding: "16px",
          background: "#111",
          border: "1px solid #1a1a1a",
          borderRadius: "8px",
          color: "#888",
          fontFamily: "monospace",
          fontSize: "12px",
        }}
      >
        {error ?? "No teams available."}
      </div>
    );
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(180px, 1fr))", gap: "12px" }}>
      {teams.map((team) => {
        const livery = TEAM_LIVERIES[team.liveryKey] ?? TEAM_LIVERIES["red-bull"];
        const isActive = activeTeamId ? activeTeamId === team.liveryKey : false;
        return (
          <Link
            key={team.id}
            href={`/car/${team.id}`}
            className="card card--interactive"
            onMouseEnter={() => onTeamHover?.(team)}
            style={{
              display: "block",
              padding: "16px",
              borderColor: isActive ? livery.primary : undefined,
              background: isActive ? `${livery.primary}18` : undefined,
              textDecoration: "none",
            }}
          >
            <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "10px" }}>
              <div style={{ display: "flex", gap: "5px" }}>
                {[livery.primary, livery.secondary, livery.accent].map((col, i) => (
                  <div
                    key={i}
                    style={{
                      width: "12px",
                      height: "12px",
                      borderRadius: "50%",
                      background: col,
                      border: "1px solid #2a2a2a",
                      flexShrink: 0,
                    }}
                  />
                ))}
              </div>
              <div
                style={{
                  width: "28px",
                  height: "28px",
                  borderRadius: "50%",
                  background: "#1a1a1a",
                  border: `1px solid ${livery.primary}66`,
                  color: "#999",
                  fontFamily: "monospace",
                  fontSize: "9px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  letterSpacing: "0.5px",
                }}
              >
                LOGO
              </div>
            </div>
            <div
              style={{
                fontFamily: "monospace",
                fontSize: "10px",
                color: "#666",
                letterSpacing: "1px",
                textTransform: "uppercase",
                marginBottom: "4px",
              }}
            >
              {team.shortName}
            </div>
            <div
              style={{
                fontSize: "13px",
                fontWeight: 600,
                color: isActive ? "#e5e5e5" : "#aaa",
                marginBottom: "4px",
              }}
            >
              {team.name}
            </div>
            <div style={{ fontSize: "11px", color: "#555", fontFamily: "monospace", minHeight: "16px", marginBottom: "10px" }}>
              {team.teamPrincipal ?? "Team principal TBD"}
            </div>
            <div
              style={{
                textAlign: "center",
                padding: "5px 0",
                background: "#1a1a1a",
                border: "1px solid #2a2a2a",
                borderRadius: "4px",
                color: "#888",
                fontFamily: "monospace",
                fontSize: "10px",
                letterSpacing: "1px",
                textTransform: "uppercase",
              }}
            >
              View Car →
            </div>
          </Link>
        );
      })}
    </div>
  );
}
