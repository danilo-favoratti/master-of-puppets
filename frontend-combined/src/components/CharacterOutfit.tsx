import { useFrame } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

// Import all outfit sprites
// Different outfit types
// Alchemist outfit variants
import alchV01 from "../assets/spritesheets/1out/char_a_p1_1out_alch_v01.png";
import alchV02 from "../assets/spritesheets/1out/char_a_p1_1out_alch_v02.png";
import alchV03 from "../assets/spritesheets/1out/char_a_p1_1out_alch_v03.png";
import alchV04 from "../assets/spritesheets/1out/char_a_p1_1out_alch_v04.png";
import alchV05 from "../assets/spritesheets/1out/char_a_p1_1out_alch_v05.png";

// Angler outfit variants
import anglV01 from "../assets/spritesheets/1out/char_a_p1_1out_angl_v01.png";
import anglV02 from "../assets/spritesheets/1out/char_a_p1_1out_angl_v02.png";
import anglV03 from "../assets/spritesheets/1out/char_a_p1_1out_angl_v03.png";
import anglV04 from "../assets/spritesheets/1out/char_a_p1_1out_angl_v04.png";
import anglV05 from "../assets/spritesheets/1out/char_a_p1_1out_angl_v05.png";

// Blacksmith outfit variants
import bksmV01 from "../assets/spritesheets/1out/char_a_p1_1out_bksm_v01.png";
import bksmV02 from "../assets/spritesheets/1out/char_a_p1_1out_bksm_v02.png";
import bksmV03 from "../assets/spritesheets/1out/char_a_p1_1out_bksm_v03.png";
import bksmV04 from "../assets/spritesheets/1out/char_a_p1_1out_bksm_v04.png";
import bksmV05 from "../assets/spritesheets/1out/char_a_p1_1out_bksm_v05.png";

// Forester outfit variants
import fstrV01 from "../assets/spritesheets/1out/char_a_p1_1out_fstr_v01.png";
import fstrV02 from "../assets/spritesheets/1out/char_a_p1_1out_fstr_v02.png";
import fstrV03 from "../assets/spritesheets/1out/char_a_p1_1out_fstr_v03.png";
import fstrV04 from "../assets/spritesheets/1out/char_a_p1_1out_fstr_v04.png";
import fstrV05 from "../assets/spritesheets/1out/char_a_p1_1out_fstr_v05.png";

// Pathfinder outfit variants
import pfdrV01 from "../assets/spritesheets/1out/char_a_p1_1out_pfdr_v01.png";
import pfdrV02 from "../assets/spritesheets/1out/char_a_p1_1out_pfdr_v02.png";
import pfdrV03 from "../assets/spritesheets/1out/char_a_p1_1out_pfdr_v03.png";
import pfdrV04 from "../assets/spritesheets/1out/char_a_p1_1out_pfdr_v04.png";
import pfdrV05 from "../assets/spritesheets/1out/char_a_p1_1out_pfdr_v05.png";

// Import animation types from CharacterSprite
import { AnimationType } from "../../../frontend-char/src/components/CharacterSprite";

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

  // Animation definitions from CharacterSprite
  const ANIMATIONS: Record<
    AnimationType,
    { frames: number[]; frameTiming: number[]; loop?: boolean }
  > = {
    [AnimationType.IDLE_DOWN]: {
      frames: [0],
      frameTiming: [300],
    },
    [AnimationType.IDLE_UP]: {
      frames: [8],
      frameTiming: [300],
    },
    [AnimationType.IDLE_LEFT]: {
      frames: [24],
      frameTiming: [300],
    },
    [AnimationType.IDLE_RIGHT]: {
      frames: [16],
      frameTiming: [300],
    },
    [AnimationType.WALK_DOWN]: {
      frames: [32, 33, 34, 35, 36, 37],
      frameTiming: [135, 135, 135, 135, 135, 135],
    },
    [AnimationType.WALK_UP]: {
      frames: [40, 41, 42, 43, 44, 45],
      frameTiming: [135, 135, 135, 135, 135, 135],
    },
    [AnimationType.WALK_LEFT]: {
      frames: [56, 57, 58, 59, 60, 61],
      frameTiming: [135, 135, 135, 135, 135, 135],
    },
    [AnimationType.WALK_RIGHT]: {
      frames: [48, 49, 50, 51, 52, 53],
      frameTiming: [135, 135, 135, 135, 135, 135],
    },
    [AnimationType.RUN_DOWN]: {
      frames: [64, 65, 70, 67, 68, 71],
      frameTiming: [80, 55, 125, 80, 55, 125],
    },
    [AnimationType.RUN_UP]: {
      frames: [72, 73, 78, 75, 76, 79],
      frameTiming: [80, 55, 125, 80, 55, 125],
    },
    [AnimationType.RUN_LEFT]: {
      frames: [88, 89, 94, 91, 92, 95],
      frameTiming: [80, 55, 125, 80, 55, 125],
    },
    [AnimationType.RUN_RIGHT]: {
      frames: [80, 81, 86, 83, 84, 87],
      frameTiming: [80, 55, 125, 80, 55, 125],
    },
    [AnimationType.PUSH_DOWN]: {
      frames: [1, 2],
      frameTiming: [300, 300],
    },
    [AnimationType.PUSH_UP]: {
      frames: [9, 10],
      frameTiming: [300, 300],
    },
    [AnimationType.PUSH_LEFT]: {
      frames: [25, 26],
      frameTiming: [300, 300],
    },
    [AnimationType.PUSH_RIGHT]: {
      frames: [17, 18],
      frameTiming: [300, 300],
    },
    [AnimationType.PULL_DOWN]: {
      frames: [3, 4],
      frameTiming: [400, 400],
    },
    [AnimationType.PULL_UP]: {
      frames: [11, 12],
      frameTiming: [400, 400],
    },
    [AnimationType.PULL_LEFT]: {
      frames: [27, 28],
      frameTiming: [400, 400],
    },
    [AnimationType.PULL_RIGHT]: {
      frames: [19, 20],
      frameTiming: [400, 400],
    },
    [AnimationType.JUMP_DOWN]: {
      frames: [5, 6, 7, 5],
      frameTiming: [300, 150, 100, 300],
      loop: false,
    },
    [AnimationType.JUMP_UP]: {
      frames: [13, 14, 15, 13],
      frameTiming: [300, 150, 100, 300],
      loop: false,
    },
    [AnimationType.JUMP_LEFT]: {
      frames: [29, 30, 31, 29],
      frameTiming: [300, 150, 100, 300],
      loop: false,
    },
    [AnimationType.JUMP_RIGHT]: {
      frames: [21, 22, 23, 21],
      frameTiming: [300, 150, 100, 300],
      loop: false,
    },
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
    position[2] + zOffset,
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
