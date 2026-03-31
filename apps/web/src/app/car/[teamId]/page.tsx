"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { TEAM_LIVERIES } from "@/components/F1CarModel";
import { useCarModel, findTeamByRouteParam } from "@/hooks/useCarModel";

const CarViewer = dynamic(() => import("@/components/CarViewer"), {
  ssr: false,
  loading: () => (
    <div style={{
      position: "fixed", inset: 0,
      background: "#0a0a0a",
      display: "flex", alignItems: "center", justifyContent: "center",
      color: "#666", fontFamily: "monospace", fontSize: "13px",
    }}>
      Loading 3D model…
    </div>
  ),
});

const TEAM_DRIVERS: Record<string, [string, string]> = {
  "red-bull":     ["Max Verstappen", "Isack Hadjar"],
  ferrari:        ["Charles Leclerc", "Lewis Hamilton"],
  mercedes:       ["George Russell", "Kimi Antonelli"],
  mclaren:        ["Lando Norris", "Oscar Piastri"],
  "aston-martin": ["Fernando Alonso", "Lance Stroll"],
  alpine:         ["Pierre Gasly", "Jack Doohan"],
  williams:       ["Alex Albon", "Carlos Sainz"],
  "racing-bulls": ["Yuki Tsunoda", "Liam Lawson"],
  haas:           ["Esteban Ocon", "Oliver Bearman"],
  audi:           ["Nico Hülkenberg", "Gabriel Bortoleto"],
  cadillac:       ["Colton Herta", "TBC"],
};

export default function CarPage({ params }: { params: { teamId: string } }) {
  const { teamId } = params;
  const { teams, loading, error } = useCarModel();

  const backendTeam = findTeamByRouteParam(teams, teamId);
  const resolvedTeamKey = backendTeam?.liveryKey ?? (TEAM_LIVERIES[teamId] ? teamId : "red-bull");
  const livery = TEAM_LIVERIES[resolvedTeamKey] ?? TEAM_LIVERIES["red-bull"];
  const drivers = TEAM_DRIVERS[resolvedTeamKey] ?? ["Driver 1", "Driver 2"];
  const displayName = backendTeam?.fullName ?? teamId.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const showNotFound = !loading && !backendTeam && !TEAM_LIVERIES[teamId];

  return (
    <div style={{ position: "fixed", inset: 0, background: "#0a0a0a" }}>
      <CarViewer teamId={resolvedTeamKey} height="100%" />

      {/* Back button */}
      <div style={{ position: "fixed", top: "24px", left: "24px", zIndex: 10 }}>
        <Link href="/" style={{
          display: "inline-flex", alignItems: "center", gap: "8px",
          padding: "8px 16px",
          background: "rgba(10,10,10,0.85)", border: "1px solid #2a2a2a",
          borderRadius: "6px", color: "#e5e5e5", fontFamily: "monospace",
          fontSize: "12px", textDecoration: "none", backdropFilter: "blur(8px)",
          letterSpacing: "1px", textTransform: "uppercase",
        }}>
          ← Back
        </Link>
        {error && (
          <div
            style={{
              marginTop: "10px",
              padding: "7px 10px",
              background: "#f59e0b18",
              border: "1px solid #f59e0b33",
              color: "#f59e0b",
              borderRadius: "5px",
              fontSize: "11px",
              fontFamily: "monospace",
              maxWidth: "320px",
            }}
          >
            {error}
          </div>
        )}
      </div>

      {/* Branding */}
      <div style={{
        position: "fixed", top: "24px", right: "24px", zIndex: 10,
        fontFamily: "monospace", fontSize: "12px", color: "#555",
        letterSpacing: "2px", textTransform: "uppercase",
      }}>
        F1 // Engineering
      </div>

      {/* Team info overlay */}
      <div style={{
        position: "fixed", bottom: 0, left: 0, right: 0, zIndex: 10,
        padding: "32px 32px 28px",
        background: "linear-gradient(to top, rgba(0,0,0,0.92) 0%, rgba(0,0,0,0.5) 60%, transparent 100%)",
      }}>
        <div style={{ width: "48px", height: "3px", background: livery.primary, borderRadius: "2px", marginBottom: "14px" }} />
        <div style={{ display: "flex", alignItems: "flex-end", justifyContent: "space-between", flexWrap: "wrap", gap: "16px" }}>
          <div>
            <p style={{ fontFamily: "monospace", fontSize: "11px", color: "#666", letterSpacing: "2px", textTransform: "uppercase", marginBottom: "6px" }}>
              2026 Season — F1 Engineering Dashboard
            </p>
            <h1 style={{ fontSize: "clamp(22px, 4vw, 40px)", fontWeight: 700, color: "#e5e5e5", letterSpacing: "-0.5px", marginBottom: "10px" }}>
              {loading ? "Loading…" : displayName}
            </h1>

            {/* Backend metadata row */}
            {backendTeam && (
              <div style={{ display: "flex", gap: "20px", marginBottom: "12px", flexWrap: "wrap" }}>
                {backendTeam.base && (
                  <span style={{ fontFamily: "monospace", fontSize: "11px", color: "#666" }}>
                    Base: {backendTeam.base}
                  </span>
                )}
                {backendTeam.teamPrincipal && (
                  <span style={{ fontFamily: "monospace", fontSize: "11px", color: "#666" }}>
                    TP: {backendTeam.teamPrincipal}
                  </span>
                )}
                {backendTeam.powerUnit && (
                  <span style={{ fontFamily: "monospace", fontSize: "11px", color: "#666" }}>
                    PU: {backendTeam.powerUnit}
                  </span>
                )}
              </div>
            )}

            <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
              {drivers.map((d) => (
                <span key={d} style={{
                  padding: "4px 12px", borderRadius: "4px",
                  border: `1px solid ${livery.primary}55`, background: `${livery.primary}18`,
                  color: "#ccc", fontFamily: "monospace", fontSize: "12px",
                }}>
                  {d}
                </span>
              ))}
            </div>
          </div>
          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
            {[livery.primary, livery.secondary, livery.accent].map((col, i) => (
              <div key={i} style={{ width: "24px", height: "24px", borderRadius: "50%", background: col, border: "1px solid #333" }} />
            ))}
          </div>
        </div>
      </div>

      {showNotFound && (
        <div
          style={{
            position: "fixed",
            left: "50%",
            top: "96px",
            transform: "translateX(-50%)",
            zIndex: 11,
            background: "rgba(0,0,0,0.82)",
            border: "1px solid #2a2a2a",
            borderRadius: "6px",
            padding: "10px 14px",
            color: "#bbb",
            fontFamily: "monospace",
            fontSize: "11px",
            letterSpacing: "0.4px",
          }}
        >
          Team not found in API dataset. Showing default model.
        </div>
      )}
    </div>
  );
}
