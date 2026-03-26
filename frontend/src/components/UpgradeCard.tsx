import type { Upgrade } from "@/lib/api";

function categoryClass(category: string): string {
  const map: Record<string, string> = {
    Aero: "badge--aero",
    Mechanical: "badge--mechanical",
    Cooling: "badge--cooling",
    Floor: "badge--floor",
    Suspension: "badge--suspension",
    "Power Unit": "badge--power-unit",
    Other: "badge--other",
  };
  return map[category] ?? "badge--confidence";
}

export default function UpgradeCard({
  upgrade,
  onOpenFocus,
}: {
  upgrade: Upgrade;
  onOpenFocus?: (upgrade: Upgrade) => void;
}) {
  return (
    <button
      type="button"
      className={`card ${onOpenFocus ? "card--interactive" : ""}`}
      onClick={() => onOpenFocus?.(upgrade)}
    >
      <div className="card__header">
        <span className="card__team">{upgrade.team?.name ?? "—"}</span>
        <span className="card__race">{upgrade.race?.name ?? "—"}</span>
      </div>

      <div className="card__component">
        {upgrade.component?.name ?? "Unknown Component"}
      </div>

      <p className="card__description">{upgrade.description}</p>

      {upgrade.expected_effect && (
        <p className="card__description" style={{ fontStyle: "italic" }}>
          → {upgrade.expected_effect}
        </p>
      )}

      <div className="card__meta">
        <span className={`badge ${categoryClass(upgrade.category)}`}>
          {upgrade.category}
        </span>
        <span className="badge badge--confidence">
          Confidence: {(upgrade.confidence * 100).toFixed(0)}%
        </span>
        {upgrade.component?.zone && (
          <span className="badge badge--confidence">
            {upgrade.component.zone}
          </span>
        )}
      </div>
    </button>
  );
}
