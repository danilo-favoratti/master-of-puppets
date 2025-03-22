import { useFrame } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

// Import all hair sprites
// Main hairstyle variants
import bob2 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v00.png";
import flat from "../assets/spritesheets/4har/char_a_p1_4har_flat_v00.png";
import fro1 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v00.png";
import pon1 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v00.png";
import spk2 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v00.png";

// Color variants for each style (we'll pick one randomly)
// Flat style color variants
import flatV01 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v01.png";
import flatV02 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v02.png";
import flatV03 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v03.png";
import flatV04 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v04.png";
import flatV05 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v05.png";
import flatV06 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v06.png";
import flatV07 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v07.png";
import flatV08 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v08.png";
import flatV09 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v09.png";
import flatV10 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v10.png";
import flatV11 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v11.png";
import flatV12 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v12.png";
import flatV13 from "../assets/spritesheets/4har/char_a_p1_4har_flat_v13.png";

// Bob style color variants
import bobV01 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v01.png";
import bobV02 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v02.png";
import bobV03 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v03.png";
import bobV04 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v04.png";
import bobV05 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v05.png";
import bobV06 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v06.png";
import bobV07 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v07.png";
import bobV08 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v08.png";
import bobV09 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v09.png";
import bobV10 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v10.png";
import bobV11 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v11.png";
import bobV12 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v12.png";
import bobV13 from "../assets/spritesheets/4har/char_a_p1_4har_bob2_v13.png";

// Fro style color variants
import froV01 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v01.png";
import froV02 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v02.png";
import froV03 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v03.png";
import froV04 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v04.png";
import froV05 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v05.png";
import froV06 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v06.png";
import froV07 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v07.png";
import froV08 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v08.png";
import froV09 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v09.png";
import froV10 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v10.png";
import froV11 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v11.png";
import froV12 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v12.png";
import froV13 from "../assets/spritesheets/4har/char_a_p1_4har_fro1_v13.png";

// Ponytail style color variants
import ponV01 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v01.png";
import ponV02 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v02.png";
import ponV03 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v03.png";
import ponV04 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v04.png";
import ponV05 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v05.png";
import ponV06 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v06.png";
import ponV07 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v07.png";
import ponV08 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v08.png";
import ponV09 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v09.png";
import ponV10 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v10.png";
import ponV11a from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v11a.png";
import ponV11b from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v11b.png";
import ponV12 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v12.png";
import ponV13 from "../assets/spritesheets/4har/char_a_p1_4har_pon1_v13.png";

// Spiky style color variants
import spkV01 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v01.png";
import spkV02 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v02.png";
import spkV03 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v03.png";
import spkV04 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v04.png";
import spkV05 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v05.png";
import spkV06 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v06.png";
import spkV07 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v07.png";
import spkV08 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v08.png";
import spkV09 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v09.png";
import spkV10 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v10.png";
import spkV11 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v11.png";
import spkV12 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v12.png";
import spkV13 from "../assets/spritesheets/4har/char_a_p1_4har_spk2_v13.png";

// Define hairstyle types
export enum HairStyle {
  FLAT = "flat",
  BOB = "bob",
  FRO = "fro",
  PONYTAIL = "ponytail",
  SPIKY = "spiky",
}

// Import animation types from CharacterSprite
import { AnimationType } from "./CharacterSprite.tsx";

// Group hair sprites by style
const HAIRSTYLES = {
  [HairStyle.FLAT]: [
    flat,
    flatV01,
    flatV02,
    flatV03,
    flatV04,
    flatV05,
    flatV06,
    flatV07,
    flatV08,
    flatV09,
    flatV10,
    flatV11,
    flatV12,
    flatV13,
  ],
  [HairStyle.BOB]: [
    bob2,
    bobV01,
    bobV02,
    bobV03,
    bobV04,
    bobV05,
    bobV06,
    bobV07,
    bobV08,
    bobV09,
    bobV10,
    bobV11,
    bobV12,
    bobV13,
  ],
  [HairStyle.FRO]: [
    fro1,
    froV01,
    froV02,
    froV03,
    froV04,
    froV05,
    froV06,
    froV07,
    froV08,
    froV09,
    froV10,
    froV11,
    froV12,
    froV13,
  ],
  [HairStyle.PONYTAIL]: [
    pon1,
    ponV01,
    ponV02,
    ponV03,
    ponV04,
    ponV05,
    ponV06,
    ponV07,
    ponV08,
    ponV09,
    ponV10,
    ponV11a,
    ponV11b,
    ponV12,
    ponV13,
  ],
  [HairStyle.SPIKY]: [
    spk2,
    spkV01,
    spkV02,
    spkV03,
    spkV04,
    spkV05,
    spkV06,
    spkV07,
    spkV08,
    spkV09,
    spkV10,
    spkV11,
    spkV12,
    spkV13,
  ],
};

// Function to get a random hairstyle
const getRandomHairstyle = () => {
  // Get random style type
  const styles = Object.values(HairStyle);
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants = HAIRSTYLES[randomStyleType];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    style: randomStyleType,
    sprite: randomVariant,
  };
};

interface CharacterHairProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: AnimationType;
  frame?: number;
  hairStyle?: HairStyle; // Optional specific hairstyle
  zOffset?: number; // Optional Z offset to position the hair slightly in front of the character
  onAnimationComplete?: (animation: AnimationType) => void;
}

const CharacterHair = ({
  position = [0, 0, 0],
  scale = [1, 1, 1],
  rows = 8,
  cols = 8,
  animation = AnimationType.IDLE_DOWN,
  frame = undefined,
  hairStyle = undefined, // If not specified, will pick randomly
  zOffset = 0.01, // Default small offset to place hair in front of character
  onAnimationComplete,
}: CharacterHairProps) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [frameTimeAccumulator, setFrameTimeAccumulator] = useState(0);
  const animationRef = useRef(animation);
  const [selectedHair, setSelectedHair] = useState<{
    style: HairStyle;
    sprite: string;
  } | null>(null);

  // Set random hairstyle on first render
  useEffect(() => {
    if (!hairStyle) {
      setSelectedHair(getRandomHairstyle());
    } else {
      // Use the specified style with a random variant
      const styleVariants = HAIRSTYLES[hairStyle];
      const randomVariant =
        styleVariants[Math.floor(Math.random() * styleVariants.length)];
      setSelectedHair({
        style: hairStyle,
        sprite: randomVariant,
      });
    }
  }, [hairStyle]);

  // Load texture when selectedHair changes
  useEffect(() => {
    if (!selectedHair) return;

    console.log("Loading hair texture...");
    const textureLoader = new THREE.TextureLoader();
    textureLoader.load(
      selectedHair.sprite,
      (loadedTexture) => {
        console.log("Hair texture loaded successfully!", loadedTexture);
        loadedTexture.magFilter = THREE.NearestFilter;
        loadedTexture.minFilter = THREE.NearestFilter;
        loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;
        loadedTexture.repeat.set(1 / cols, 1 / rows);
        setTexture(loadedTexture);
      },
      (progress) => {
        console.log(
          `Loading hair progress: ${Math.round(
            (progress.loaded / progress.total) * 100
          )}%`
        );
      },
      (error) => {
        console.error("Error loading hair texture:", error);
      }
    );
  }, [selectedHair, rows, cols]);

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

  if (!texture || !selectedHair) {
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

export default CharacterHair;
