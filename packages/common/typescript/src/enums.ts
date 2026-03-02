export const UpgradeCategory = {
  AERO: "Aero",
  MECHANICAL: "Mechanical",
  COOLING: "Cooling",
  FLOOR: "Floor",
  SUSPENSION: "Suspension",
  POWER_UNIT: "Power Unit",
  OTHER: "Other",
} as const;
export type UpgradeCategory =
  (typeof UpgradeCategory)[keyof typeof UpgradeCategory];

export const ComponentZone = {
  FRONT_WING: "Front Wing",
  REAR_WING: "Rear Wing",
  FLOOR: "Floor",
  FLOOR_EDGE: "Floor Edge",
  SIDEPOD: "Sidepod",
  DIFFUSER: "Diffuser",
  BARGEBOARD: "Bargeboard",
  ENGINE_COVER: "Engine Cover",
  BRAKE_DUCT: "Brake Duct",
  SUSPENSION_ARM: "Suspension Arm",
  HALO: "Halo",
  NOSE: "Nose",
  OTHER: "Other",
} as const;
export type ComponentZone =
  (typeof ComponentZone)[keyof typeof ComponentZone];
