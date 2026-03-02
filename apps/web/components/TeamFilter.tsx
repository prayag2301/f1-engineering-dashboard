"use client";

import type { Team } from "@/lib/api";

export default function TeamFilter({
  teams,
  selectedTeamId,
  onSelect,
}: {
  teams: Team[];
  selectedTeamId: string;
  onSelect: (teamId: string) => void;
}) {
  return (
    <div className="team-filter">
      <label htmlFor="team-filter-select" className="team-filter__label">
        Team View
      </label>
      <select
        id="team-filter-select"
        className="team-filter__select"
        value={selectedTeamId}
        onChange={(event) => onSelect(event.target.value)}
      >
        <option value="All">All Teams</option>
        {teams.map((team) => (
          <option key={team.id} value={team.id}>
            {team.name}
          </option>
        ))}
      </select>
    </div>
  );
}
