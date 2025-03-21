import { useFrame } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";

// Import animation types from CharacterSprite
import { AnimationType } from "../../../frontend-char/src/components/CharacterSprite";

// Import all cloak sprites
// Long cloaks (lnpl)
import lnplV01 from "../assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v01.png";
import lnplV02 from "../assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v02.png";
import lnplV03 from "../assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v03.png";
import lnplV04 from "../assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v04.png";
import lnplV05 from "../assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v05.png";
import lnplV06 from "../assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v06.png";
import lnplV07 from "../assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v07.png";
import lnplV08 from "../assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v08.png";
import lnplV09 from "../assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v09.png";
import lnplV10 from "../assets/spritesheets/2clo/char_a_p1_2clo_lnpl_v10.png";

// Medium cloaks (mnpl)
import mnplV01 from "../assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v01.png";
import mnplV02 from "../assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v02.png";
import mnplV03 from "../assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v03.png";
import mnplV04 from "../assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v04.png";
import mnplV05 from "../assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v05.png";
import mnplV06 from "../assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v06.png";
import mnplV07 from "../assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v07.png";
import mnplV08 from "../assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v08.png";
import mnplV09 from "../assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v09.png";
import mnplV10 from "../assets/spritesheets/2clo/char_a_p1_2clo_mnpl_v10.png";

// Define cloak styles
export enum CloakStyle {
  LONG = "long",
  MEDIUM = "medium",
  NONE = "none", // Added for possibility of no cloak
}

// Group cloak sprites by style
const CLOAKS = {
  [CloakStyle.LONG]: [
    lnplV01,
    lnplV02,
    lnplV03,
    lnplV04,
    lnplV05,
    lnplV06,
    lnplV07,
    lnplV08,
    lnplV09,
    lnplV10,
  ],
  [CloakStyle.MEDIUM]: [
    mnplV01,
    mnplV02,
    mnplV03,
    mnplV04,
    mnplV05,
    mnplV06,
    mnplV07,
    mnplV08,
    mnplV09,
    mnplV10,
  ],
};

// Function to get a random cloak or none (with a certain probability)
const getRandomCloak = (chanceOfNoCloak: number = 30) => {
  // First, determine if we should have no cloak (default 30% chance)
  if (Math.random() * 100 < chanceOfNoCloak) {
    return {
      style: CloakStyle.NONE,
      sprite: null,
    };
  }

  // Get random style type (excluding NONE)
  const styles = [CloakStyle.LONG, CloakStyle.MEDIUM];
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants = CLOAKS[randomStyleType as keyof typeof CLOAKS];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    style: randomStyleType,
    sprite: randomVariant,
  };
};

interface CharacterCloakProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: AnimationType;
  frame?: number;
  cloakStyle?: CloakStyle; // Optional specific cloak style
  zOffset?: number; // Optional Z offset to position the cloak relative to the character
  chanceOfNoCloak?: number; // Percentage chance (0-100) that no cloak will be shown
  onAnimationComplete?: (animation: AnimationType) => void;
}

const CharacterCloak = ({
  position = [0, 0, 0],
  scale = [1, 1, 1],
  rows = 8,
  cols = 8,
  animation = AnimationType.IDLE_DOWN,
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

  // If no cloak or texture, don't render anything
  if (!texture || !selectedCloak || selectedCloak.style === CloakStyle.NONE) {
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

export default CharacterCloak;
