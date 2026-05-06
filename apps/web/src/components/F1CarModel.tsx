"use client";

import { useEffect, useMemo, useRef } from "react";
import { useFrame } from "@react-three/fiber";
import * as THREE from "three";
import type { Group } from "three";

export const TEAM_LIVERIES: Record<
  string,
  { primary: string; secondary: string; accent: string }
> = {
  "red-bull":     { primary: "#0C1A3E", secondary: "#FFD700", accent: "#CC0001" },
  ferrari:        { primary: "#E8002D", secondary: "#FFFFFF", accent: "#FFF200" },
  mercedes:       { primary: "#00D2BE", secondary: "#1C1C1C", accent: "#FFFFFF" },
  mclaren:        { primary: "#FF8000", secondary: "#0F0F0F", accent: "#FFFFFF" },
  "aston-martin": { primary: "#006F62", secondary: "#CEDC00", accent: "#FFFFFF" },
  alpine:         { primary: "#0093CC", secondary: "#E40078", accent: "#FFFFFF" },
  williams:       { primary: "#005AFF", secondary: "#FFFFFF", accent: "#E40020" },
  "racing-bulls": { primary: "#1E41B7", secondary: "#CC0000", accent: "#FFFFFF" },
  haas:           { primary: "#E8002D", secondary: "#FFFFFF", accent: "#B6BABD" },
  audi:           { primary: "#1C1C1C", secondary: "#BF0000", accent: "#FFFFFF" },
  cadillac:       { primary: "#0A0A0A", secondary: "#B5956A", accent: "#FFFFFF" },
};

const DEFAULT_LIVERY = TEAM_LIVERIES["red-bull"];

export type HighlightMap = Record<string, string>;

export type ModelQuality = "high" | "medium" | "low";

export interface F1CarModelProps {
  teamId?: string;
  autoRotate?: boolean;
  highlightedZones?: HighlightMap;
  quality?: ModelQuality;
  drsOpen?: boolean;
}

const SEGMENTS: Record<ModelQuality, { cyl: number; rim: number }> = {
  high:   { cyl: 32, rim: 24 },
  medium: { cyl: 20, rim: 16 },
  low:    { cyl: 12, rim: 10 },
};

function ZoneGroup({
  zone,
  highlight,
  children,
}: {
  zone: string;
  highlight?: string;
  children: React.ReactNode;
}) {
  const groupRef = useRef<Group>(null);
  const originalsRef = useRef<Map<THREE.Mesh, THREE.Material | THREE.Material[]>>(new Map());

  useEffect(() => {
    const group = groupRef.current;
    if (!group) return;
    const originals = originalsRef.current;

    if (highlight) {
      const color = new THREE.Color(highlight);
      group.traverse((obj) => {
        if ((obj as THREE.Mesh).isMesh) {
          const mesh = obj as THREE.Mesh;
          if (!originals.has(mesh)) originals.set(mesh, mesh.material);
          const base = Array.isArray(mesh.material) ? mesh.material[0] : mesh.material;
          const cloned = (base as THREE.MeshStandardMaterial).clone();
          cloned.emissive = color;
          cloned.emissiveIntensity = 0.85;
          mesh.material = cloned;
        }
      });
    } else {
      originals.forEach((mat, mesh) => {
        mesh.material = mat;
      });
      originals.clear();
    }

    return () => {
      originals.forEach((mat, mesh) => {
        mesh.material = mat;
      });
      originals.clear();
    };
  }, [highlight]);

  return (
    <group ref={groupRef} name={`zone:${zone}`} userData={{ zone }}>
      {children}
    </group>
  );
}

