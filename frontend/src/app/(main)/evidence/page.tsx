"use client";

import { useEffect, useMemo, useState } from "react";
import {
  getEvidence,
  getUpgrades,
  IS_DEMO,
  type EvidenceRecord,
  type Upgrade,
} from "@/lib/api";
import ComingSoon from "@/components/ComingSoon";

export default function EvidencePage() {
  if (IS_DEMO) {
    return (
      <>
        <h1 className="page-title">Evidence</h1>
        <p className="page-subtitle">
          Source-cited upgrade evidence from the ingestion pipeline.
        </p>
        <ComingSoon feature="Evidence browser" />
      </>
    );
  }
  return <EvidencePageInner />;
}

function EvidencePageInner() {
  const [evidence, setEvidence] = useState<EvidenceRecord[]>([]);
  const [upgrades, setUpgrades] = useState<Upgrade[]>([]);
  const [teamId, setTeamId] = useState("All");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([getEvidence(), getUpgrades()])
      .then(([evidenceRows, upgradeRows]) => {
        setEvidence(evidenceRows);
        setUpgrades(upgradeRows);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const upgradeById = useMemo(
    () => new Map(upgrades.map((upgrade) => [upgrade.id, upgrade])),
    [upgrades],
  );

  const teamOptions = useMemo(() => {
    const byId = new Map<string, string>();
    for (const upgrade of upgrades) {
      if (upgrade.team_id && upgrade.team?.name) {
        byId.set(upgrade.team_id, upgrade.team.name);
      }
    }
    return Array.from(byId.entries()).sort((a, b) => a[1].localeCompare(b[1]));
  }, [upgrades]);

  const filteredEvidence = useMemo(() => {
    if (teamId === "All") return evidence;
    return evidence.filter((row) => upgradeById.get(row.upgrade_id)?.team_id === teamId);
  }, [evidence, teamId, upgradeById]);

  return (
    <>
      <h1 className="page-title">Evidence Browser</h1>
      <p className="page-subtitle">
        Browse source evidence linked to technical upgrades, with credibility
        scoring and traceable source paths.
      </p>

      <div className="filters-row">
        <div className="team-filter">
          <label className="team-filter__label" htmlFor="evidence-team-filter">
            Team
          </label>
          <select
            id="evidence-team-filter"
            className="team-filter__select"
            value={teamId}
            onChange={(event) => setTeamId(event.target.value)}
          >
            <option value="All">All Teams</option>
            {teamOptions.map(([id, name]) => (
              <option key={id} value={id}>
                {name}
              </option>
            ))}
          </select>
        </div>
      </div>

      {loading && <div className="loading">Loading evidence…</div>}

      {error && (
        <div className="empty">
          Error: {error}
          <br />
          <small>Make sure the backend is running and database is seeded.</small>
        </div>
      )}

      {!loading && !error && filteredEvidence.length === 0 && (
        <div className="empty">
          No evidence found.
          <br />
          <small>POST /api/v1/seed/ to create sample events and evidence.</small>
        </div>
      )}

      {!loading && !error && filteredEvidence.length > 0 && (
        <div className="upgrade-grid">
          {filteredEvidence.map((row) => {
            const upgrade = upgradeById.get(row.upgrade_id);
            const teamName = upgrade?.team?.name ?? "Unknown Team";
            const raceName = upgrade?.race?.name ?? "Unknown Race";
            const componentName = upgrade?.component?.name ?? "Unknown Component";
            const credibility = Math.round(row.credibility_score * 100);

            return (
              <article key={row.id} className="card">
                <div className="card__header">
                  <span className="card__team">{teamName}</span>
                  <span className="card__race">{credibility}% credibility</span>
                </div>
                <div className="card__component">{componentName}</div>
                <p className="card__description">{row.source}</p>
                <div className="card__meta">
                  <span className="badge badge--confidence">{raceName}</span>
                  <span className="badge badge--confidence">{row.license}</span>
                </div>
                <div className="card__meta" style={{ marginTop: 12 }}>
                  {row.article_path && (
                    <a
                      className="filter-btn"
                      href={row.article_path}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Article
                    </a>
                  )}
                  {row.media_path && (
                    <a
                      className="filter-btn"
                      href={row.media_path}
                      target="_blank"
                      rel="noreferrer"
                    >
                      Media
                    </a>
                  )}
                </div>
              </article>
            );
          })}
        </div>
      )}
    </>
  );
}
