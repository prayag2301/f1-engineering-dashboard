"use client";

import React, { Suspense, useEffect, useMemo, useRef, useState } from "react";
import Link from "next/link";
import { staticArchive } from "@/lib/archive";
import { Canvas, ThreeEvent, useThree, useFrame } from "@react-three/fiber";
import {
  ContactShadows,
  Environment,
  Lightformer,
  OrbitControls,
  useGLTF,
} from "@react-three/drei";
import type { OrbitControls as Controls } from "three-stdlib";
import * as THREE from "three";
import type { CarVersion, ViewName } from "@/lib/releases";

export type CameraPose = {
  position: [number, number, number];
  target: [number, number, number];
};
export const CAMERA_PRESETS: Record<ViewName, CameraPose> = {
  three_quarter: { position: [5, 2.6, -7], target: [0, 0.35, 0] },
  front: { position: [0, 1.15, -8], target: [0, 0.35, 0] },
  side: { position: [8, 1.15, 0], target: [0, 0.35, 0] },
  rear: { position: [0, 1.25, 8], target: [0, 0.35, 0] },
};
const AERO_FRAMING: Record<string, CameraPose> = {
  front_wing: { target: [0, 0.18, -2.25], position: [1.7, 1.1, -5.45] },
  floor: { target: [0, 0.18, 0.35], position: [3.6, 2.6, -4.15] },
  rear_wing: { target: [0, 0.66, 2.05], position: [1.6, 1.55, 4.6] },
  diffuser: { target: [0, 0.17, 1.8], position: [1.7, 0.8, 4.1] },
  suspension: { target: [0, 0.35, -1.5], position: [2.6, 1.3, -4.3] },
};
export interface CameraBus {
  listeners: Set<(pose: CameraPose, sender: string) => void>;
  pose: CameraPose;
  viewKey?: string;
}
export function createCameraBus(): CameraBus {
  return { listeners: new Set(), pose: CAMERA_PRESETS.three_quarter };
}

class ModelBoundary extends React.Component<
  { children: React.ReactNode; onError: () => void },
  { failed: boolean }
> {
  state = { failed: false };
  static getDerivedStateFromError() {
    return { failed: true };
  }
  componentDidCatch() {
    this.props.onError();
  }
  render() {
    return this.state.failed ? null : this.props.children;
  }
}

function ContextLossGuard({ onLost }: { onLost: () => void }) {
  const { gl } = useThree();
  useEffect(() => {
    const canvas = gl.domElement;
    canvas.addEventListener("webglcontextlost", onLost);
    // R3F deliberately disposes an old context after unmount. A late event from
    // that canvas must not fail the replacement canvas created by Retry 3D.
    return () => canvas.removeEventListener("webglcontextlost", onLost);
  }, [gl, onLost]);
  return null;
}

