"use client";

import { Html } from "@react-three/drei";
import type { Upgrade } from "@/lib/api";
import {
  anchorForZone,
  confidenceTier,
  CONFIDENCE_COLORS,
  type Vec3,
} from "@/lib/annotationAnchors";

interface Props {
  upgrade: Upgrade;
  active: boolean;
  onSelect: (id: string) => void;
  position?: Vec3;
}

export default function UpgradeAnnotation({ upgrade, active, onSelect, position }: Props) {
  const zone = upgrade.component?.zone ?? "Other";
  const anchor = anchorForZone(zone);
  const pos = position ?? anchor.position;
  const tier = confidenceTier(upgrade.confidence);
  const tierColor = CONFIDENCE_COLORS[tier];

  return (
    <group position={pos}>
      <Html
        center
        distanceFactor={8}
        occlude
        zIndexRange={[10, 0]}
        style={{ pointerEvents: "auto" }}
      >
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onSelect(upgrade.id);
          }}
          className={`annotation ${active ? "annotation--active" : ""}`}
          style={{
            borderColor: active ? tierColor : "#2a2a2a",
            boxShadow: active ? `0 0 0 2px ${tierColor}66` : "none",
          }}
        >
          <span className="annotation__pin" style={{ background: tierColor }} />
          <div className="annotation__body">
            <div className="annotation__zone">{zone}</div>
            {active && (
              <>
                <div className="annotation__desc">{upgrade.description}</div>
                <div className="annotation__meta">
                  <span className="annotation__badge">{upgrade.category}</span>
                  <span className="annotation__conf" style={{ color: tierColor }}>
                    {(upgrade.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                {upgrade.source && (
                  <a
                    href={upgrade.source}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="annotation__source"
                    onClick={(e) => e.stopPropagation()}
                  >
                    source ↗
                  </a>
                )}
              </>
            )}
          </div>
        </button>
      </Html>
    </group>
  );
}
