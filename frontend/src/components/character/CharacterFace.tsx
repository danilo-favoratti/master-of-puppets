import {useFrame} from "@react-three/fiber";
import React, {useEffect, useRef, useState, forwardRef, useImperativeHandle} from "react";
import * as THREE from "three";
import {ANIMATIONS, CharacterAnimationType} from "../../types/animations";
import {CharacterFaceProps, FACES, FaceStyle, getRandomFace,} from "../../types/character-face";
import {CharacterPartRef} from "./CharacterCloak"; // Assuming exported from Cloak

const CharacterFace = forwardRef<CharacterPartRef, CharacterFaceProps>(
  (
    {
      position = [0, 0, 0],
      scale = [1, 1, 1],
      rows = 8,
      cols = 8,
      animation = CharacterAnimationType.IDLE_DOWN,
      faceStyle = undefined, // If not specified, will pick randomly
      zOffset = 0.04, // Default offset to place face in front of character and cloak
      chanceOfNoFace = 40, // 40% chance of no face accessory by default
      onAnimationComplete,
    },
    ref // Accept the ref
  ) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const [texture, setTexture] = useState<THREE.Texture | null>(null);
    const [selectedFace, setSelectedFace] = useState<{
      style: FaceStyle;
      sprite: string | null;
    } | null>(null);

    // Set random face on first render
    useEffect(() => {
      if (!faceStyle) {
        setSelectedFace(getRandomFace(chanceOfNoFace));
      } else if (faceStyle === FaceStyle.NONE) {
        setSelectedFace({
          style: FaceStyle.NONE,
          sprite: null,
        });
      } else {
        // Use the specified style with a random variant
        const styleVariants = FACES[faceStyle as keyof typeof FACES];
        const randomVariant =
          styleVariants[Math.floor(Math.random() * styleVariants.length)];
        setSelectedFace({
          style: faceStyle,
          sprite: randomVariant,
        });
      }
    }, [faceStyle, chanceOfNoFace]);

    // Load texture when selectedFace changes
    useEffect(() => {
      if (
        !selectedFace ||
        selectedFace.style === FaceStyle.NONE ||
        !selectedFace.sprite
      ) {
        setTexture(null);
        return;
      }

      const textureLoader = new THREE.TextureLoader();
      textureLoader.load(
        selectedFace.sprite,
        (loadedTexture) => {
          loadedTexture.magFilter = THREE.NearestFilter;
          loadedTexture.minFilter = THREE.NearestFilter;
          loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;
          loadedTexture.repeat.set(1 / cols, 1 / rows);
          setTexture(loadedTexture);
        },
        undefined,
        (error) => {
          console.error("Error loading face texture:", error);
          setTexture(null);
        }
      );
    }, [selectedFace, rows, cols]);

    // Add Mount/Unmount Logging
    useEffect(() => {
      console.log("MOUNT: CharacterFace");
      return () => {
        console.log("UNMOUNT: CharacterFace");
      };
    }, []); // Empty dependency array ensures this runs only on mount and unmount

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
        setTextureOffsetFromFrame(frameNumber);
      },
    }));

    // If no face accessory or texture, don't render anything
    if (!texture || !selectedFace || selectedFace.style === FaceStyle.NONE) {
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

export default CharacterFace;
