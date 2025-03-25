import { Text } from "@react-three/drei";
import { ThreeEvent } from "@react-three/fiber";
import React, { useEffect, useRef, useState } from "react";
import * as THREE from "three";
import { Position } from "../types/game";

interface AnimatedSpriteProps {
  id: string;
  type: string;
  name: string;
  position: Position;
  imageUrl: string;
  spritesheetSize?: {
    columns: number;
    rows: number;
  };
  tileSize?: {
    width: number;
    height: number;
  };
  animationConfig?: {
    unlit?: {
      frame: { x: number; y: number };
      frameDuration: number;
    };
    burning?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    dying?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    extinguished?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    idleUp?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    idleDown?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    idleLeft?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    idleRight?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    walkLeft?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    walkRight?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    walkUp?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    walkDown?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    broken?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    breaking?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    idle?: {
      frame: { x: number; y: number };
      frameDuration: number;
    };
    open?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    closed?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    empty?: {
      frame: { x: number; y: number };
      frameDuration: number;
    };
    cooking?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
    cooked?: {
      frames: Array<{ x: number; y: number }>;
      frameDuration: number;
    };
  };
  isActive?: boolean;
  size?: number;
  emissive?: boolean;
  emissiveIntensity?: number;
  state?:
    | "unlit"
    | "burning"
    | "dying"
    | "extinguished"
    | "idleUp"
    | "idleDown"
    | "idleLeft"
    | "idleRight"
    | "walkLeft"
    | "walkRight"
    | "walkUp"
    | "walkDown"
    | "broken"
    | "breaking"
    | "idle"
    | "open"
    | "closed"
    | "empty"
    | "cooking"
    | "cooked";
  onClick?: (event: ThreeEvent<MouseEvent>) => void;
  onAnimationComplete?: (currentState: string) => void;
  showText?: boolean;
}

export const AnimatedSprite: React.FC<AnimatedSpriteProps> = ({
  id,
  name,
  position,
  imageUrl,
  spritesheetSize = { columns: 1, rows: 1 },
  tileSize = { width: 32, height: 32 },
  animationConfig = {
    unlit: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    burning: {
      frames: [{ x: 0, y: 0 }],
      frameDuration: 200,
    },
    dying: {
      frames: [{ x: 0, y: 0 }],
      frameDuration: 200,
    },
    extinguished: {
      frames: [{ x: 0, y: 0 }],
      frameDuration: 200,
    },
    idleUp: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    idleDown: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    idleLeft: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    idleRight: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    walkLeft: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    walkRight: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    walkUp: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    walkDown: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    broken: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    breaking: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    idle: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    empty: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    cooking: { frame: { x: 0, y: 0 }, frameDuration: 200 },
    cooked: { frame: { x: 0, y: 0 }, frameDuration: 200 },
  },

  isActive = false,
  size = 1,
  state = "idle",
  onClick,
  onAnimationComplete,
  showText = false,
}) => {
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const animationRef = useRef<number>();
  const lastFrameTimeRef = useRef<number>(0);
  const { columns, rows } = spritesheetSize;
  const { width: tileWidth, height: tileHeight } = tileSize;

  useEffect(() => {
    const loader = new THREE.TextureLoader();
    loader.load(
      imageUrl,
      (loadedTexture) => {
        loadedTexture.magFilter = THREE.NearestFilter;
        loadedTexture.minFilter = THREE.NearestFilter;
        setTexture(loadedTexture);
      },
      undefined,
      (error) => {
        console.error("Error loading texture:", error);
      }
    );
  }, [imageUrl]);

  useEffect(() => {
    if (!texture) return;

    const currentState = animationConfig[state];

    if (!currentState) {
      console.warn(`Animation config for state "${state}" is missing`);
      return;
    }

    // Handle unlit state (static frame)
    if ((state === "unlit" || state === "idle") && "frame" in currentState) {
      const frame = currentState.frame;
      if (frame && typeof frame === "object" && "x" in frame && "y" in frame) {
        const { x, y } = frame;
        texture.repeat.set(1 / columns, 1 / rows);
        texture.offset.set(x / columns, 1 - (y + 1) / rows);
        return;
      }
    }

    // Animation logic for states with multiple frames
    const animate = (currentTime: number) => {
      if ("frames" in currentState && currentState.frames) {
        const { frames, frameDuration } = currentState;

        const elapsed = currentTime - lastFrameTimeRef.current;
        if (elapsed >= frameDuration) {
          const nextFrame = (currentFrame + 1) % frames.length;
          const { x, y } = frames[nextFrame];

          texture.repeat.set(1 / columns, 1 / rows);
          texture.offset.set(x / columns, 1 - (y + 1) / rows);
          texture.needsUpdate = true;

          setCurrentFrame(nextFrame);
          lastFrameTimeRef.current = currentTime;

          // Check if animation has completed (reached the last frame)
          if (nextFrame === 0 && currentFrame === frames.length - 1) {
            onAnimationComplete?.(state);
          }
        }

        animationRef.current = requestAnimationFrame(animate);
      }
    };

    // Start animation immediately
    lastFrameTimeRef.current = performance.now();
    animationRef.current = requestAnimationFrame(animate);

    return () => {
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current);
      }
    };
  }, [
    state,
    columns,
    rows,
    animationConfig,
    texture,
    currentFrame,
    onAnimationComplete,
  ]);

  // Reset currentFrame when state changes
  useEffect(() => {
    setCurrentFrame(0);
    lastFrameTimeRef.current = performance.now();
  }, [state]);

  if (!texture) {
    return null; // or a loading placeholder
  }

  return (
    <group position={[position.x, position.y, 0.2]}>
      <mesh name={name} onClick={onClick}>
        <planeGeometry args={[size, size]} />
        <meshStandardMaterial
          map={texture}
          transparent={true}
          side={THREE.DoubleSide}
        />
      </mesh>
      {showText && (
        <>
          <Text
            position={[0, -0.55, 0]}
            fontSize={0.16}
            color="white"
            anchorX="center"
            anchorY="middle"
          >
            {id}
          </Text>
          <Text
            position={[0, -0.8, 0]}
            fontSize={0.12}
            color="white"
            anchorX="center"
            anchorY="middle"
          >
            {state}
          </Text>
        </>
      )}
    </group>
  );
};

export default AnimatedSprite;
