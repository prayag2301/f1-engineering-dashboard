export const TEAM_NAMES = {
  ferrari: "Ferrari",
  mercedes: "Mercedes",
  mclaren: "McLaren",
  red_bull: "Red Bull Racing",
  aston_martin: "Aston Martin",
  alpine: "Alpine",
  williams: "Williams",
  haas: "Haas",
  racing_bulls: "Racing Bulls",
  audi: "Audi",
  cadillac: "Cadillac",
} as const;
export type TeamKey = keyof typeof TEAM_NAMES;
export const TEAM_KEYS = Object.keys(TEAM_NAMES) as TeamKey[];
export type ViewName = "three_quarter" | "front" | "side" | "rear";
export interface Source {
  id: string;
  url: string;
  title: string;
  publisher: string;
  published_at: string | null;
  retrieved_at: string;
  source_type: string;
  image_urls: string[];
  rights: string;
}
export interface Candidate {
  id: string;
  source_id: string;
  team_key: TeamKey | null;
  season: number;
  component: string | null;
  event_name: string | null;
  observed_at: string | null;
  summary: string;
  supporting_passage: string;
  page: number | null;
  evidence_status: "unverified" | "reported" | "confirmed" | "conflicting";
  representation: "annotation_only" | "modeled";
  status: "draft" | "approved" | "rejected";
  review_notes: string;
  source?: Source;
}
export interface Asset {
  filename: string;
  url: string;
  sha256: string;
  bytes: number;
}
export interface ComponentState {
  revision_id: string;
  label: string;
  anchor: [number, number, number];
  parameters: Record<string, number>;
  source_ids: string[];
  uncertainty: string;
  changed: boolean;
}
export interface CarVersion {
  id: string;
  team_key: TeamKey;
  season: number;
  label: string;
  configuration_event: string;
  configuration_kind: string;
  reverts_to_id?: string | null;
  as_of: string;
  evidence_cutoff: string;
  status: "draft" | "building" | "ready" | "published" | "failed";
  parent_id: string | null;
  published_at: string | null;
  is_current: boolean;
  notes: string;
  component_revisions: Record<string, string>;
  visual_review: Partial<Record<ViewName, boolean>> & {
    notes?: string;
    reference_urls?: string[];
    reviewed_at?: string;
  };
  manifest: {
    components: Record<string, ComponentState>;
    sources: Source[];
    changes: Candidate[];
    assets: Record<string, Asset>;
    component_hashes?: Record<string, string>;
    no_new_modeled_change: boolean;
    reconstruction_notice: string;
    validation?: { triangles: number; glb_bytes: number; textures: number };
  };
}
export interface Catalog {
  teams: Record<
    TeamKey,
    {
      name: string;
      car_name: string;
      accent: string;
      baseline_date: string;
      notes: string;
      source_url: string;
    }
  >;
  components: Record<
    string,
    {
      label: string;
      anchor: [number, number, number];
      parameters: Record<string, [number, number]>;
    }
  >;
  season: number;
}
export interface Job {
  id: string;
  version_id: string | null;
  kind: string;
  status: string;
  attempts: number;
  error: string | null;
  result: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
}
export interface Dashboard {
  versions: CarVersion[];
  candidates: Candidate[];
  jobs: Job[];
  sources: Source[];
  audit: { action: string; target_id: string; created_at: string }[];
}

export async function request<T>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const response = await fetch(`/api/v1${path}`, {
    ...init,
    credentials: "same-origin",
    cache: "no-store",
    headers: {
      "Content-Type": "application/json",
      "X-F1-Review": "1",
      ...init.headers,
    },
  });
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try {
      const body = await response.json();
      detail =
        typeof body.detail === "string"
          ? body.detail
          : JSON.stringify(body.detail);
    } catch {
      /* proxy may return HTML */
    }
    throw new Error(detail);
  }
  return response.json();
}
export const mutate = <T>(path: string, body: unknown = {}, method = "POST") =>
  request<T>(path, { method, body: JSON.stringify(body) });
export const dateLabel = (date: string) =>
  new Date(date).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    timeZone: "UTC",
  });
