export type ComponentZone =
  | "Front Wing"
  | "Rear Wing"
  | "Floor"
  | "Floor Edge"
  | "Sidepod"
  | "Diffuser"
  | "Bargeboard"
  | "Engine Cover"
  | "Brake Duct"
  | "Suspension Arm"
  | "Halo"
  | "Nose"
  | "Other";

export type Vec3 = [number, number, number];

export interface ZoneAnchor {
  position: Vec3;
  cameraTarget: Vec3;
  cameraOffset: Vec3;
}

export const ZONE_ANCHORS: Record<ComponentZone, ZoneAnchor> = {
  "Front Wing":      { position: [0.0,  0.38, -2.32], cameraTarget: [0.0, 0.22, -2.28], cameraOffset: [2.2, 1.2, -4.2] },
  "Rear Wing":       { position: [0.0,  1.22,  2.05], cameraTarget: [0.0, 0.93,  2.03], cameraOffset: [2.0, 1.6,  4.8] },
  Floor:             { position: [0.55, 0.22, -0.10], cameraTarget: [0.0, 0.12, -0.10], cameraOffset: [4.2, 0.8,  0.0] },
  "Floor Edge":      { position: [0.92, 0.22,  0.20], cameraTarget: [0.8, 0.12,  0.20], cameraOffset: [4.6, 1.0, -0.6] },
  Sidepod:           { position: [0.72, 0.52,  0.25], cameraTarget: [0.44, 0.30, 0.25], cameraOffset: [4.0, 1.2, -1.0] },
  Diffuser:          { position: [0.0,  0.52,  2.45], cameraTarget: [0.0, 0.18,  2.00], cameraOffset: [1.6, 1.0,  4.8] },
  Bargeboard:        { position: [0.70, 0.55, -0.80], cameraTarget: [0.50, 0.30, -0.80], cameraOffset: [3.6, 1.3, -2.6] },
  "Engine Cover":    { position: [0.0,  1.10,  0.70], cameraTarget: [0.0, 0.73,  0.70], cameraOffset: [3.2, 1.8,  2.8] },
  "Brake Duct":      { position: [0.95, 0.60, -1.80], cameraTarget: [0.72, 0.34, -1.80], cameraOffset: [3.8, 1.4, -3.2] },
  "Suspension Arm":  { position: [0.75, 0.72, -1.80], cameraTarget: [0.52, 0.35, -1.80], cameraOffset: [3.6, 1.6, -3.4] },
  Halo:              { position: [0.0,  1.15, -0.15], cameraTarget: [0.0, 0.82, -0.15], cameraOffset: [2.4, 1.6, -2.6] },
  Nose:              { position: [0.0,  0.62, -1.70], cameraTarget: [0.0, 0.29, -1.62], cameraOffset: [2.6, 1.3, -3.6] },
  Other:             { position: [0.0,  1.00,  0.00], cameraTarget: [0.0, 0.40,  0.00], cameraOffset: [3.6, 1.8,  4.6] },
};

export function anchorForZone(zone: string | null | undefined): ZoneAnchor {
  if (!zone) return ZONE_ANCHORS.Other;
  return ZONE_ANCHORS[zone as ComponentZone] ?? ZONE_ANCHORS.Other;
}

export function confidenceTier(c: number): "high" | "medium" | "low" {
  if (c >= 0.75) return "high";
  if (c >= 0.5) return "medium";
  return "low";
}

export const CONFIDENCE_COLORS = {
  high: "#22c55e",
  medium: "#f59e0b",
  low: "#ef4444",
} as const;
