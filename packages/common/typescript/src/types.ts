import type { UpgradeCategory, ComponentZone } from "./enums";

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
  zone: ComponentZone;
  description: string | null;
  created_at: string;
}

export interface Upgrade {
  id: string;
  team_id: string;
  race_id: string;
  component_id: string;
  category: UpgradeCategory;
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

export interface UpgradeIntelligencePreview {
  inferred_category: UpgradeCategory;
  inferred_component_zone: ComponentZone;
  confidence: number;
  aero_reasoning: string;
  mechanical_reasoning: string;
  performance_hypothesis: string;
  signals: string[];
}

export interface UpgradeIngestItem {
  team_id: string;
  race_id: string;
  component_id: string;
  description: string;
  technical_detail?: string;
  expected_effect?: string;
  category?: UpgradeCategory;
  confidence?: number;
  source?: string;
}

export interface UpgradeBatchIngestResult {
  created: number;
  skipped_duplicates: number;
  upgrades: Upgrade[];
}

export interface PerformanceDelta {
  id: string;
  team_id: string;
  race_id: string;
  fp1_time: number | null;
  fp2_time: number | null;
  fp3_time: number | null;
  quali_time: number | null;
  race_best_lap: number | null;
  delta_fp1_to_quali: number;
  delta_quali_to_race: number;
  delta_race_over_race: number;
  upgrade_efficiency_score: number;
  notes: string | null;
  created_at: string;
  team: Team | null;
  race: Race | null;
}

export interface EvidenceRecord {
  id: string;
  upgrade_id: string;
  source: string;
  license: string;
  credibility_score: number;
  media_path: string | null;
  article_path: string | null;
  created_at: string;
}

export interface CalloutRecord {
  id: string;
  upgrade_id: string;
  label: string;
  anchor_type: string;
  anchor_ref: string;
  description: string;
  created_at: string;
}
