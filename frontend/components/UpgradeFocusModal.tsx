"use client";

import type { Upgrade } from "@/lib/api";

type ZoneFocus = {
  label: string;
  transform: string;
  top: string;
  left: string;
};

const TEAM_CAR_IMAGE: Record<string, string> = {
  "Red Bull":
    "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/redbullracing/2025redbullracingcarright.webp",
  Ferrari:
    "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/ferrari/2025ferraricarright.webp",
  Mercedes:
    "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/mercedes/2025mercedescarright.webp",
  McLaren:
    "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/mclaren/2025mclarencarright.webp",
  "Aston Martin":
    "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/astonmartin/2025astonmartincarright.webp",
  Alpine:
    "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/alpine/2025alpinecarright.webp",
  Williams:
    "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/williams/2025williamscarright.webp",
  RB: "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/racingbulls/2025racingbullscarright.webp",
  "Kick Sauber":
    "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/sauber/2025saubercarright.webp",
  Haas:
    "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/haas/2025haascarright.webp",
};

const ZONE_FOCUS: Record<string, ZoneFocus> = {
  "Front Wing": {
    label: "Front Wing Focus",
    transform: "scale(2.5) translate(17%, -3%)",
    top: "58%",
    left: "15%",
  },
  "Suspension Arm": {
    label: "Suspension Focus",
    transform: "scale(2.7) translate(19%, -8%)",
    top: "56%",
    left: "21%",
  },
  "Brake Duct": {
    label: "Brake Duct Focus",
    transform: "scale(2.7) translate(18%, -6%)",
    top: "61%",
    left: "19%",
  },
  Sidepod: {
    label: "Sidepod Focus",
    transform: "scale(2.2) translate(-6%, -4%)",
    top: "45%",
    left: "44%",
  },
  Floor: {
    label: "Floor Focus",
    transform: "scale(2.1) translate(-2%, 8%)",
    top: "66%",
    left: "43%",
  },
  "Floor Edge": {
    label: "Floor Edge Focus",
    transform: "scale(2.2) translate(4%, 7%)",
    top: "66%",
    left: "36%",
  },
  Diffuser: {
    label: "Diffuser Focus",
    transform: "scale(2.4) translate(-28%, 8%)",
    top: "63%",
    left: "78%",
  },
  "Rear Wing": {
    label: "Rear Wing Focus",
    transform: "scale(2.4) translate(-30%, -12%)",
    top: "25%",
    left: "82%",
  },
  "Engine Cover": {
    label: "Engine Cover Focus",
    transform: "scale(2.1) translate(-13%, -20%)",
    top: "31%",
    left: "57%",
  },
};

const UPGRADE_FOCUS_OVERRIDE: Record<string, ZoneFocus> = {
  // McLaren front wing endplate
  "McLaren|Front Wing Endplate": {
    label: "Front Wing Endplate Focus",
    transform: "scale(3.05) translate(24%, -2%)",
    top: "60%",
    left: "14%",
  },
  // Mercedes diffuser strake
  "Mercedes|Diffuser Strake": {
    label: "Diffuser Strake Focus",
    transform: "scale(3.1) translate(-39%, 9%)",
    top: "70%",
    left: "86%",
  },
  // Red Bull suspension fairing
  "Red Bull|Suspension Fairing": {
    label: "Front Suspension Focus",
    transform: "scale(3.2) translate(23%, -5%)",
    top: "56%",
    left: "19%",
  },
  // Red Bull floor edge
  "Red Bull|Floor Edge": {
    label: "Floor Edge Focus",
    transform: "scale(2.75) translate(-2%, 10%)",
    top: "72%",
    left: "42%",
  },
};

function resolveTeamImage(upgrade: Upgrade): string {
  const teamName = upgrade.team?.name ?? "";
  return (
    TEAM_CAR_IMAGE[teamName] ??
    "https://media.formula1.com/image/upload/c_lfill,w_3392/q_auto/v1740000000/common/f1/2025/redbullracing/2025redbullracingcarright.webp"
  );
}

function resolveZoneFocus(upgrade: Upgrade): ZoneFocus {
  const teamName = upgrade.team?.name ?? "";
  const componentName = upgrade.component?.name ?? "";
  const overrideKey = `${teamName}|${componentName}`;
  if (UPGRADE_FOCUS_OVERRIDE[overrideKey]) {
    return UPGRADE_FOCUS_OVERRIDE[overrideKey];
  }

  const zone = upgrade.component?.zone ?? "Other";
  return (
    ZONE_FOCUS[zone] ?? {
      label: "Technical Focus",
      transform: "scale(1.8) translate(0%, 0%)",
      top: "50%",
      left: "50%",
    }
  );
}

export default function UpgradeFocusModal({
  upgrade,
  onClose,
}: {
  upgrade: Upgrade;
  onClose: () => void;
}) {
  const teamImage = resolveTeamImage(upgrade);
  const zoneFocus = resolveZoneFocus(upgrade);

  return (
    <div className="focus-modal__backdrop" onClick={onClose} role="presentation">
      <div className="focus-modal" onClick={(event) => event.stopPropagation()}>
        <div className="focus-modal__header">
          <div>
            <h2 className="focus-modal__title">
              {upgrade.team?.name ?? "Team"} •{" "}
              {upgrade.component?.zone ?? "Upgrade Focus"}
            </h2>
            <p className="focus-modal__subtitle">
              Demo 3D focus viewer with zoomed highlighted upgrade zone.
            </p>
          </div>
          <button className="focus-modal__close" onClick={onClose} type="button">
            Close
          </button>
        </div>

        <div className="focus-modal__content">
          <div className="focus-viewer">
            <img
              src={teamImage}
              alt={`${upgrade.team?.name ?? "F1"} car 3D focus`}
              className="focus-viewer__car"
              style={{ transform: zoneFocus.transform }}
            />
            <div
              className="focus-viewer__hotspot"
              style={{ top: zoneFocus.top, left: zoneFocus.left }}
            >
              {zoneFocus.label}
            </div>
          </div>

          <div className="focus-modal__details">
            <h3>{upgrade.component?.name ?? "Component"}</h3>
            <p>{upgrade.description}</p>
            {upgrade.technical_detail && <p>{upgrade.technical_detail}</p>}
            {upgrade.aero_reasoning && (
              <p>
                <strong>Aero:</strong> {upgrade.aero_reasoning}
              </p>
            )}
            {upgrade.mechanical_reasoning && (
              <p>
                <strong>Mechanical:</strong> {upgrade.mechanical_reasoning}
              </p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
