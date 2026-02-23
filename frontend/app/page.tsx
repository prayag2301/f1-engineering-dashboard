"use client";

import { useEffect, useMemo, useState } from "react";
import { getTeams, getUpgrades, type Team, type Upgrade } from "@/lib/api";
import UpgradeCard from "@/components/UpgradeCard";
import CategoryFilter from "@/components/CategoryFilter";
import TeamFilter from "@/components/TeamFilter";
import UpgradeFocusModal from "@/components/UpgradeFocusModal";

export default function HomePage() {
  const [upgrades, setUpgrades] = useState<Upgrade[]>([]);
  const [teams, setTeams] = useState<Team[]>([]);
  const [category, setCategory] = useState("All");
  const [teamId, setTeamId] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [focusedUpgrade, setFocusedUpgrade] = useState<Upgrade | null>(null);

  useEffect(() => {
    getTeams().then(setTeams).catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const params: { category?: string; team_id?: string } = {};
    if (category !== "All") params.category = category;
    if (teamId !== "All") params.team_id = teamId;
    getUpgrades(params)
      .then(setUpgrades)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [category, teamId]);

  const teamWiseGroups = useMemo(() => {
    const grouped = new Map<string, Upgrade[]>();
    for (const upgrade of upgrades) {
      const key = upgrade.team?.name ?? "Unknown Team";
      const existing = grouped.get(key) ?? [];
      existing.push(upgrade);
      grouped.set(key, existing);
    }
    return Array.from(grouped.entries()).sort(([a], [b]) => a.localeCompare(b));
  }, [upgrades]);

  return (
    <>
      <h1 className="page-title">Upgrade Intelligence</h1>
      <p className="page-subtitle">
        Team-wise technical upgrades across the grid. Click any upgrade card to
        open a clean demo 3D focus view of the upgraded area.
      </p>

      <div className="filters-row">
        <CategoryFilter selected={category} onSelect={setCategory} />
        <TeamFilter
          teams={teams}
          selectedTeamId={teamId}
          onSelect={(nextTeamId) => setTeamId(nextTeamId)}
        />
      </div>

      {loading && <div className="loading">Loading upgrades…</div>}

      {error && (
        <div className="empty">
          Error: {error}
          <br />
          <small>Make sure the backend is running and the database is seeded.</small>
        </div>
      )}

      {!loading && !error && upgrades.length === 0 && (
        <div className="empty">
          No upgrades found.
          <br />
          <small>
            POST /api/v1/seed/ to populate the database with sample data.
          </small>
        </div>
      )}

      {!loading && !error && upgrades.length > 0 && (
        <>
          {teamWiseGroups.map(([teamName, teamUpgrades]) => (
            <section key={teamName} className="team-section">
              <h2 className="team-section__title">{teamName}</h2>
              <div className="upgrade-grid">
                {teamUpgrades.map((upgrade) => (
                  <UpgradeCard
                    key={upgrade.id}
                    upgrade={upgrade}
                    onOpenFocus={setFocusedUpgrade}
                  />
                ))}
              </div>
            </section>
          ))}
        </>
      )}

      {focusedUpgrade && (
        <UpgradeFocusModal
          upgrade={focusedUpgrade}
          onClose={() => setFocusedUpgrade(null)}
        />
      )}
    </>
  );
}
