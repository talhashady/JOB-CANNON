"use client";

import { Canvas, useFrame } from "@react-three/fiber";
import {
  Float,
  Environment,
  MeshDistortMaterial,
  GradientTexture,
  Sparkles,
} from "@react-three/drei";
import { Suspense, useRef } from "react";
import type { Mesh, Group } from "three";

/**
 * A cinematic 3D hero: a slowly morphing "career orb" orbited by smaller
 * gem-like agents, wrapped in floating sparkles. Designed to feel premium and
 * alive without overwhelming the content. Degrades gracefully on low-power
 * devices via dpr clamping and lazy Suspense.
 */

const CAMERA = { position: [0, 0, 8] as [number, number, number], fov: 45 };
const GL = { antialias: true, alpha: true };
const GRADIENT_STOPS = [0, 0.45, 1];
const GRADIENT_COLORS = ["#8b5cf6", "#d946ef", "#22d3ee"];

function CareerOrb() {
  const mesh = useRef<Mesh>(null);
  useFrame((state) => {
    if (!mesh.current) return;
    const t = state.clock.getElapsedTime();
    mesh.current.rotation.y = t * 0.12;
    mesh.current.rotation.z = Math.sin(t * 0.1) * 0.15;
  });
  return (
    <Float speed={1.4} rotationIntensity={0.6} floatIntensity={1.2}>
      <mesh ref={mesh} scale={2.1}>
        <icosahedronGeometry args={[1, 24]} />
        <MeshDistortMaterial
          distort={0.42}
          speed={1.6}
          roughness={0.08}
          metalness={0.9}
          envMapIntensity={1.2}
        >
          <GradientTexture stops={GRADIENT_STOPS} colors={GRADIENT_COLORS} />
        </MeshDistortMaterial>
      </mesh>
    </Float>
  );
}

function AgentSatellites() {
  const group = useRef<Group>(null);
  useFrame((state) => {
    if (group.current) group.current.rotation.y = state.clock.getElapsedTime() * 0.25;
  });
  const count = 8;
  return (
    <group ref={group}>
      {Array.from({ length: count }).map((_, i) => {
        const angle = (i / count) * Math.PI * 2;
        const r = 3.4;
        const pos: [number, number, number] = [
          Math.cos(angle) * r,
          Math.sin(angle * 1.3) * 0.8,
          Math.sin(angle) * r,
        ];
        return (
          <Float key={i} speed={2} rotationIntensity={1.5} floatIntensity={1.5}>
            <mesh position={pos} scale={0.28}>
              <octahedronGeometry args={[1, 0]} />
              <meshStandardMaterial
                color={i % 2 === 0 ? "#22d3ee" : "#d946ef"}
                emissive={i % 2 === 0 ? "#0891b2" : "#a21caf"}
                emissiveIntensity={0.6}
                roughness={0.2}
                metalness={0.8}
              />
            </mesh>
          </Float>
        );
      })}
    </group>
  );
}

export default function Scene3D() {
  const dpr: [number, number] = [1, 1.8];
  return (
    <Canvas className="!absolute inset-0" dpr={dpr} camera={CAMERA} gl={GL}>
      <Suspense fallback={null}>
        <ambientLight intensity={0.4} />
        <directionalLight position={[5, 5, 5]} intensity={1.4} color="#c4b5fd" />
        <pointLight position={[-6, -3, -4]} intensity={2} color="#22d3ee" />
        <CareerOrb />
        <AgentSatellites />
        <Sparkles count={120} scale={12} size={2.5} speed={0.4} color="#a5b4fc" opacity={0.6} />
        <Environment preset="city" />
      </Suspense>
    </Canvas>
  );
}