export function F1CarModel({
  teamId = "red-bull",
  autoRotate = false,
  highlightedZones,
  quality = "high",
  drsOpen = false,
}: F1CarModelProps) {
  const groupRef = useRef<Group>(null);
  const livery = TEAM_LIVERIES[teamId] ?? DEFAULT_LIVERY;
  const segs = SEGMENTS[quality];
  const mirror = quality !== "low";

  useFrame((_state, delta) => {
    if (autoRotate && groupRef.current) {
      groupRef.current.rotation.y += delta * 0.4;
    }
  });

  const materials = useMemo(() => ({
    body: new THREE.MeshStandardMaterial({ color: livery.primary, roughness: 0.25, metalness: 0.55 }),
    accent: new THREE.MeshStandardMaterial({ color: livery.secondary, roughness: 0.2, metalness: 0.6 }),
    wing: new THREE.MeshStandardMaterial({ color: livery.primary, roughness: 0.2, metalness: 0.5 }),
    tire: new THREE.MeshStandardMaterial({ color: "#1A1A1A", roughness: 0.9, metalness: 0.0 }),
    rim: new THREE.MeshStandardMaterial({
      color: livery.accent !== "#FFFFFF" ? livery.accent : "#C0C0C0",
      roughness: 0.15,
      metalness: 0.85,
    }),
    floor: new THREE.MeshStandardMaterial({ color: "#0D0D0D", roughness: 0.35, metalness: 0.4 }),
    halo: new THREE.MeshStandardMaterial({ color: "#1C1C1C", roughness: 0.2, metalness: 0.8 }),
    sidepod: new THREE.MeshStandardMaterial({ color: livery.secondary, roughness: 0.25, metalness: 0.5 }),
    inlet: new THREE.MeshStandardMaterial({ color: "#080808", roughness: 0.5, metalness: 0.3 }),
  }), [livery]);

  const h = highlightedZones ?? {};

  function Wheel({ x, z, isFront }: { x: number; z: number; isFront: boolean }) {
    const tireRadius = 0.335;
    const tireWidth = isFront ? 0.305 : 0.405;
    return (
      <group position={[x, tireRadius, z]}>
        <mesh material={materials.tire} rotation={[0, 0, Math.PI / 2]} castShadow>
          <cylinderGeometry args={[tireRadius, tireRadius, tireWidth, segs.cyl]} />
        </mesh>
        <mesh material={materials.rim} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.225, 0.225, tireWidth + 0.01, segs.rim]} />
        </mesh>
        <mesh material={materials.rim} position={[x > 0 ? 0.01 : -0.01, 0, 0]} rotation={[0, 0, Math.PI / 2]}>
          <cylinderGeometry args={[0.09, 0.09, 0.03, segs.rim]} />
        </mesh>
      </group>
    );
  }

  return (
    <group ref={groupRef}>
      <ZoneGroup zone="Floor" highlight={h["Floor"]}>
        <mesh material={materials.floor} position={[0, 0.095, -0.1]}>
          <boxGeometry args={[1.65, 0.04, 3.8]} />
        </mesh>
      </ZoneGroup>

      <ZoneGroup zone="Diffuser" highlight={h["Diffuser"]}>
        <mesh material={materials.floor} position={[0, 0.18, 2.0]} rotation={[-0.35, 0, 0]}>
          <boxGeometry args={[1.5, 0.04, 0.8]} />
        </mesh>
      </ZoneGroup>

      <ZoneGroup zone="Monocoque" highlight={h["Monocoque"]}>
        <mesh material={materials.body} position={[0, 0.265, -0.3]}>
          <boxGeometry args={[0.46, 0.28, 1.9]} />
        </mesh>
        <mesh material={materials.body} position={[0, 0.44, -0.35]}>
          <boxGeometry args={[0.24, 0.14, 0.9]} />
        </mesh>
        {mirror && ([-1, 1] as const).map((side) => (
          <group key={side}>
            <mesh material={materials.halo} position={[side * 0.36, 0.55, -0.4]} rotation={[0, side * -0.18, 0]}>
              <boxGeometry args={[0.012, 0.025, 0.18]} />
            </mesh>
            <mesh material={materials.body} position={[side * 0.46, 0.56, -0.45]} rotation={[0, side * -0.22, 0]}>
              <boxGeometry args={[0.05, 0.07, 0.13]} />
            </mesh>
          </group>
        ))}
      </ZoneGroup>

      <ZoneGroup zone="Nose" highlight={h["Nose"]}>
        <mesh material={materials.body} position={[0, 0.29, -1.625]} rotation={[0.06, 0, 0]}>
          <cylinderGeometry args={[0.035, 0.09, 1.55, segs.cyl]} />
        </mesh>
        <mesh material={materials.body} position={[0, 0.32, -2.36]}>
          <sphereGeometry args={[0.05, segs.rim, segs.rim / 2]} />
        </mesh>
      </ZoneGroup>

      <ZoneGroup zone="Sidepod" highlight={h["Sidepod"]}>
        {([-1, 1] as const).map((side) => (
          <group key={side}>
            <mesh material={materials.sidepod} position={[side * 0.44, 0.27, 0.25]}>
              <boxGeometry args={[0.34, 0.38, 1.75]} />
            </mesh>
            <mesh material={materials.inlet} position={[side * 0.44, 0.3, -0.565]}>
              <boxGeometry args={[0.28, 0.22, 0.04]} />
            </mesh>
          </group>
        ))}
      </ZoneGroup>

      <ZoneGroup zone="Engine Cover" highlight={h["Engine Cover"]}>
        <mesh material={materials.accent} position={[0, 0.73, 0.7]}>
          <boxGeometry args={[0.055, 0.72, 1.3]} />
        </mesh>
      </ZoneGroup>

      <ZoneGroup zone="Halo" highlight={h["Halo"]}>
        <mesh material={materials.halo} position={[0, 0.75, 0.1]}>
          <boxGeometry args={[0.38, 0.08, 0.1]} />
        </mesh>
        <mesh material={materials.halo} position={[-0.19, 0.82, 0.1]}>
          <boxGeometry args={[0.06, 0.2, 0.08]} />
        </mesh>
        <mesh material={materials.halo} position={[0.19, 0.82, 0.1]}>
          <boxGeometry args={[0.06, 0.2, 0.08]} />
        </mesh>
        <mesh material={materials.halo} position={[0, 0.52, -0.55]}>
          <cylinderGeometry args={[0.025, 0.025, 0.62, segs.rim / 2]} />
        </mesh>
        <mesh material={materials.halo} position={[0, 0.82, -0.15]}>
          <boxGeometry args={[0.52, 0.04, 0.72]} />
        </mesh>
        <mesh material={materials.halo} position={[-0.26, 0.66, -0.15]}>
          <boxGeometry args={[0.04, 0.34, 0.72]} />
        </mesh>
        <mesh material={materials.halo} position={[0.26, 0.66, -0.15]}>
          <boxGeometry args={[0.04, 0.34, 0.72]} />
        </mesh>
      </ZoneGroup>

      <ZoneGroup zone="Front Wing" highlight={h["Front Wing"]}>
        <mesh material={materials.wing} position={[0, 0.11, -2.28]}>
          <boxGeometry args={[1.8, 0.058, 0.32]} />
        </mesh>
        <mesh material={materials.wing} position={[0, 0.19, -2.23]} rotation={[-0.08, 0, 0]}>
          <boxGeometry args={[1.72, 0.045, 0.24]} />
        </mesh>
        <mesh material={materials.wing} position={[0, 0.26, -2.18]} rotation={[-0.12, 0, 0]}>
          <boxGeometry args={[1.65, 0.038, 0.18]} />
        </mesh>
        <mesh material={materials.accent} position={[0, 0.15, -2.3]}>
          <boxGeometry args={[0.12, 0.2, 0.35]} />
        </mesh>
        <mesh material={materials.accent} position={[-0.9, 0.15, -2.28]}>
          <boxGeometry args={[0.022, 0.2, 0.36]} />
        </mesh>
        <mesh material={materials.accent} position={[0.9, 0.15, -2.28]}>
          <boxGeometry args={[0.022, 0.2, 0.36]} />
        </mesh>
        <mesh material={materials.wing} position={[-0.9, 0.22, -2.28]}>
          <boxGeometry args={[0.22, 0.055, 0.025]} />
        </mesh>
        <mesh material={materials.wing} position={[0.9, 0.22, -2.28]}>
          <boxGeometry args={[0.22, 0.055, 0.025]} />
        </mesh>
      </ZoneGroup>

      <ZoneGroup zone="Rear Wing" highlight={h["Rear Wing"]}>
        <mesh material={materials.wing} position={[0, 0.895, 2.05]}>
          <boxGeometry args={[0.95, 0.065, 0.3]} />
        </mesh>
        <mesh
          material={materials.wing}
          position={[0, drsOpen ? 1.04 : 0.985, drsOpen ? 1.96 : 2.0]}
          rotation={[drsOpen ? -0.55 : -0.1, 0, 0]}
        >
          <boxGeometry args={[0.9, 0.052, 0.24]} />
        </mesh>
        <mesh material={materials.accent} position={[-0.475, 0.895, 2.02]}>
          <boxGeometry args={[0.022, 0.28, 0.34]} />
        </mesh>
        <mesh material={materials.accent} position={[0.475, 0.895, 2.02]}>
          <boxGeometry args={[0.022, 0.28, 0.34]} />
        </mesh>
        <mesh material={materials.wing} position={[0, 0.58, 1.95]}>
          <boxGeometry args={[0.45, 0.04, 0.2]} />
        </mesh>
        <mesh material={materials.accent} position={[-0.2, 0.74, 2.02]}>
          <boxGeometry args={[0.06, 0.28, 0.065]} />
        </mesh>
        <mesh material={materials.accent} position={[0.2, 0.74, 2.02]}>
          <boxGeometry args={[0.06, 0.28, 0.065]} />
        </mesh>
      </ZoneGroup>

      <ZoneGroup zone="Suspension Arm" highlight={h["Suspension Arm"]}>
        <mesh material={materials.halo} position={[-0.52, 0.48, -1.8]} rotation={[0, 0.35, 0.18]}>
          <boxGeometry args={[0.52, 0.025, 0.025]} />
        </mesh>
        <mesh material={materials.halo} position={[0.52, 0.48, -1.8]} rotation={[0, -0.35, -0.18]}>
          <boxGeometry args={[0.52, 0.025, 0.025]} />
        </mesh>
        <mesh material={materials.halo} position={[-0.52, 0.22, -1.8]} rotation={[0, 0.28, -0.08]}>
          <boxGeometry args={[0.56, 0.025, 0.025]} />
        </mesh>
        <mesh material={materials.halo} position={[0.52, 0.22, -1.8]} rotation={[0, -0.28, 0.08]}>
          <boxGeometry args={[0.56, 0.025, 0.025]} />
        </mesh>
        <mesh material={materials.halo} position={[-0.52, 0.48, 1.8]} rotation={[0, -0.28, 0.18]}>
          <boxGeometry args={[0.5, 0.025, 0.025]} />
        </mesh>
        <mesh material={materials.halo} position={[0.52, 0.48, 1.8]} rotation={[0, 0.28, -0.18]}>
          <boxGeometry args={[0.5, 0.025, 0.025]} />
        </mesh>
      </ZoneGroup>

      <ZoneGroup zone="Brake Duct" highlight={h["Brake Duct"]}>
        <mesh material={materials.inlet} position={[-0.72, 0.335, -1.8]}>
          <boxGeometry args={[0.22, 0.2, 0.15]} />
        </mesh>
        <mesh material={materials.inlet} position={[0.72, 0.335, -1.8]}>
          <boxGeometry args={[0.22, 0.2, 0.15]} />
        </mesh>
      </ZoneGroup>

      <Wheel x={-0.88} z={-1.8} isFront={true} />
      <Wheel x={0.88} z={-1.8} isFront={true} />
      <Wheel x={-0.80} z={1.8} isFront={false} />
      <Wheel x={0.80} z={1.8} isFront={false} />
    </group>
  );
}