function Model({
  url,
  active,
  highlighted,
  onSelect,
  onLoaded,
  neutral,
  isolate,
}: {
  url: string;
  active?: string | null;
  highlighted: string[];
  onSelect?: (component: string) => void;
  onLoaded: () => void;
  neutral: boolean;
  isolate: boolean;
}) {
  const { scene } = useGLTF(url);
  const { invalidate } = useThree();
  const model = useMemo(() => {
    const clone = scene.clone(true);
    clone.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      object.castShadow = true;
      object.receiveShadow = true;
      object.material = Array.isArray(object.material)
        ? object.material.map((m) => m.clone())
        : object.material.clone();
      if (neutral) {
        const originals = Array.isArray(object.material)
          ? object.material
          : [object.material];
        const clay = originals.map((m) => {
          const dark = /rubber|intake|cockpit|inset/i.test(
            m.name + " " + object.name,
          );
          m.dispose();
          return new THREE.MeshStandardMaterial({
            color: dark ? "#252a30" : "#b4bdc6",
            roughness: 0.62,
            metalness: 0,
            side: THREE.DoubleSide,
          });
        });
        object.material = Array.isArray(object.material) ? clay : clay[0];
      }
      if (
        /flow_line|turquoise_nose_line|upper_turquoise_sweep/.test(object.name)
      ) {
        (Array.isArray(object.material)
          ? object.material
          : [object.material]
        ).forEach((m) => {
          m.polygonOffset = true;
          m.polygonOffsetFactor = -1;
          m.polygonOffsetUnits = -1;
        });
      }
    });
    return clone;
  }, [scene, neutral]);
  useEffect(() => {
    model.traverse((object) => {
      if (!(object instanceof THREE.Mesh)) return;
      const component = object.userData.component ?? object.name.split(".")[0];
      const paint = /flow_line|turquoise_nose_line|upper_turquoise_sweep/.test(
        object.name,
      );
      object.visible =
        !(neutral && paint) && (!isolate || !active || component === active);
      const materials = Array.isArray(object.material)
        ? object.material
        : [object.material];
      materials.forEach((m: THREE.Material) => {
        if (!(m instanceof THREE.MeshStandardMaterial)) return;
        if (!m.userData.baseEmissive)
          m.userData.baseEmissive = m.emissive.clone();
        m.emissive.copy(m.userData.baseEmissive);
        m.emissiveIntensity = 1;
        if (component === active || highlighted.includes(component)) {
          m.emissive.set(component === active ? "#55cdbc" : "#cc9f51");
          m.emissiveIntensity = 0.25;
        }
      });
    });
    invalidate();
  }, [model, active, highlighted, neutral, isolate, invalidate]);
  useEffect(() => {
    onLoaded();
    return () =>
      model.traverse((o) => {
        if (o instanceof THREE.Mesh)
          (Array.isArray(o.material) ? o.material : [o.material]).forEach((m) =>
            m.dispose(),
          );
      });
  }, [model, onLoaded]);
  const select = (event: ThreeEvent<MouseEvent>) => {
    event.stopPropagation();
    let object: THREE.Object3D | null = event.object;
    while (object) {
      if (object.userData.component) {
        onSelect?.(object.userData.component);
        return;
      }
      object = object.parent;
    }
  };
  return <primitive object={model} onClick={select} dispose={null} />;
}

