import type { CarVersion, Catalog, Source, TeamKey } from "./releases";

export interface DashboardData {
  catalog: Catalog;
  versions: CarVersion[];
}

export const teamName = (team: TeamKey) =>
  team === "ferrari" ? "Ferrari" : "Mercedes";
export const currentVersion = (versions: CarVersion[], team: TeamKey) =>
  versions.find((v) => v.team_key === team && v.is_current) ??
  versions.find((v) => v.team_key === team);

export function changedComponents(version: CarVersion) {
  return Object.entries(version.manifest.components)
    .filter(([, component]) => component.changed)
    .map(([key]) => key);
}

export function releaseKind(version: CarVersion) {
  if (version.configuration_kind === "reconstruction")
    return "Reconstruction update";
  if (version.configuration_kind === "baseline") return "Launch reference";
  if (version.reverts_to_id) return "Configuration reversion";
  return "Configuration update";
}

export interface EvidenceEntry {
  source: Source;
  teams: Set<TeamKey>;
  components: Set<string>;
  versions: CarVersion[];
}

export function collectEvidence(versions: CarVersion[]): EvidenceEntry[] {
  const entries = new Map<string, EvidenceEntry>();
  for (const version of versions) {
    for (const source of version.manifest.sources) {
      const entry = entries.get(source.id) ?? {
        source,
        teams: new Set<TeamKey>(),
        components: new Set<string>(),
        versions: [],
      };
      entry.teams.add(version.team_key);
      entry.versions.push(version);
      for (const [key, component] of Object.entries(
        version.manifest.components,
      )) {
        if (component.source_ids.includes(source.id)) entry.components.add(key);
      }
      for (const change of version.manifest.changes) {
        if (change.source_id === source.id && change.component)
          entry.components.add(change.component);
      }
      entries.set(source.id, entry);
    }
  }
  return [...entries.values()].sort((a, b) =>
    (b.source.published_at ?? "").localeCompare(a.source.published_at ?? ""),
  );
}

export function upgradeCount(versions: CarVersion[]) {
  return new Set(versions.flatMap((v) => v.manifest.changes.map((c) => c.id)))
    .size;
}
