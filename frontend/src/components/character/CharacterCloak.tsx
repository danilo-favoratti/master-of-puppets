import {useFrame} from "@react-three/fiber";
import React, {useEffect, useRef, useState} from "react";
import * as THREE from "three";
import {ANIMATIONS, CharacterAnimationType} from "../../types/animations";
import {CharacterCloakProps, CLOAKS, CloakStyle, getRandomCloak,} from "../../types/character-cloak";

const CharacterCloak = ({
  position = [0, 0, 0],
  scale = [1, 1, 1],
  rows = 8,
  cols = 8,
  animation = CharacterAnimationType.IDLE_DOWN,
  frame = undefined,
  cloakStyle = undefined, // If not specified, will pick randomly
  zOffset = 0.01, // Default offset to place cloak in front of character but behind face/hair
  chanceOfNoCloak = 30, // 30% chance of no cloak by default
  onAnimationComplete,
}: CharacterCloakProps) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [frameTimeAccumulator, setFrameTimeAccumulator] = useState(0);
  const animationRef = useRef(animation);
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
      // No cloak to show
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
        // Handle error silently
      }
    );
  }, [selectedCloak, rows, cols]);

  // Update animation ref when animation prop changes
  useEffect(() => {
    animationRef.current = animation;
    // Reset frame time accumulator to start the animation from the beginning
    setFrameTimeAccumulator(0);
  }, [animation]);

  // Helper function to set texture offset based on frame number
  const setTextureOffsetFromFrame = (frameNumber: number) => {
    if (!texture) return;

    // Calculate row and column from frame number
    const row = Math.floor(frameNumber / cols);
    const col = frameNumber % cols;

    // Set texture offset
    texture.offset.set(col / cols, 1 - (row + 1) / rows);
  };

  useFrame((_, delta) => {
    if (!texture) return;

    // Handle single frame case (for specific frame or idle animations)
    if (frame !== undefined) {
      setTextureOffsetFromFrame(frame);
      return;
    }

    // Get current animation config
    const animationConfig = ANIMATIONS[animationRef.current];
    if (!animationConfig || !animationConfig.frames.length) return;

    const animationFrames = animationConfig.frames;
    const frameTiming =
      animationConfig.frameTiming || animationFrames.map(() => 150);
    const shouldLoop = animationConfig.loop !== false; // Default to true if not specified

    // For single frame animations, just show the frame
    if (animationFrames.length <= 1) {
      setTextureOffsetFromFrame(animationFrames[0]);
      return;
    }

    // Accumulate time since last frame
    const newAccumulator = frameTimeAccumulator + delta * 1000; // Convert to ms
    setFrameTimeAccumulator(newAccumulator);

    // Determine which frame to show based on accumulated time
    let timeSum = 0;
    let frameIndex = 0;

    const totalDuration = frameTiming.reduce((sum, time) => sum + time, 0);

    // If we shouldn't loop and we've gone past the total duration,
    // show the last frame and don't continue animation
    if (!shouldLoop && newAccumulator > totalDuration) {
      frameIndex = animationFrames.length - 1;
    } else {
      const normalizedTime = shouldLoop
        ? newAccumulator % totalDuration
        : Math.min(newAccumulator, totalDuration);

      for (let i = 0; i < frameTiming.length; i++) {
        timeSum += frameTiming[i];
        if (normalizedTime < timeSum) {
          frameIndex = i;
          break;
        }
      }
    }

    // Update the frame
    const frameToShow = animationFrames[frameIndex];
    if (currentFrame !== frameToShow) {
      setCurrentFrame(frameToShow);
      setTextureOffsetFromFrame(frameToShow);
    }

    // Check if the animation is complete
    if (!shouldLoop && frameIndex === animationFrames.length - 1) {
      onAnimationComplete?.(animationRef.current);
    }
  });

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
};

export default CharacterCloak;
