const API_BASE =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1")
    : (process.env.INTERNAL_API_URL ?? "http://api:8000/api/v1");

export interface Team {
  id: string;
  name: string;
  full_name: string;
  base: string | null;
  team_principal: string | null;
  power_unit: string | null;
  created_at: string;
}

export interface Race {
  id: string;
  name: string;
  circuit: string;
  country: string | null;
  round_number: number;
  season: number;
  date: string;
  created_at: string;
}

export interface Component {
  id: string;
  name: string;
  zone: string;
  description: string | null;
  created_at: string;
}

export interface Upgrade {
  id: string;
  team_id: string;
  race_id: string;
  component_id: string;
  category: string;
  description: string;
  technical_detail: string | null;
  expected_effect: string | null;
  confidence: number;
  aero_reasoning: string | null;
  mechanical_reasoning: string | null;
  performance_hypothesis: string | null;
  source: string | null;
  created_at: string;
  updated_at: string;
  team: Team | null;
  race: Race | null;
  component: Component | null;
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${await res.text()}`);
  }
  return res.json();
}

export async function getUpgrades(params?: {
  category?: string;
  team_id?: string;
  race_id?: string;
}): Promise<Upgrade[]> {
  const query = new URLSearchParams();
  if (params?.category) query.set("category", params.category);
  if (params?.team_id) query.set("team_id", params.team_id);
  if (params?.race_id) query.set("race_id", params.race_id);
  const qs = query.toString();
  return apiFetch<Upgrade[]>(`/upgrades/${qs ? `?${qs}` : ""}`);
}

export async function getUpgrade(id: string): Promise<Upgrade> {
  return apiFetch<Upgrade>(`/upgrades/${id}`);
}

export async function getTeams(): Promise<Team[]> {
  return apiFetch<Team[]>("/teams/");
}

export async function getRaces(season?: number): Promise<Race[]> {
  const qs = season ? `?season=${season}` : "";
  return apiFetch<Race[]>(`/races/${qs}`);
}

export async function seedDatabase(): Promise<{ message: string; seeded: boolean }> {
  return apiFetch("/seed/", { method: "POST" });
}

export interface UpgradeIntelligencePreview {
  inferred_category: string;
  inferred_component_zone: string;
  confidence: number;
  aero_reasoning: string;
  mechanical_reasoning: string;
  performance_hypothesis: string;
  signals: string[];
}

export async function previewUpgradeIntelligence(payload: {
  description: string;
  technical_detail?: string;
  expected_effect?: string;
  source?: string;
}): Promise<UpgradeIntelligencePreview> {
  return apiFetch("/upgrades/intelligence/preview", {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

export interface UpgradeBatchIngestResult {
  created: number;
  skipped_duplicates: number;
  upgrades: Upgrade[];
}

export async function ingestUpgrades(payload: {
  items: Array<{
    team_id: string;
    race_id: string;
    component_id: string;
    description: string;
    technical_detail?: string;
    expected_effect?: string;
    category?: string;
    confidence?: number;
    source?: string;
  }>;
  enrich_missing_fields?: boolean;
  skip_duplicates?: boolean;
}): Promise<UpgradeBatchIngestResult> {
  return apiFetch("/upgrades/ingest", {
    method: "POST",
    body: JSON.stringify({ enrich_missing_fields: true, skip_duplicates: true, ...payload }),
  });
}
