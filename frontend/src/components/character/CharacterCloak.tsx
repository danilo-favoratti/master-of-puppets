import {useFrame} from "@react-three/fiber";
import React, {useEffect, useRef, useState, forwardRef, useImperativeHandle} from "react";
import * as THREE from "three";
import {ANIMATIONS, CharacterAnimationType} from "../../types/animations";
import {CharacterCloakProps, CLOAKS, CloakStyle, getRandomCloak,} from "../../types/character-cloak";

// Define handle structure for the ref
export interface CharacterPartRef {
  setFrame: (frameNumber: number) => void;
}

const CharacterCloak = forwardRef<CharacterPartRef, CharacterCloakProps>(
  (
    {
      position = [0, 0, 0],
      scale = [1, 1, 1],
      rows = 8,
      cols = 8,
      animation = CharacterAnimationType.IDLE_DOWN,
      cloakStyle = undefined, // If not specified, will pick randomly
      zOffset = 0.02, // Default offset to place cloak in front of character but behind face/hair
      chanceOfNoCloak = 30, // 30% chance of no cloak by default
      onAnimationComplete,
    },
    ref // Accept the ref
  ) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const [texture, setTexture] = useState<THREE.Texture | null>(null);
    const [selectedCloak, setSelectedCloak] = useState<{
      style: CloakStyle;
      sprite: string | null;
    } | null>(null);

    // Set random cloak on first render
    useEffect(() => {
      if (!cloakStyle) {
        setSelectedCloak(getRandomCloak(chanceOfNoCloak));
      } else if (cloakStyle === CloakStyle.NONE) {
        setSelectedCloak({
          style: CloakStyle.NONE,
          sprite: null,
        });
      } else {
        // Use the specified style with a random variant
        // Type check to ensure we're not using CloakStyle.NONE
        if (cloakStyle === CloakStyle.LONG || cloakStyle === CloakStyle.MEDIUM) {
          const styleVariants = CLOAKS[cloakStyle as keyof typeof CLOAKS];
          const randomVariant =
            styleVariants[Math.floor(Math.random() * styleVariants.length)];
          setSelectedCloak({
            style: cloakStyle,
            sprite: randomVariant,
          });
        } else {
          // Handle cases where cloakStyle might be invalid if needed
          setSelectedCloak({ style: CloakStyle.NONE, sprite: null });
        }
      }
    }, [cloakStyle, chanceOfNoCloak]);

    // Load texture when selectedCloak changes
    useEffect(() => {
      if (
        !selectedCloak ||
        selectedCloak.style === CloakStyle.NONE ||
        !selectedCloak.sprite
      ) {
        setTexture(null); // Explicitly clear texture
        return;
      }

      const textureLoader = new THREE.TextureLoader();
      textureLoader.load(
        selectedCloak.sprite,
        (loadedTexture) => {
          loadedTexture.magFilter = THREE.NearestFilter;
          loadedTexture.minFilter = THREE.NearestFilter;
          loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;
          loadedTexture.repeat.set(1 / cols, 1 / rows);
          setTexture(loadedTexture);
        },
        undefined,
        (error) => {
          console.error("Error loading cloak texture:", error);
          setTexture(null); // Clear texture on error
        }
      );
    }, [selectedCloak, rows, cols]);

    // Helper function to set texture offset based on frame number
    const setTextureOffsetFromFrame = (frameNumber: number) => {
      if (!texture) return;

      // Calculate row and column from frame number
      const row = Math.floor(frameNumber / cols);
      const col = frameNumber % cols;

      // Set texture offset
      texture.offset.set(col / cols, 1 - (row + 1) / rows);
      // Force texture update
      texture.needsUpdate = true;
    };

    // Expose setFrame via useImperativeHandle
    useImperativeHandle(ref, () => ({
      setFrame: (frameNumber: number) => {
        // Optionally add logging here too
        // console.log(`Cloak setFrame: ${frameNumber}`);
        setTextureOffsetFromFrame(frameNumber);
      },
    }));

    // If no cloak or texture, don't render anything
    if (!texture || !selectedCloak || selectedCloak.style === CloakStyle.NONE) {
      return null;
    }

    // Adjust position to include zOffset
    const adjustedPosition: [number, number, number] = [
      position[0],
      position[1],
      zOffset,
    ];

    return (
      <mesh
        ref={meshRef}
        position={new THREE.Vector3(...adjustedPosition)}
        scale={new THREE.Vector3(...scale)}
      >
        <planeGeometry args={[1, 1]} />
        <meshStandardMaterial map={texture} transparent={true} />
      </mesh>
    );
  }
);

export default CharacterCloak;
