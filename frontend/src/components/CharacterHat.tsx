import { useFrame } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

// Import animation types from CharacterSprite
import { AnimationType } from "./CharacterSprite.tsx";

// Import all hat sprites
// Headband (band)
import bandV01 from "../assets/spritesheets/5hat/char_a_p1_5hat_band_v01.png";
import bandV02 from "../assets/spritesheets/5hat/char_a_p1_5hat_band_v02.png";
import bandV03 from "../assets/spritesheets/5hat/char_a_p1_5hat_band_v03.png";
import bandV04 from "../assets/spritesheets/5hat/char_a_p1_5hat_band_v04.png";
import bandV05 from "../assets/spritesheets/5hat/char_a_p1_5hat_band_v05.png";

// Hood (hddn)
import hddnV01 from "../assets/spritesheets/5hat/char_a_p1_5hat_hddn_v01.png";
import hddnV02 from "../assets/spritesheets/5hat/char_a_p1_5hat_hddn_v02.png";
import hddnV03 from "../assets/spritesheets/5hat/char_a_p1_5hat_hddn_v03.png";
import hddnV04 from "../assets/spritesheets/5hat/char_a_p1_5hat_hddn_v04.png";
import hddnV05 from "../assets/spritesheets/5hat/char_a_p1_5hat_hddn_v05.png";
import hddnV06 from "../assets/spritesheets/5hat/char_a_p1_5hat_hddn_v06.png";
import hddnV07 from "../assets/spritesheets/5hat/char_a_p1_5hat_hddn_v07.png";
import hddnV08 from "../assets/spritesheets/5hat/char_a_p1_5hat_hddn_v08.png";
import hddnV09 from "../assets/spritesheets/5hat/char_a_p1_5hat_hddn_v09.png";
import hddnV10 from "../assets/spritesheets/5hat/char_a_p1_5hat_hddn_v10.png";

// Helmet (hdpl)
import hdplV01 from "../assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v01.png";
import hdplV02 from "../assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v02.png";
import hdplV03 from "../assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v03.png";
import hdplV04 from "../assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v04.png";
import hdplV05 from "../assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v05.png";
import hdplV06 from "../assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v06.png";
import hdplV07 from "../assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v07.png";
import hdplV08 from "../assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v08.png";
import hdplV09 from "../assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v09.png";
import hdplV10 from "../assets/spritesheets/5hat/char_a_p1_5hat_hdpl_v10.png";

// Pointy hat (pnty)
import pntyV01 from "../assets/spritesheets/5hat/char_a_p1_5hat_pnty_v01.png";
import pntyV02 from "../assets/spritesheets/5hat/char_a_p1_5hat_pnty_v02.png";
import pntyV03 from "../assets/spritesheets/5hat/char_a_p1_5hat_pnty_v03.png";
import pntyV04 from "../assets/spritesheets/5hat/char_a_p1_5hat_pnty_v04.png";
import pntyV05 from "../assets/spritesheets/5hat/char_a_p1_5hat_pnty_v05.png";

// Round hat (rnht)
import rnhtV01 from "../assets/spritesheets/5hat/char_a_p1_5hat_rnht_v01.png";
import rnhtV02 from "../assets/spritesheets/5hat/char_a_p1_5hat_rnht_v02.png";
import rnhtV03 from "../assets/spritesheets/5hat/char_a_p1_5hat_rnht_v03.png";
import rnhtV04 from "../assets/spritesheets/5hat/char_a_p1_5hat_rnht_v04.png";
import rnhtV05 from "../assets/spritesheets/5hat/char_a_p1_5hat_rnht_v05.png";

// Puff ball hat (pfbn)
import pfbnV01 from "../assets/spritesheets/5hat/char_a_p1_5hat_pfbn_v01.png";
import pfbnV02 from "../assets/spritesheets/5hat/char_a_p1_5hat_pfbn_v02.png";
import pfbnV03 from "../assets/spritesheets/5hat/char_a_p1_5hat_pfbn_v03.png";
import pfbnV04 from "../assets/spritesheets/5hat/char_a_p1_5hat_pfbn_v04.png";
import pfbnV05 from "../assets/spritesheets/5hat/char_a_p1_5hat_pfbn_v05.png";

// Define hat styles
export enum HatStyle {
  HEADBAND = "headband",
  HOOD = "hood",
  HELMET = "helmet",
  POINTY = "pointy",
  ROUND = "round",
  PUFFBALL = "puffball",
  NONE = "none", // Added for possibility of no hat
}

// Group hat sprites by style
const HATS = {
  [HatStyle.HEADBAND]: [bandV01, bandV02, bandV03, bandV04, bandV05],
  [HatStyle.HOOD]: [
    hddnV01,
    hddnV02,
    hddnV03,
    hddnV04,
    hddnV05,
    hddnV06,
    hddnV07,
    hddnV08,
    hddnV09,
    hddnV10,
  ],
  [HatStyle.HELMET]: [
    hdplV01,
    hdplV02,
    hdplV03,
    hdplV04,
    hdplV05,
    hdplV06,
    hdplV07,
    hdplV08,
    hdplV09,
    hdplV10,
  ],
  [HatStyle.POINTY]: [pntyV01, pntyV02, pntyV03, pntyV04, pntyV05],
  [HatStyle.ROUND]: [rnhtV01, rnhtV02, rnhtV03, rnhtV04, rnhtV05],
  [HatStyle.PUFFBALL]: [pfbnV01, pfbnV02, pfbnV03, pfbnV04, pfbnV05],
};

// Function to get a random hat or none (with a certain probability)
const getRandomHat = (chanceOfNoHat: number = 25) => {
  // First, determine if we should have no hat (default 25% chance)
  if (Math.random() * 100 < chanceOfNoHat) {
    return {
      style: HatStyle.NONE,
      sprite: null,
    };
  }

  // Get random style type (excluding NONE)
  const styles = [
    HatStyle.HEADBAND,
    HatStyle.HOOD,
    HatStyle.HELMET,
    HatStyle.POINTY,
    HatStyle.ROUND,
    HatStyle.PUFFBALL,
  ];
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants = HATS[randomStyleType as keyof typeof HATS];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    style: randomStyleType,
    sprite: randomVariant,
  };
};

interface CharacterHatProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: AnimationType;
  frame?: number;
  hatStyle?: HatStyle; // Optional specific hat style
  zOffset?: number; // Optional Z offset to position the hat relative to the character
  chanceOfNoHat?: number; // Percentage chance (0-100) that no hat will be shown
  onAnimationComplete?: (animation: AnimationType) => void;
}

const CharacterHat = ({
  position = [0, 0, 0],
  scale = [1, 1, 1],
  rows = 8,
  cols = 8,
  animation = AnimationType.IDLE_DOWN,
  frame = undefined,
  hatStyle = undefined, // If not specified, will pick randomly
  zOffset = 0.03, // Default offset to place hat in front of character, cloak, and face
  chanceOfNoHat = 25, // 25% chance of no hat by default
  onAnimationComplete,
}: CharacterHatProps) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [frameTimeAccumulator, setFrameTimeAccumulator] = useState(0);
  const animationRef = useRef(animation);
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
      // No hat to show
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
        // Handle error silently
      }
    );
  }, [selectedHat, rows, cols]);

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

  // Animation definitions
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
      <meshBasicMaterial map={texture} transparent={true} />
    </mesh>
  );
};

export default CharacterHat;
