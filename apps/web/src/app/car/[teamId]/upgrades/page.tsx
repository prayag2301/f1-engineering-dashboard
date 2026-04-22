"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import dynamic from "next/dynamic";
import { TEAM_LIVERIES, type HighlightMap } from "@/components/F1CarModel";
import { useCarModel, findTeamByRouteParam } from "@/hooks/useCarModel";
import { useUpgrades } from "@/hooks/useUpgrades";
import UpgradeTimeline from "@/components/UpgradeTimeline";
import {
  anchorForZone,
  confidenceTier,
  CONFIDENCE_COLORS,
  type Vec3,
} from "@/lib/annotationAnchors";

const CarViewer = dynamic(() => import("@/components/CarViewer"), {
  ssr: false,
  loading: () => (
    <div
      style={{
        height: "100%", width: "100%", minHeight: 400,
        background: "#0a0a0a",
        display: "flex", alignItems: "center", justifyContent: "center",
        color: "#666", fontFamily: "monospace", fontSize: "13px",
      }}
    >
      Loading 3D model…
    </div>
  ),
});

export default function UpgradesPage({ params }: { params: { teamId: string } }) {
  const { teamId } = params;
  const { teams } = useCarModel();

  const backendTeam = findTeamByRouteParam(teams, teamId);
  const resolvedTeamKey =
    backendTeam?.liveryKey ?? (TEAM_LIVERIES[teamId] ? teamId : "red-bull");
  const displayName =
    backendTeam?.fullName ??
    teamId.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

  const { upgrades, loading, error } = useUpgrades({
    teamId: backendTeam?.id,
  });

  const [activeId, setActiveId] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);

  useEffect(() => {
    if (!activeId && upgrades.length > 0) setActiveId(upgrades[0].id);
  }, [upgrades, activeId]);

  const activeUpgrade = useMemo(
    () => upgrades.find((u) => u.id === activeId) ?? null,
    [upgrades, activeId],
  );

  const handleSelect = useCallback((id: string) => setActiveId(id), []);

  const handleArrow = useCallback(
    (dir: -1 | 1) => {
      if (upgrades.length === 0) return;
      const idx = upgrades.findIndex((u) => u.id === activeId);
      const nextIdx = (idx + dir + upgrades.length) % upgrades.length;
      setActiveId(upgrades[nextIdx].id);
    },
    [upgrades, activeId],
  );

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "ArrowDown" || e.key === "ArrowRight") {
        e.preventDefault();
        handleArrow(1);
      } else if (e.key === "ArrowUp" || e.key === "ArrowLeft") {
        e.preventDefault();
        handleArrow(-1);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [handleArrow]);

  const focusTarget: Vec3 | null = useMemo(() => {
    if (!activeUpgrade || showAll) return null;
    return anchorForZone(activeUpgrade.component?.zone).cameraTarget;
  }, [activeUpgrade, showAll]);

  const focusCameraOffset: Vec3 | null = useMemo(() => {
    if (!activeUpgrade || showAll) return null;
    return anchorForZone(activeUpgrade.component?.zone).cameraOffset;
  }, [activeUpgrade, showAll]);

  const highlightedZones: HighlightMap = useMemo(() => {
    if (showAll) {
      const map: HighlightMap = {};
      for (const u of upgrades) {
        const zone = u.component?.zone;
        if (!zone) continue;
        const tier = confidenceTier(u.confidence);
        const existing = map[zone];
        if (!existing || tier === "high") {
          map[zone] = CONFIDENCE_COLORS[tier];
        }
      }
      return map;
    }
    if (activeUpgrade?.component?.zone) {
      const tier = confidenceTier(activeUpgrade.confidence);
      return { [activeUpgrade.component.zone]: CONFIDENCE_COLORS[tier] };
    }
    return {};
  }, [showAll, upgrades, activeUpgrade]);

  const annotationsToRender = useMemo(() => {
    if (showAll) return upgrades;
    return activeUpgrade ? [activeUpgrade] : [];
  }, [showAll, upgrades, activeUpgrade]);

  return (
    <div className="container">
      <header className="header">
        <Link href="/" className="header__logo">F1 // Engineering</Link>
        <nav className="header__nav">
          <Link href="/">Cars</Link>
          <Link href={`/car/${teamId}`}>Viewer</Link>
          <Link href="/analyze">Analyze</Link>
        </nav>
      </header>
      <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: "16px", gap: "16px", flexWrap: "wrap" }}>
        <div>
          <h1 className="page-title">{displayName} — Upgrades</h1>
          <p className="page-subtitle">
            Use arrow keys to navigate. Click the car or timeline to focus an upgrade.
          </p>
        </div>
        <div style={{ display: "flex", gap: "8px" }}>
          <Link
            href={`/car/${teamId}`}
            style={{
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
            }}
          >
            Full Screen →
          </Link>
        </div>
      </div>

      <div className="upgrades-layout">
        <div className="upgrades-viewer">
          <div className="upgrades-toolbar">
            <button
              type="button"
              className={`upgrades-toggle ${showAll ? "upgrades-toggle--on" : ""}`}
              onClick={() => setShowAll((v) => !v)}
            >
              {showAll ? "Showing all" : "Show all upgrades"}
            </button>
          </div>
          <CarViewer
            teamId={resolvedTeamKey}
            height="100%"
            upgrades={annotationsToRender}
            activeUpgradeId={activeId}
            onSelectUpgrade={handleSelect}
            highlightedZones={highlightedZones}
            focusTarget={focusTarget}
            focusCameraOffset={focusCameraOffset}
          />
        </div>

        <UpgradeTimeline
          upgrades={upgrades}
          activeUpgradeId={activeId}
          onSelect={handleSelect}
          loading={loading}
          error={error}
        />
      </div>
    </div>
  );
}
