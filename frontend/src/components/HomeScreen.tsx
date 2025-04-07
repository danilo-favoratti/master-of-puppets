// HomeScreen.tsx

import React, { useState, useEffect, useRef, Suspense, useMemo } from 'react';
import * as THREE from 'three'; // Import THREE
import { Canvas, useFrame } from '@react-three/fiber'; // Import Canvas, useFrame
import { OrbitControls, Text } from '@react-three/drei'; // Import Text

interface HomeScreenProps {
  themeIsSelected: boolean;
  isConnected: boolean;
  themeSelect: (theme: string) => void;
  socketMessage: string | null;
}

// Define constants for the portal (adjust as needed for homepage)
const PORTAL_POS_X = 0;
const PORTAL_POS_Y = 1.2; // Slightly higher position
const PORTAL_POS_Z = 0;

// Gist Adaptation: HomePagePortal Component (moved here)
const HomePagePortal = () => {
  const portalGroupRef = useRef<THREE.Group>(null);
  const particlesRef = useRef<THREE.Points>(null);

  const portalOuterRadius = 1.5;
  const portalTubeRadius = 0.2;
  const portalInnerRadius = 1.3;

  const portalColor = useMemo(() => new THREE.Color(0x00ff00), []); // Green

  const particleCount = 500;
  const { positions, colors } = useMemo(() => {
    const positions = new Float32Array(particleCount * 3);
    const colors = new Float32Array(particleCount * 3);
    const color = new THREE.Color();

    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3;
      const angle = Math.random() * Math.PI * 2;
      const radius = portalOuterRadius + (Math.random() - 0.5) * (portalTubeRadius * 2);
      positions[i3] = Math.cos(angle) * radius;
      positions[i3 + 1] = Math.sin(angle) * radius;
      positions[i3 + 2] = (Math.random() - 0.5) * (portalTubeRadius * 2);

      color.setRGB(0, 0.8 + Math.random() * 0.2, 0);
      colors[i3] = color.r;
      colors[i3 + 1] = color.g;
      colors[i3 + 2] = color.b;
    }
    return { positions, colors };
  }, [particleCount, portalOuterRadius, portalTubeRadius]);

  useFrame(({ clock }) => {
    if (particlesRef.current) {
      const geomPositions = particlesRef.current.geometry.attributes.position.array as Float32Array;
      const time = clock.getElapsedTime();
      for (let i = 0; i < geomPositions.length; i += 3) {
        geomPositions[i + 2] += 0.005 * Math.sin(time * 2 + i);
        const radius = Math.sqrt(geomPositions[i]**2 + geomPositions[i+1]**2);
        const angle = Math.atan2(geomPositions[i+1], geomPositions[i]);
        const newAngle = angle + 0.001;
        geomPositions[i] = Math.cos(newAngle) * radius;
        geomPositions[i+1] = Math.sin(newAngle) * radius;
      }
      particlesRef.current.geometry.attributes.position.needsUpdate = true;
    }
  });

  return (
    <group ref={portalGroupRef} position={[PORTAL_POS_X, PORTAL_POS_Y, PORTAL_POS_Z]} rotation={[0.35, 0, 0]}>
      <mesh>
        <torusGeometry args={[portalOuterRadius, portalTubeRadius, 16, 100]} />
        <meshPhongMaterial
          color={portalColor}
          emissive={portalColor}
          transparent
          opacity={0.8}
        />
      </mesh>
      <mesh>
        <circleGeometry args={[portalInnerRadius, 32]} />
        <meshBasicMaterial
          color={portalColor}
          transparent
          opacity={0.5}
          side={THREE.DoubleSide}
        />
      </mesh>
      <points ref={particlesRef}>
        <bufferGeometry attach="geometry">
          <bufferAttribute
            attach="attributes-position"
            array={positions}
            count={particleCount}
            itemSize={3}
          />
          <bufferAttribute
            attach="attributes-color"
            array={colors}
            count={particleCount}
            itemSize={3}
          />
        </bufferGeometry>
        <pointsMaterial
          attach="material"
          size={0.02}
          vertexColors
          transparent
          opacity={0.6}
          sizeAttenuation
        />
      </points>
    </group>
  );
};

const HomeScreen: React.FC<HomeScreenProps> = ({
  themeIsSelected,
  isConnected,
  themeSelect,
  socketMessage,
}) => {
  // State to manage loading indicators for buttons
  const [loadingTheme, setLoadingTheme] = useState<string | null>(null);

  const handleThemeClick = (themeName: string) => {
    if (isConnected && !themeIsSelected && !loadingTheme) {
      setLoadingTheme(themeName); // Set loading for this theme
      themeSelect(themeName);
    }
  };

  // Reset loading state if connection changes or selection completes
  useEffect(() => {
    if (!isConnected || themeIsSelected) {
      setLoadingTheme(null);
    }
  }, [isConnected, themeIsSelected]);

  return (
    <div className="home-screen">
      <div className="canvas-container">
        <Canvas camera={{ position: [0, 1.5, 5], fov: 60 }}> {/* Adjusted fov */}
          <ambientLight intensity={0.7} />
          <pointLight position={[10, 10, 10]} intensity={1} />
          <Suspense fallback={null}>
            <HomePagePortal />
            <Text
              position={[0, PORTAL_POS_Y + 2.2, 0]} // Position text above portal
              color="#ffffff"
              anchorX="center"
              anchorY="middle"
              fontSize={0.2}
              font="/fonts/Roboto-Bold.ttf" // Example: ensure font path is correct
            >
              Master of Puppets
            </Text>
            <Text
              position={[0, PORTAL_POS_Y + 1.8, 0]} // Position text above portal
              color="#cccccc"
              anchorX="center"
              anchorY="middle"
              fontSize={0.1}
              font="/fonts/Roboto-Regular.ttf" // Example: ensure font path is correct
            >
              Select a Theme to Begin Your Adventure
            </Text>
          </Suspense>
          <OrbitControls enabled={false} /> {/* Disable controls */}
        </Canvas>
      </div>

      <div className="theme-selection-container">
        <div className="theme-button-group">
          {/* --- Theme Buttons --- */}
          <button
            onClick={() => handleThemeClick("Abandoned_Prisioner")} // Use correct theme name
            className="theme-button"
            disabled={!isConnected || !!loadingTheme}
          >
            {loadingTheme === "Abandoned_Prisioner" ? "Loading..." : "Abandoned Prisoner"}
          </button>
          <button
            onClick={() => handleThemeClick("Mysterious Island Survival")} // Use correct theme name
            className="theme-button"
            disabled={!isConnected || !!loadingTheme}
          >
            {loadingTheme === "Mysterious Island Survival" ? "Loading..." : "Mysterious Island"}
          </button>
          {/* Add more buttons here following the pattern */}
        </div>

        <div className="status-message">
          {!isConnected
            ? "Connecting to server..."
            : socketMessage
            ? socketMessage
            : "Connected. Please select a theme."
          }
        </div>
      </div>
    </div>
  );
};

export default HomeScreen;