function CameraRig({
  preset,
  resetIndex,
  focus,
  focusComponent,
  bus,
  id,
}: {
  preset: ViewName;
  resetIndex: number;
  focus?: [number, number, number] | null;
  focusComponent?: string | null;
  bus?: CameraBus;
  id: string;
}) {
  const controls = useRef<Controls>(null);
  const { camera, invalidate, gl, size } = useThree();
  useFrame(() => {
    gl.domElement.dataset.renderFrame = String(gl.info.render.frame);
  });
  useEffect(() => {
    if (
      camera instanceof THREE.PerspectiveCamera &&
      size.width &&
      size.height
    ) {
      // Match the studio's horizontal lens framing across wide and narrow panels.
      camera.fov = THREE.MathUtils.radToDeg(
        2 *
          Math.atan(
            Math.tan(THREE.MathUtils.degToRad(19)) / (size.width / size.height),
          ),
      );
      camera.updateProjectionMatrix();
      invalidate();
    }
  }, [camera, size.width, size.height, invalidate]);
  const applying = useRef(false);
  useEffect(() => {
    gl.domElement.tabIndex = 0;
    gl.domElement.setAttribute(
      "aria-label",
      "Car orbit view. Arrow keys pan; camera preset buttons change viewing angle.",
    );
    const orbit = controls.current;
    orbit?.listenToKeyEvents(gl.domElement);
    return () => orbit?.stopListenToKeyEvents();
  }, [gl]);
  useEffect(() => {
    // Aero assemblies span much more of the car than a nose/inlet detail.
    // Frame the complete assembly instead of clipping it at the old close-up distance.
    const aero = focus ? AERO_FRAMING[focusComponent ?? ""] : undefined;
    const target = aero?.target ?? focus ?? CAMERA_PRESETS[preset].target;
    let position: [number, number, number] = focus
      ? (aero?.position ?? [
          focus[0] + 1.45,
          focus[1] + 0.65,
          focus[2] + (focus[2] > 1 ? 1.65 : -1.65),
        ])
      : CAMERA_PRESETS[preset].position;
    if (aero && preset !== "three_quarter") {
      const distance = new THREE.Vector3(...aero.position).distanceTo(
        new THREE.Vector3(...aero.target),
      );
      position = new THREE.Vector3(...CAMERA_PRESETS[preset].position)
        .sub(new THREE.Vector3(...CAMERA_PRESETS[preset].target))
        .normalize()
        .multiplyScalar(distance)
        .add(new THREE.Vector3(...target))
        .toArray() as [number, number, number];
    }
    const viewKey = `${preset}:${resetIndex}:${focusComponent ?? ""}:${focus?.join(",") ?? "complete"}`;
    const pose = bus?.viewKey === viewKey ? bus.pose : { position, target };
    if (bus) {
      bus.viewKey = viewKey;
      bus.pose = pose;
    }
    applying.current = true;
    camera.position.set(...pose.position);
    controls.current?.target.set(...pose.target);
    controls.current?.update();
    applying.current = false;
    invalidate();
  }, [camera, preset, resetIndex, focus, focusComponent, bus, invalidate]);
  useEffect(() => {
    if (!bus) return;
    const receive = (pose: CameraPose, sender: string) => {
      if (sender === id) return;
      applying.current = true;
      camera.position.set(...pose.position);
      controls.current?.target.set(...pose.target);
      controls.current?.update();
      applying.current = false;
      invalidate();
    };
    bus.listeners.add(receive);
    receive(bus.pose, "initial");
    return () => {
      bus.listeners.delete(receive);
    };
  }, [bus, id, camera, invalidate]);
  const changed = () => {
    // A small DOM diagnostic makes synchronized camera behavior measurable in browser checks.
    gl.domElement.dataset.cameraPosition = camera.position
      .toArray()
      .map((v) => v.toFixed(4))
      .join(",");
    if (!bus || applying.current || !controls.current) return;
    const pose: CameraPose = {
      position: camera.position.toArray() as CameraPose["position"],
      target: controls.current.target.toArray() as CameraPose["target"],
    };
    bus.pose = pose;
    bus.listeners.forEach((listener) => listener(pose, id));
  };
  return (
    <OrbitControls
      ref={controls}
      makeDefault
      enableDamping
      dampingFactor={0.09}
      minDistance={1.3}
      maxDistance={13}
      maxPolarAngle={Math.PI * 0.49}
      onChange={changed}
    />
  );
}

export interface CarViewerProps {
  version: CarVersion | null;
  preset?: ViewName;
  resetIndex?: number;
  activeComponent?: string | null;
  onSelectComponent?: (component: string) => void;
  highlighted?: string[];
  focus?: boolean;
  cameraBus?: CameraBus;
  syncId?: string;
  height?: string;
  neutral?: boolean;
  isolate?: boolean;
}

export default function CarViewer(props: CarViewerProps) {
  // Keyed state ensures a failed or slow previous car never appears for another release.
  return <ViewerInstance key={props.version?.id ?? "empty"} {...props} />;
}

