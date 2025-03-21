import { useFrame } from "@react-three/fiber";
import { useEffect, useRef, useState } from "react";
import * as THREE from "three";
// Import the sprite sheet 
import characterSpriteImage from "../assets/char_a_p1_0bas_humn_v00.png";

// Define animation types
export enum AnimationType {
  IDLE_DOWN = "idle_down",
  IDLE_UP = "idle_up",
  IDLE_LEFT = "idle_left",
  IDLE_RIGHT = "idle_right",
  WALK_DOWN = "walk_down",
  WALK_UP = "walk_up",
  WALK_LEFT = "walk_left",
  WALK_RIGHT = "walk_right",
  RUN_DOWN = "run_down",
  RUN_UP = "run_up",
  RUN_LEFT = "run_left",
  RUN_RIGHT = "run_right",
  PUSH_DOWN = "push_down",
  PUSH_UP = "push_up",
  PUSH_LEFT = "push_left",
  PUSH_RIGHT = "push_right",
  PULL_DOWN = "pull_down",
  PULL_UP = "pull_up",
  PULL_LEFT = "pull_left",
  PULL_RIGHT = "pull_right",
  JUMP_DOWN = "jump_down",
  JUMP_UP = "jump_up",
  JUMP_LEFT = "jump_left",
  JUMP_RIGHT = "jump_right",
  // Other animations can be added as needed (fishing, farming, etc.)
}

// Animation configuration interface
interface AnimationConfig {
  frames: number[];
  frameTiming: number[];
  loop?: boolean;
}

// Animation frame definitions
// Each row in the sprite sheet has 8 columns (frames)
// Based on the documentation, rows 0-3 are for directional animations (down, up, left, right)
export const ANIMATIONS: Record<AnimationType, AnimationConfig> = {
  // Idle animations (first frame of each row)
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

  // Walk animations (frames 0-5 on rows 0-3)
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

  // Run animations (per docs: frames 1,2,7,4,5,8 in sequence)
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

  // Push animations (2-frame loop - columns 1,2 on rows 0-3)
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

  // Pull animations (2-frame loop - columns 3,4 on rows 0-3)
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

  // Jump animations (4-frame sequence - last 3 columns on rows 0-3, with the first frame repeated at the end)
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

interface CharacterSpriteProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: AnimationType;
  frame?: number; // Optional specific frame to display
  onAnimationComplete?: (animation: AnimationType) => void; // Callback when animation completes
}

const CharacterSprite = ({
  position = [0, 0, 0],
  scale = [1, 1, 1],
  rows = 8,
  cols = 8,
  animation = AnimationType.IDLE_DOWN,
  frame = undefined, // If specified, will override the animation
  onAnimationComplete,
}: CharacterSpriteProps) => {
  const meshRef = useRef<THREE.Mesh>(null);
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const [frameTimeAccumulator, setFrameTimeAccumulator] = useState(0);
  const animationRef = useRef(animation);

  // Load texture
  useEffect(() => {
    console.log("Loading texture...");
    const textureLoader = new THREE.TextureLoader();
    textureLoader.load(
      characterSpriteImage,
      (loadedTexture) => {
        console.log("Texture loaded successfully!", loadedTexture);
        loadedTexture.magFilter = THREE.NearestFilter;
        loadedTexture.minFilter = THREE.NearestFilter;
        loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;
        loadedTexture.repeat.set(1 / cols, 1 / rows);
        setTexture(loadedTexture);
      },
      (progress) => {
        console.log(
          `Loading progress: ${Math.round(
            (progress.loaded / progress.total) * 100
          )}%`
        );
      },
      (error) => {
        console.error("Error loading texture:", error);
      }
    );
  }, [rows, cols]);

  // Update animation ref when animation prop changes
  useEffect(() => {
    animationRef.current = animation;
    console.log("Animation changed to:", animation);
    // Reset frame time accumulator to start the animation from the beginning
    setFrameTimeAccumulator(0);
    setCurrentFrame(0);
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
    if (animationFrames.length === 1) {
      setTextureOffsetFromFrame(animationFrames[0]);
      return;
    }

    // Update frame using delta time
    let newFrameTimeAccumulator = frameTimeAccumulator + delta * 1000;

    // Check if we need to advance to the next frame
    if (newFrameTimeAccumulator >= frameTiming[currentFrame]) {
      // Reset accumulator
      newFrameTimeAccumulator -= frameTiming[currentFrame];

      // Advance to next frame
      let newFrame = currentFrame + 1;

      // Check if animation is complete
      if (newFrame >= animationFrames.length) {
        if (shouldLoop) {
          // Loop back to the beginning
          newFrame = 0;
        } else {
          // Animation is complete, stay at the last frame
          newFrame = animationFrames.length - 1;

          // Notify that animation is complete
          if (onAnimationComplete) {
            onAnimationComplete(animationRef.current);
          }
        }
      }

      setCurrentFrame(newFrame);
      setTextureOffsetFromFrame(animationFrames[newFrame]);
    }

    setFrameTimeAccumulator(newFrameTimeAccumulator);
  });

  if (!texture) {
    // Return a placeholder while the texture is loading
    return (
      <mesh position={position} scale={scale}>
        <boxGeometry args={[1, 1, 0.1]} />
        <meshStandardMaterial color="lightblue" />
      </mesh>
    );
  }

  return (
    <mesh ref={meshRef} position={position} scale={scale}>
      <planeGeometry args={[1, 1]} />
      <meshBasicMaterial map={texture} transparent={true} />
    </mesh>
  );
};

export default CharacterSprite; 