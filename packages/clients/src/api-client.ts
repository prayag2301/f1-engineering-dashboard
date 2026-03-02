import type {
  Team,
  Race,
  Upgrade,
  UpgradeIntelligencePreview,
  UpgradeBatchIngestResult,
  UpgradeIngestItem,
} from "@f1/common";

export class F1ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string) {
    this.baseUrl = baseUrl;
  }

  private async fetch<T>(path: string, init?: RequestInit): Promise<T> {
    const res = await fetch(`${this.baseUrl}${path}`, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
    if (!res.ok) {
      throw new Error(`API error ${res.status}: ${await res.text()}`);
    }
    return res.json() as Promise<T>;
  }

  async getTeams(): Promise<Team[]> {
    return this.fetch<Team[]>("/teams/");
  }

  async getRaces(season?: number): Promise<Race[]> {
    const qs = season ? `?season=${season}` : "";
    return this.fetch<Race[]>(`/races/${qs}`);
  }

  async getUpgrades(params?: {
    category?: string;
    team_id?: string;
    race_id?: string;
  }): Promise<Upgrade[]> {
    const query = new URLSearchParams();
    if (params?.category) query.set("category", params.category);
    if (params?.team_id) query.set("team_id", params.team_id);
    if (params?.race_id) query.set("race_id", params.race_id);
    const qs = query.toString();
    return this.fetch<Upgrade[]>(`/upgrades/${qs ? `?${qs}` : ""}`);
  }

  async getUpgrade(id: string): Promise<Upgrade> {
    return this.fetch<Upgrade>(`/upgrades/${id}`);
  }

  async previewUpgradeIntelligence(payload: {
    description: string;
    technical_detail?: string;
    expected_effect?: string;
    source?: string;
  }): Promise<UpgradeIntelligencePreview> {
    return this.fetch<UpgradeIntelligencePreview>(
      "/upgrades/intelligence/preview",
      { method: "POST", body: JSON.stringify(payload) },
    );
  }

  async ingestUpgrades(payload: {
    items: UpgradeIngestItem[];
    enrich_missing_fields?: boolean;
    skip_duplicates?: boolean;
  }): Promise<UpgradeBatchIngestResult> {
    return this.fetch<UpgradeBatchIngestResult>("/upgrades/ingest", {
      method: "POST",
      body: JSON.stringify({
        enrich_missing_fields: true,
        skip_duplicates: true,
        ...payload,
      }),
    });
  }

  async seedDatabase(): Promise<{ message: string; seeded: boolean }> {
    return this.fetch("/seed/", { method: "POST" });
  }
}
