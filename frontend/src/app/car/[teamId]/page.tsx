"use client";

import Link from "next/link";
import dynamic from "next/dynamic";
import { TEAM_LIVERIES } from "@/components/F1CarModel";

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

const TEAM_DISPLAY: Record<string, string> = {
  "red-bull":     "Oracle Red Bull Racing",
  ferrari:        "Scuderia Ferrari HP",
  mercedes:       "Mercedes-AMG Petronas F1",
  mclaren:        "McLaren Formula 1 Team",
  "aston-martin": "Aston Martin Aramco F1",
  alpine:         "BWT Alpine F1 Team",
  williams:       "Williams Racing",
  "racing-bulls": "Visa Cash App RB F1",
  haas:           "MoneyGram Haas F1 Team",
  audi:           "Audi F1 Team",
  cadillac:       "Cadillac F1 Team",
};

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
  const livery = TEAM_LIVERIES[teamId] ?? TEAM_LIVERIES["red-bull"];
  const displayName = TEAM_DISPLAY[teamId] ?? teamId;
  const drivers = TEAM_DRIVERS[teamId] ?? ["Driver 1", "Driver 2"];

  return (
    <div style={{ position: "fixed", inset: 0, background: "#0a0a0a" }}>
      <CarViewer teamId={teamId} height="100%" />

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
              {displayName}
            </h1>
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
    </div>
  );
}