function ViewerInstance({
  version,
  preset = "three_quarter",
  resetIndex = 0,
  activeComponent,
  onSelectComponent,
  highlighted = [],
  focus = false,
  cameraBus,
  syncId = "car",
  height = "620px",
  neutral = false,
  isolate = false,
}: CarViewerProps) {
  const [failed, setFailed] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [attempt, setAttempt] = useState(0);
  const url = version?.manifest.assets.glb?.url;
  const still =
    version?.manifest.assets[`preview_${preset}`]?.url ??
    version?.manifest.assets.preview_three_quarter?.url;
  const onLoaded = React.useCallback(() => setLoaded(true), []);
  const focusTarget =
    focus && activeComponent
      ? version?.manifest.components[activeComponent]?.anchor
      : null;
  useEffect(() => {
    if (!url) return;
    const timeout = window.setTimeout(() => setFailed(true), 45000);
    if (loaded) window.clearTimeout(timeout);
    return () => window.clearTimeout(timeout);
  }, [url, attempt, loaded]);
  const retry = () => {
    if (url) useGLTF.clear(url);
    setFailed(false);
    setLoaded(false);
    setAttempt((v) => v + 1);
  };
  return (
    <div
      className="car-stage"
      data-material-mode={neutral ? "shape" : "livery"}
      data-isolated-component={isolate ? (activeComponent ?? "") : ""}
      style={{ height }}
      aria-label={
        version
          ? `${version.team_key} ${version.label}, interactive 3D viewer`
          : "Car viewer"
      }
    >
      {still && (!loaded || failed) && (
        <img
          className="car-stage__poster"
          src={still}
          alt={`${version?.label} studio ${preset.replaceAll("_", " ")} view`}
        />
      )}
      {!url && (
        <div className="stage-message">
          <span className="eyebrow">Awaiting a reviewed release</span>
          <h2>The next view starts with evidence.</h2>
          <p>
            A car appears here when its geometry and references have been
            reviewed.
          </p>
          <Link href={staticArchive ? "/about" : "/review"} className="button">
            {staticArchive
              ? "How releases are reviewed ↗"
              : "Open review studio ↗"}
          </Link>
        </div>
      )}
      {url && !failed && (
        <ModelBoundary key={attempt} onError={() => setFailed(true)}>
          <Canvas
            dpr={[1, 1.5]}
            frameloop="demand"
            shadows
            camera={{ position: [5, 2.6, -7], fov: 38, near: 0.05, far: 100 }}
            gl={{ antialias: true, toneMapping: THREE.ACESFilmicToneMapping }}
          >
            <ContextLossGuard onLost={() => setFailed(true)} />
            <color attach="background" args={["#14191e"]} />
            <ambientLight intensity={0.18} />
            <directionalLight
              position={[3, 6, -3]}
              intensity={2.5}
              castShadow
              shadow-mapSize={[2048, 2048]}
              shadow-camera-left={-4}
              shadow-camera-right={4}
              shadow-camera-top={4}
              shadow-camera-bottom={-4}
              shadow-bias={-0.0003}
            />
            <Environment resolution={256}>
              <Lightformer
                position={[0, 5, -1]}
                rotation={[Math.PI / 2, 0, 0]}
                scale={[7, 3, 1]}
                intensity={3}
                color="#fff4e8"
              />
              <Lightformer
                position={[-4, 2, 0]}
                rotation={[0, Math.PI / 2, 0]}
                scale={[3, 6, 1]}
                intensity={2}
                color="#dae8ff"
              />
              <Lightformer
                position={[3, 3, 4]}
                rotation={[0, Math.PI, 0]}
                scale={[5, 2, 1]}
                intensity={4}
              />
            </Environment>
            <Suspense fallback={null}>
              <Model
                url={url}
                active={activeComponent}
                highlighted={highlighted}
                onSelect={onSelectComponent}
                onLoaded={onLoaded}
                neutral={neutral}
                isolate={isolate}
              />
            </Suspense>
            <mesh
              rotation={[-Math.PI / 2, 0, 0]}
              position={[0, -0.008, 0]}
              receiveShadow
            >
              <planeGeometry args={[100, 100]} />
              <meshStandardMaterial
                color="#161c22"
                roughness={0.48}
                metalness={0.15}
              />
            </mesh>
            {!isolate && (
              <ContactShadows
                position={[0, -0.003, 0]}
                opacity={0.65}
                scale={12}
                blur={2.5}
                far={1.5}
                frames={1}
                resolution={512}
              />
            )}
            <CameraRig
              preset={preset}
              resetIndex={resetIndex}
              focus={focusTarget}
              focusComponent={focus ? activeComponent : null}
              bus={cameraBus}
              id={syncId}
            />
          </Canvas>
        </ModelBoundary>
      )}
      {url && !loaded && !failed && (
        <div className="loading-pill" role="status">
          Loading car surfaces…
        </div>
      )}
      {failed && (
        <div className="stage-error" role="alert">
          <p>
            Interactive model unavailable
            {still ? "; showing this release’s studio render." : "."}
          </p>
          <button onClick={retry}>Retry 3D</button>
        </div>
      )}
      {loaded && !failed && (
        <div className="stage-caption">
          <span>DRAG TO ORBIT · SCROLL TO INSPECT</span>
          <span>1 UNIT = 1 METRE</span>
        </div>
      )}
    </div>
  );
}
