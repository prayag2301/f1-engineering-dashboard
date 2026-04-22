"use client";

import { useMemo } from "react";
import type { Upgrade } from "@/lib/api";
import { confidenceTier, CONFIDENCE_COLORS } from "@/lib/annotationAnchors";

interface Props {
  upgrades: Upgrade[];
  activeUpgradeId: string | null;
  onSelect: (id: string) => void;
  loading?: boolean;
  error?: string | null;
}

interface RaceGroup {
  key: string;
  label: string;
  round: number;
  date: string | null;
  items: Upgrade[];
}

function groupByRace(upgrades: Upgrade[]): RaceGroup[] {
  const groups = new Map<string, RaceGroup>();
  for (const u of upgrades) {
    const race = u.race;
    const key = race?.id ?? "unscheduled";
    const existing = groups.get(key);
    if (existing) {
      existing.items.push(u);
    } else {
      groups.set(key, {
        key,
        label: race?.name ?? "Unscheduled",
        round: race?.round_number ?? 999,
        date: race?.date ?? null,
        items: [u],
      });
    }
  }
  return Array.from(groups.values()).sort((a, b) => {
    if (a.date && b.date) return b.date.localeCompare(a.date);
    return a.round - b.round;
  });
}

export default function UpgradeTimeline({
  upgrades,
  activeUpgradeId,
  onSelect,
  loading,
  error,
}: Props) {
  const groups = useMemo(() => groupByRace(upgrades), [upgrades]);

  return (
    <div className="timeline">
      <div className="timeline__header">
        <span className="timeline__title">Upgrade Timeline</span>
        <span className="timeline__count">{upgrades.length}</span>
      </div>

      {loading && (
        <div className="timeline__empty">Loading upgrade intel…</div>
      )}
      {error && !loading && (
        <div className="timeline__empty">{error}</div>
      )}
      {!loading && !error && upgrades.length === 0 && (
        <div className="timeline__empty">
          No upgrades recorded for this team yet.
          <br />
          <small>Ingest pipeline runs on demand via `fetch_upgrades`.</small>
        </div>
      )}

      {groups.map((group) => (
        <div key={group.key} className="timeline__group">
          <div className="timeline__race">
            {group.date ? `Rd ${group.round} · ${group.label}` : group.label}
          </div>
          {group.items.map((upgrade) => {
            const tier = confidenceTier(upgrade.confidence);
            const active = upgrade.id === activeUpgradeId;
            return (
              <button
                key={upgrade.id}
                type="button"
                onClick={() => onSelect(upgrade.id)}
                className={`timeline__entry ${active ? "timeline__entry--active" : ""}`}
                style={{ borderLeftColor: CONFIDENCE_COLORS[tier] }}
              >
                <span
                  className="timeline__dot"
                  style={{ background: CONFIDENCE_COLORS[tier] }}
                />
                <div className="timeline__body">
                  <div className="timeline__zone">
                    {upgrade.component?.zone ?? upgrade.component?.name ?? "Component"}
                  </div>
                  <div className="timeline__desc">{upgrade.description}</div>
                  <div className="timeline__meta">
                    <span>{upgrade.category}</span>
                    <span>· {(upgrade.confidence * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </button>
            );
          })}
        </div>
      ))}
    </div>
  );
}
