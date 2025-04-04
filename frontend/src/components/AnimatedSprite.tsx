import {Text} from "@react-three/drei";
import {ThreeEvent} from "@react-three/fiber";
import React, {useEffect, useRef, useState} from "react";
import * as THREE from "three";
import {Position} from "../types/game";

interface AnimatedSpriteProps {
  id: string;
  type: string;
  name: string;
  position: Position;
  imageUrl: string;
  zOffset?: number;
  spritesheetSize?: {
    columns: number;
    rows: number;
  };
  tileSize?: {
    width: number;
    height: number;
  };
  animationConfig?: Record<string, any>;
  isActive?: boolean;
  size?: number;
  emissive?: boolean;
  emissiveIntensity?: number;
  state?: string;
  onClick?: (event: ThreeEvent<MouseEvent>) => void;
  onAnimationComplete?: (currentState: string) => void;
  showText?: boolean;
  heightProportion?: number;
}

export const AnimatedSprite = (props: AnimatedSpriteProps) => {
  const [texture, setTexture] = useState<THREE.Texture | null>(null);
  const [currentFrame, setCurrentFrame] = useState(0);
  const animationRef = useRef<number>();
  const lastFrameTimeRef = useRef<number>(0);
  const { columns, rows } = props.spritesheetSize || { columns: 1, rows: 1 };

  useEffect(() => {
    const loader = new THREE.TextureLoader();
    loader.load(
      props.imageUrl,
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
  }, [props.imageUrl]);

  useEffect(() => {
    if (!texture) return;

    const currentState =
      props.animationConfig?.[
        props.state as keyof typeof props.animationConfig
      ];

    if (!currentState) {
      console.warn(`Animation config for state "${props.state}" is missing`);
      return;
    }

    // Handle unlit state (static frame)
    if (
      (props.state === "unlit" || props.state === "idle") &&
      "frame" in currentState
    ) {
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
            props.onAnimationComplete?.(props.state || "idle");
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
    props.state,
    columns,
    rows,
    props.animationConfig,
    texture,
    currentFrame,
    props.onAnimationComplete,
  ]);

  // Reset currentFrame when state changes
  useEffect(() => {
    setCurrentFrame(0);
    lastFrameTimeRef.current = performance.now();
  }, [props.state]);

  if (!texture) {
    return null; // or a loading placeholder
  }

  const heightProportion = props.heightProportion || 1;
  const baseSize = props.size || 1;

  let posY = props.position.y;

  if (heightProportion != 1) {
    posY += baseSize / 2;
  }

  return (
    <group position={[props.position.x, posY, props.zOffset || 0.01]}>
      <mesh name={props.name} onClick={props.onClick}>
        <planeGeometry args={[baseSize, baseSize * heightProportion]} />
        <meshStandardMaterial
          map={texture}
          transparent={true}
          side={THREE.DoubleSide}
        />
      </mesh>
      {props.showText && (
        <>
          <Text
            position={[0, -0.55, 0]}
            fontSize={0.16}
            color="white"
            anchorX="center"
            anchorY="middle"
          >
            {props.id}
          </Text>
          <Text
            position={[0, -0.8, 0]}
            fontSize={0.12}
            color="white"
            anchorX="center"
            anchorY="middle"
          >
            {props.state}
          </Text>
        </>
      )}
    </group>
  );
};

export default AnimatedSprite;
