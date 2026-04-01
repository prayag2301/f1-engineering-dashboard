"use client";

import { Suspense } from "react";
import { Canvas } from "@react-three/fiber";
import {
  OrbitControls,
  Environment,
  ContactShadows,
  Grid,
  useGLTF,
} from "@react-three/drei";

function GLBScene({ url }: { url: string }) {
  const { scene } = useGLTF(url);
  return <primitive object={scene} />;
}

interface ModelViewerProps {
  url: string;
  height?: number;
}

export function ModelViewer({ url, height = 500 }: ModelViewerProps) {
  return (
    <div
      style={{
        width: "100%",
        height,
        background: "#0a0a0a",
        borderRadius: 8,
        overflow: "hidden",
      }}
    >
      <Canvas
        camera={{ position: [2, 0.6, 2], fov: 45 }}
        style={{ width: "100%", height: "100%" }}
      >
        <ambientLight intensity={0.5} />
        <directionalLight position={[5, 8, 5]} intensity={1.4} castShadow />
        <directionalLight position={[-4, 4, -4]} intensity={0.5} />
        <Suspense fallback={null}>
          <GLBScene url={url} />
          <ContactShadows
            opacity={0.4}
            scale={4}
            blur={1.5}
            far={2}
            position={[0, 0, 0]}
          />
        </Suspense>
        <Grid
          args={[10, 10]}
          position={[0, -0.001, 0]}
          cellColor="#1a1a1a"
          sectionColor="#2a2a2a"
          fadeDistance={6}
          infiniteGrid
        />
        <OrbitControls
          enablePan={false}
          minDistance={0.5}
          maxDistance={6}
          target={[0, 0.15, 0]}
          autoRotate
          autoRotateSpeed={0.6}
        />
        <Environment preset="studio" />
      </Canvas>
    </div>
  );
}
