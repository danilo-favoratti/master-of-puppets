import {useFrame} from "@react-three/fiber";
import React, {useEffect, useRef, useState, forwardRef, useImperativeHandle} from "react";
import * as THREE from "three";
import {ANIMATIONS, CharacterAnimationType} from "../../types/animations";
import {CharacterHairProps, getRandomHairstyle, HairStyle, HAIRSTYLES,} from "../../types/character-hair";
import {CharacterPartRef} from "./CharacterCloak"; // Reuse ref type

const CharacterHair = forwardRef<CharacterPartRef, CharacterHairProps>(
  (
    {
      position = [0, 0, 0],
      scale = [1, 1, 1],
      rows = 8,
      cols = 8,
      animation = CharacterAnimationType.IDLE_DOWN,
      hairStyle = undefined,
      zOffset = 0.05,
      onAnimationComplete,
    },
    ref
  ) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const [texture, setTexture] = useState<THREE.Texture | null>(null);
    const [selectedHair, setSelectedHair] = useState<{
      style: HairStyle;
      sprite: string;
    } | null>(null);

    useEffect(() => {
      if (!hairStyle) {
        setSelectedHair(getRandomHairstyle());
      } else {
        const styleVariants = HAIRSTYLES[hairStyle];
        const randomVariant =
          styleVariants[Math.floor(Math.random() * styleVariants.length)];
        setSelectedHair({
          style: hairStyle,
          sprite: randomVariant,
        });
      }
    }, [hairStyle]);

    useEffect(() => {
      if (!selectedHair) return;
      const textureLoader = new THREE.TextureLoader();
      textureLoader.load(
        selectedHair.sprite,
        (loadedTexture) => {
          loadedTexture.magFilter = THREE.NearestFilter;
          loadedTexture.minFilter = THREE.NearestFilter;
          loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;
          loadedTexture.repeat.set(1 / cols, 1 / rows);
          setTexture(loadedTexture);
        },
        undefined,
        (error) => {
          console.error("Error loading hair texture:", error);
        }
      );
    }, [selectedHair, rows, cols]);

    const setTextureOffsetFromFrame = (frameNumber: number) => {
      if (!texture) return;
      const row = Math.floor(frameNumber / cols);
      const col = frameNumber % cols;
      texture.offset.set(col / cols, 1 - (row + 1) / rows);
      texture.needsUpdate = true;
    };

    useImperativeHandle(ref, () => ({
      setFrame: (frameNumber: number) => {
        setTextureOffsetFromFrame(frameNumber);
      },
    }));

    if (!texture || !selectedHair) {
      return null;
    }

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

export default CharacterHair;
