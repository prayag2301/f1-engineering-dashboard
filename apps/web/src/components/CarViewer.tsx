"use client";

import { Suspense, useRef, useEffect } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Environment, ContactShadows, Grid } from "@react-three/drei";
import type { OrbitControls as OrbitControlsImpl } from "three-stdlib";
import * as THREE from "three";
import { F1CarModel, type HighlightMap } from "./F1CarModel";
import UpgradeAnnotation from "./UpgradeAnnotation";
import type { Upgrade } from "@/lib/api";
import { anchorForZone, type Vec3 } from "@/lib/annotationAnchors";

export interface CarViewerProps {
  teamId?: string;
  height?: string;
  upgrades?: Upgrade[];
  activeUpgradeId?: string | null;
  onSelectUpgrade?: (id: string) => void;
  highlightedZones?: HighlightMap;
  focusTarget?: Vec3 | null;
  focusCameraOffset?: Vec3 | null;
}

function LoadingFallback() {
  return (
    <mesh>
      <boxGeometry args={[0.5, 0.5, 0.5]} />
      <meshStandardMaterial color="#222222" wireframe />
    </mesh>
  );
}

const DEFAULT_TARGET: Vec3 = [0, 0.4, 0];
const DEFAULT_CAM: Vec3 = [5, 2.5, 7];

function CameraRig({
  controlsRef,
  focusTarget,
  focusCameraOffset,
}: {
  controlsRef: React.RefObject<OrbitControlsImpl>;
  focusTarget: Vec3 | null | undefined;
  focusCameraOffset: Vec3 | null | undefined;
}) {
  const targetVec = useRef(new THREE.Vector3(...DEFAULT_TARGET));
  const camVec = useRef(new THREE.Vector3(...DEFAULT_CAM));

  useEffect(() => {
    if (focusTarget) targetVec.current.set(...focusTarget);
    if (focusCameraOffset) camVec.current.set(...focusCameraOffset);
  }, [focusTarget, focusCameraOffset]);

  useFrame((state) => {
    const controls = controlsRef.current;
    if (!controls) return;
    const desiredTarget = focusTarget ? targetVec.current : new THREE.Vector3(...DEFAULT_TARGET);
    controls.target.lerp(desiredTarget, 0.08);
    if (focusCameraOffset) {
      state.camera.position.lerp(camVec.current, 0.05);
    }
    controls.update();
  });

  return null;
}

export default function CarViewer({
  teamId = "red-bull",
  height = "600px",
  upgrades = [],
  activeUpgradeId = null,
  onSelectUpgrade,
  highlightedZones,
  focusTarget,
  focusCameraOffset,
}: CarViewerProps) {
  const controlsRef = useRef<OrbitControlsImpl>(null);

  return (
    <div style={{ height, width: "100%", background: "#0a0a0a", borderRadius: "8px", overflow: "hidden" }}>
      <Canvas
        camera={{ position: DEFAULT_CAM, fov: 45, near: 0.1, far: 100 }}
        gl={{ antialias: true, toneMapping: 4 }}
        shadows
      >
        <ambientLight intensity={0.4} />
        <directionalLight
          position={[8, 10, 5]}
          intensity={1.2}
          castShadow
          shadow-mapSize={[2048, 2048]}
          shadow-camera-far={30}
          shadow-camera-left={-8}
          shadow-camera-right={8}
          shadow-camera-top={8}
          shadow-camera-bottom={-8}
        />
        <directionalLight position={[-6, 4, -4]} intensity={0.5} color="#aaddff" />
        <spotLight position={[0, 8, 0]} intensity={0.8} angle={0.6} penumbra={0.5} castShadow />
        <spotLight position={[-4, 3, 6]} intensity={0.4} angle={0.5} penumbra={0.8} />

        <Suspense fallback={<LoadingFallback />}>
          <F1CarModel teamId={teamId} autoRotate={false} highlightedZones={highlightedZones} />
        </Suspense>

        {upgrades.map((u) => {
          const zone = u.component?.zone ?? "Other";
          const anchor = anchorForZone(zone);
          return (
            <UpgradeAnnotation
              key={u.id}
              upgrade={u}
              active={u.id === activeUpgradeId}
              onSelect={(id) => onSelectUpgrade?.(id)}
              position={anchor.position}
            />
          );
        })}

        <ContactShadows position={[0, 0, 0]} opacity={0.55} scale={14} blur={2.5} far={1.2} />
        <Grid
          position={[0, -0.001, 0]}
          args={[20, 20]}
          cellSize={0.5}
          cellThickness={0.5}
          cellColor="#1a1a1a"
          sectionSize={2}
          sectionThickness={1}
          sectionColor="#222222"
          fadeDistance={18}
          fadeStrength={1}
          infiniteGrid
        />
        <Environment preset="studio" />
        <OrbitControls
          ref={controlsRef}
          makeDefault
          enablePan={false}
          minDistance={2}
          maxDistance={12}
          minPolarAngle={0.1}
          maxPolarAngle={Math.PI / 2.1}
          target={DEFAULT_TARGET}
        />
        <CameraRig
          controlsRef={controlsRef}
          focusTarget={focusTarget}
          focusCameraOffset={focusCameraOffset}
        />
      </Canvas>
    </div>
  );
}
