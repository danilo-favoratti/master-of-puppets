import { Text } from "@react-three/drei";
import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import forestSpritesheet from "../assets/spritesheets/forest/gentle forest (48x48 resize) v08.png";

interface ForestTileProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  size?: number;
  tileX: number;
  tileY: number;
  gridX?: number;
  gridY?: number;
  isEmpty?: boolean;
}

const ForestTile = ({
  position = [0, 0, 0],
  scale = [1, 1, 1],
  size = 1,
  tileX = 0,
  tileY = 0,
  gridX = 0,
  gridY = 0,
  isEmpty = true,
}: ForestTileProps) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const rows = 16;
  const cols = 16;
  const [showDebugUi, setShowDebugUi] = useState(false);

  // Escala para o tamanho do tile
  const finalScale = [size, size, scale[2]];

  // Ajuste crucial: posicionar com base no tamanho do tile
  // Multiplicamos a posição da grade pelo tamanho do tile
  const adjustedPosition: [number, number, number] = [
    position[0] + gridX * size, // A multiplicação por size é essencial
    position[1] + gridY * size, // A multiplicação por size é essencial
    position[2],
  ];

  // change debug ui to true when key is pressed
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "l") {
        setShowDebugUi((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  // Load texture
  useEffect(() => {
    const textureLoader = new THREE.TextureLoader();
    const spritesheet = forestSpritesheet;
    textureLoader.load(
      spritesheet,
      (loadedTexture) => {
        loadedTexture.magFilter = THREE.NearestFilter;
        loadedTexture.minFilter = THREE.NearestFilter;
        loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;

        // Set repeat to slice the spritesheet into tiles
        loadedTexture.repeat.set(1 / cols, 1 / rows);

        // Set the offset to display the specific tile
        // The Y offset is inverted (1 - y) because texture coordinates start from bottom
        loadedTexture.offset.set(tileX / cols, 1 - (tileY + 1) / rows);

        setTexture(loadedTexture);
      },
      undefined,
      (error) => {
        console.error("Error loading forest spritesheet:", error);
      }
    );
  }, [tileX, tileY, rows, cols]);

  // Update texture offset when tileX or tileY changes
  useEffect(() => {
    if (texture) {
      texture.offset.set(tileX / cols, 1 - (tileY + 1) / rows);
    }
  }, [tileX, tileY, texture, rows, cols]);

  if (!texture) {
    // Return a placeholder while the texture is loading
    return (
      <mesh
        position={new THREE.Vector3(...adjustedPosition)}
        scale={new THREE.Vector3(...finalScale)}
      >
        <boxGeometry args={[1, 1, 0.1]} />
        <meshStandardMaterial color="green" />
      </mesh>
    );
  }

  return (
    <mesh ref={meshRef} position={adjustedPosition} scale={finalScale}>
      <planeGeometry args={[1, 1]} />
      <meshStandardMaterial
        map={texture}
        transparent={true}
        side={THREE.DoubleSide}
        receiveShadow={true}
        roughness={0.8}
        metalness={0.2}
      />{" "}
      {showDebugUi && (
        <Text position={[0, 0, 0.3]} fontSize={0.2} color="white">
          {gridX}, {gridY}
        </Text>
      )}
    </mesh>
  );
};

export default ForestTile;
