import {useFrame} from "@react-three/fiber";
import React, {useEffect, useRef, useState, forwardRef, useImperativeHandle} from "react";
import * as THREE from "three";
import {ANIMATIONS, CharacterAnimationType} from "../../types/animations";
import {CharacterOutfitProps, getRandomOutfit, OUTFITS, OutfitStyle,} from "../../types/character-outfit";
import {CharacterPartRef} from "./CharacterCloak"; // Reuse ref type

const CharacterOutfit = forwardRef<CharacterPartRef, CharacterOutfitProps>(
  (
    {
      position = [0, 0, 0],
      scale = [1, 1, 1],
      rows = 8,
      cols = 8,
      animation = CharacterAnimationType.IDLE_DOWN,
      outfitStyle = undefined, // If not specified, will pick randomly
      zOffset = 0.07, // Default small offset to place outfit in front of character but behind hair
      onAnimationComplete,
    },
    ref // Accept the ref
  ) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const [texture, setTexture] = useState<THREE.Texture | null>(null);
    const [selectedOutfit, setSelectedOutfit] = useState<{
      style: OutfitStyle;
      sprite: string;
    } | null>(null);

    // Set random outfit on first render
    useEffect(() => {
      if (!outfitStyle) {
        setSelectedOutfit(getRandomOutfit());
      } else {
        // Use the specified style with a random variant
        const styleVariants = OUTFITS[outfitStyle];
        const randomVariant =
          styleVariants[Math.floor(Math.random() * styleVariants.length)];
        setSelectedOutfit({
          style: outfitStyle,
          sprite: randomVariant,
        });
      }
    }, [outfitStyle]);

    // Load texture when selectedOutfit changes
    useEffect(() => {
      if (!selectedOutfit) return;

      const textureLoader = new THREE.TextureLoader();
      textureLoader.load(
        selectedOutfit.sprite,
        (loadedTexture) => {
          loadedTexture.magFilter = THREE.NearestFilter;
          loadedTexture.minFilter = THREE.NearestFilter;
          loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;
          loadedTexture.repeat.set(1 / cols, 1 / rows);
          setTexture(loadedTexture);
        },
        undefined,
        (error) => {
          console.error("Error loading outfit texture:", error);
          setTexture(null);
        }
      );
    }, [selectedOutfit, rows, cols]);

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
        // console.log(`Outfit setFrame: ${frameNumber}`);
        setTextureOffsetFromFrame(frameNumber);
      },
    }));

    if (!texture || !selectedOutfit) {
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

export default CharacterOutfit;
