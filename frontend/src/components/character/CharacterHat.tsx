import {useFrame} from "@react-three/fiber";
import React, {useEffect, useRef, useState, forwardRef, useImperativeHandle} from "react";
import * as THREE from "three";
import {ANIMATIONS, CharacterAnimationType} from "../../types/animations";
import {CharacterHatProps, getRandomHat, HATS, HatStyle,} from "../../types/character-hat";
import {CharacterPartRef} from "./CharacterCloak"; // Reuse ref type

const CharacterHat = forwardRef<CharacterPartRef, CharacterHatProps>(
  (
    {
      position = [0, 0, 0],
      scale = [1, 1, 1],
      rows = 8,
      cols = 8,
      animation = CharacterAnimationType.IDLE_DOWN,
      hatStyle = undefined, // If not specified, will pick randomly
      zOffset = 0.06, // Default offset to place hat in front of character, cloak, and face
      chanceOfNoHat = 25, // 25% chance of no hat by default
      onAnimationComplete,
    },
    ref // Accept the ref
  ) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const [texture, setTexture] = useState<THREE.Texture | null>(null);
    const [selectedHat, setSelectedHat] = useState<{
      style: HatStyle;
      sprite: string | null;
    } | null>(null);

    // Set random hat on first render
    useEffect(() => {
      if (!hatStyle) {
        setSelectedHat(getRandomHat(chanceOfNoHat));
      } else if (hatStyle === HatStyle.NONE) {
        setSelectedHat({
          style: HatStyle.NONE,
          sprite: null,
        });
      } else {
        // Use the specified style with a random variant
        const styleVariants = HATS[hatStyle as keyof typeof HATS];
        const randomVariant =
          styleVariants[Math.floor(Math.random() * styleVariants.length)];
        setSelectedHat({
          style: hatStyle,
          sprite: randomVariant,
        });
      }
    }, [hatStyle, chanceOfNoHat]);

    // Load texture when selectedHat changes
    useEffect(() => {
      if (
        !selectedHat ||
        selectedHat.style === HatStyle.NONE ||
        !selectedHat.sprite
      ) {
        setTexture(null); // Explicitly clear texture if no hat
        return;
      }

      const textureLoader = new THREE.TextureLoader();
      textureLoader.load(
        selectedHat.sprite,
        (loadedTexture) => {
          loadedTexture.magFilter = THREE.NearestFilter;
          loadedTexture.minFilter = THREE.NearestFilter;
          loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;
          loadedTexture.repeat.set(1 / cols, 1 / rows);
          setTexture(loadedTexture);
        },
        undefined,
        (error) => {
          console.error("Error loading hat texture:", error);
          setTexture(null); // Clear texture on error
        }
      );
    }, [selectedHat, rows, cols]);

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
        // console.log(`Hat setFrame: ${frameNumber}`);
        setTextureOffsetFromFrame(frameNumber);
      },
    }));

    // If no hat or texture, don't render anything
    if (!texture || !selectedHat || selectedHat.style === HatStyle.NONE) {
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

export default CharacterHat;
