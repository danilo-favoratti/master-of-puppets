import { useFrame } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

// Import all outfit sprites
// Different outfit types
// Alchemist outfit variants
import alchV01 from "/src/assets/spritesheets/1out/char_a_p1_1out_alch_v01.png";
import alchV02 from "/src/assets/spritesheets/1out/char_a_p1_1out_alch_v02.png";
import alchV03 from "/src/assets/spritesheets/1out/char_a_p1_1out_alch_v03.png";
import alchV04 from "/src/assets/spritesheets/1out/char_a_p1_1out_alch_v04.png";
import alchV05 from "/src/assets/spritesheets/1out/char_a_p1_1out_alch_v05.png";

// Angler outfit variants
import anglV01 from "/src/assets/spritesheets/1out/char_a_p1_1out_angl_v01.png";
import anglV02 from "/src/assets/spritesheets/1out/char_a_p1_1out_angl_v02.png";
import anglV03 from "/src/assets/spritesheets/1out/char_a_p1_1out_angl_v03.png";
import anglV04 from "/src/assets/spritesheets/1out/char_a_p1_1out_angl_v04.png";
import anglV05 from "/src/assets/spritesheets/1out/char_a_p1_1out_angl_v05.png";

// Blacksmith outfit variants
import bksmV01 from "/src/assets/spritesheets/1out/char_a_p1_1out_bksm_v01.png";
import bksmV02 from "/src/assets/spritesheets/1out/char_a_p1_1out_bksm_v02.png";
import bksmV03 from "/src/assets/spritesheets/1out/char_a_p1_1out_bksm_v03.png";
import bksmV04 from "/src/assets/spritesheets/1out/char_a_p1_1out_bksm_v04.png";
import bksmV05 from "/src/assets/spritesheets/1out/char_a_p1_1out_bksm_v05.png";

// Forester outfit variants
import fstrV01 from "/src/assets/spritesheets/1out/char_a_p1_1out_fstr_v01.png";
import fstrV02 from "/src/assets/spritesheets/1out/char_a_p1_1out_fstr_v02.png";
import fstrV03 from "/src/assets/spritesheets/1out/char_a_p1_1out_fstr_v03.png";
import fstrV04 from "/src/assets/spritesheets/1out/char_a_p1_1out_fstr_v04.png";
import fstrV05 from "/src/assets/spritesheets/1out/char_a_p1_1out_fstr_v05.png";

// Pathfinder outfit variants
import pfdrV01 from "/src/assets/spritesheets/1out/char_a_p1_1out_pfdr_v01.png";
import pfdrV02 from "/src/assets/spritesheets/1out/char_a_p1_1out_pfdr_v02.png";
import pfdrV03 from "/src/assets/spritesheets/1out/char_a_p1_1out_pfdr_v03.png";
import pfdrV04 from "/src/assets/spritesheets/1out/char_a_p1_1out_pfdr_v04.png";
import pfdrV05 from "/src/assets/spritesheets/1out/char_a_p1_1out_pfdr_v05.png";

// Import animation types from CharacterSprite
import React from "react";
import { ANIMATIONS, AnimationType } from "../../types/animations";

// Define outfit types
export enum OutfitStyle {
  ALCHEMIST = "alchemist",
  ANGLER = "angler",
  BLACKSMITH = "blacksmith",
  FORESTER = "forester",
  PATHFINDER = "pathfinder",
}

// Group outfit sprites by style
const OUTFITS = {
  [OutfitStyle.ALCHEMIST]: [alchV01, alchV02, alchV03, alchV04, alchV05],
  [OutfitStyle.ANGLER]: [anglV01, anglV02, anglV03, anglV04, anglV05],
  [OutfitStyle.BLACKSMITH]: [bksmV01, bksmV02, bksmV03, bksmV04, bksmV05],
  [OutfitStyle.FORESTER]: [fstrV01, fstrV02, fstrV03, fstrV04, fstrV05],
  [OutfitStyle.PATHFINDER]: [pfdrV01, pfdrV02, pfdrV03, pfdrV04, pfdrV05],
};

// Function to get a random outfit
const getRandomOutfit = () => {
  // Get random style type
  const styles = Object.values(OutfitStyle);
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants = OUTFITS[randomStyleType];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    style: randomStyleType,
    sprite: randomVariant,
  };
};

interface CharacterOutfitProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: AnimationType;
  frame?: number;
  outfitStyle?: OutfitStyle; // Optional specific outfit style
  zOffset?: number; // Optional Z offset to position the outfit relative to the character
  onAnimationComplete?: (animation: AnimationType) => void;
}

const CharacterOutfit = ({
  position = [0, 0, 0],
  scale = [1, 1, 1],
  rows = 8,
  cols = 8,
  animation = AnimationType.IDLE_DOWN,
  frame = undefined,
  outfitStyle = undefined, // If not specified, will pick randomly
  zOffset = 0.005, // Default small offset to place outfit in front of character but behind hair
  onAnimationComplete,
}: CharacterOutfitProps) => {
  const currentFrameRef = useRef(0);
  const frameTimeAccumulatorRef = useRef(0);
  const meshRef = useRef<THREE.Mesh>(null);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [frameTimeAccumulator, setFrameTimeAccumulator] = useState(0);
  const animationRef = useRef(animation);
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

    console.log("Loading outfit texture...");
    const textureLoader = new THREE.TextureLoader();
    textureLoader.load(
      selectedOutfit.sprite,
      (loadedTexture) => {
        console.log("Outfit texture loaded successfully!", loadedTexture);
        loadedTexture.magFilter = THREE.NearestFilter;
        loadedTexture.minFilter = THREE.NearestFilter;
        loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;
        loadedTexture.repeat.set(1 / cols, 1 / rows);
        setTexture(loadedTexture);
      },
      (progress) => {
        console.log(
          `Loading outfit progress: ${Math.round(
            (progress.loaded / progress.total) * 100
          )}%`
        );
      },
      (error) => {
        console.error("Error loading outfit texture:", error);
      }
    );
  }, [selectedOutfit, rows, cols]);

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
      <meshBasicMaterial map={texture} transparent={true} />
    </mesh>
  );
};

export default CharacterOutfit;
