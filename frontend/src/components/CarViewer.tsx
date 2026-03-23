"use client";
import { Canvas } from "@react-three/fiber";
import { OrbitControls, Environment, useGLTF } from "@react-three/drei";

function Model() {
  // Use a placeholder public model or handle when undefined
  try {
    const { scene } = useGLTF("/models/placeholder-car.glb");
    return <primitive object={scene} />;
  } catch (e) {
    return (
      <mesh>
        <boxGeometry args={[1, 1, 3]} />
        <meshStandardMaterial color="red" />
      </mesh>
    );
  }
}

export default function CarViewer() {
  return (
    <div style={{ height: "100vh", width: "100vw", background: "#1a1a1a" }}>
      <Canvas camera={{ position: [5, 2, 5], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <spotLight position={[10, 10, 10]} angle={0.15} penumbra={1} />
        <Model />
        <OrbitControls makeDefault />
        <Environment preset="city" />
      </Canvas>
    </div>
  );
}
