"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment, ContactShadows, Grid } from "@react-three/drei";
import { F1CarModel } from "./F1CarModel";

export interface CarViewerProps {
  teamId?: string;
  height?: string;
}

function LoadingFallback() {
  return (
    <mesh>
      <boxGeometry args={[0.5, 0.5, 0.5]} />
      <meshStandardMaterial color="#222222" wireframe />
    </mesh>
  );
}

export default function CarViewer({ teamId = "red-bull", height = "600px" }: CarViewerProps) {
  return (
    <div style={{ height, width: "100%", background: "#0a0a0a", borderRadius: "8px", overflow: "hidden" }}>
      <Canvas
        camera={{ position: [5, 2.5, 7], fov: 45, near: 0.1, far: 100 }}
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
          <F1CarModel teamId={teamId} autoRotate={false} />
        </Suspense>

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
          makeDefault
          enablePan={false}
          minDistance={2}
          maxDistance={12}
          minPolarAngle={0.1}
          maxPolarAngle={Math.PI / 2.1}
          target={[0, 0.4, 0]}
        />
      </Canvas>
    </div>
  );
}
