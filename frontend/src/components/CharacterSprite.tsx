import { Text } from "@react-three/drei";
import { useFrame } from "@react-three/fiber";
import React, {
  forwardRef,
  useEffect,
  useImperativeHandle,
  useRef,
  useState,
} from "react";
import * as THREE from "three";
import { ANIMATIONS, AnimationType } from "../types/animations";
import {
  CharacterSpriteProps,
  MovementState,
  Point,
} from "../types/character-sprite";
import {
  CHARACTERS,
  CharacterType,
  getRandomCharacter,
} from "../types/characters";

const CharacterSprite = forwardRef<
  { moveAlongPath: (path: Point[]) => void },
  CharacterSpriteProps
>(
  (
    {
      position = [0, 0, 0],
      scale = [1, 1, 1],
      rows = 8,
      cols = 8,
      animation = AnimationType.IDLE_DOWN,
      frame = undefined, // If specified, will override the animation
      characterType = undefined, // If not specified, will pick randomly
      onAnimationComplete,
      speed = 2, // Units per second
      onMoveComplete,
      setPosition,
      setAnimation,
      zOffset = 0.1,
    },
    ref
  ) => {
    const currentFrameRef = useRef(0);
    const frameTimeAccumulatorRef = useRef(0);
    const meshRef = useRef<THREE.Mesh>(null);
    const [texture, setTexture] = useState<THREE.Texture | null>(null);
    const [currentFrame, setCurrentFrame] = useState(0);
    const [frameTimeAccumulator, setFrameTimeAccumulator] = useState(0);
    const animationRef = useRef(animation);
    const [selectedCharacter, setSelectedCharacter] = useState<{
      type: CharacterType;
      sprite: string;
    } | null>(null);
    const [movementState, setMovementState] = useState<MovementState>({
      path: [],
      currentPathIndex: 0,
      isMoving: false,
    });

    // Set random character on first render
    useEffect(() => {
      if (!characterType) {
        setSelectedCharacter(getRandomCharacter());
      } else {
        // Use the specified type with a random variant
        const typeVariants = CHARACTERS[characterType];
        const randomVariant =
          typeVariants[Math.floor(Math.random() * typeVariants.length)];
        setSelectedCharacter({
          type: characterType,
          sprite: randomVariant,
        });
      }
    }, [characterType]);

    // Load texture
    useEffect(() => {
      if (!selectedCharacter) return;

      const textureLoader = new THREE.TextureLoader();
      textureLoader.load(
        selectedCharacter.sprite,
        (loadedTexture) => {
          loadedTexture.magFilter = THREE.NearestFilter;
          loadedTexture.minFilter = THREE.NearestFilter;
          loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;
          loadedTexture.repeat.set(1 / cols, 1 / rows);
          setTexture(loadedTexture);
        },
        undefined,
        (error) => {
          // Silently handle error
        }
      );
    }, [selectedCharacter, rows, cols]);

    // Update animation ref when animation prop changes
    useEffect(() => {
      animationRef.current = animation;
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

    // Expor moveAlongPath através da ref
    useImperativeHandle(ref, () => ({
      moveAlongPath: (path: Point[]) => {
        setMovementState({
          path,
          currentPathIndex: 0,
          isMoving: true,
        });
      },
    }));

    // Update movement in the animation frame
    useFrame((_, delta) => {
      if (!meshRef.current || !movementState.isMoving) return;

      const currentPos = meshRef.current.position;
      const currentPathIndex = movementState.currentPathIndex;

      if (currentPathIndex >= movementState.path.length) {
        setMovementState((prev) => ({ ...prev, isMoving: false }));
        setAnimation?.(AnimationType.IDLE_DOWN);
        setCurrentFrame(0);
        setFrameTimeAccumulator(0);
        console.log("currentPos", currentPos);
        if (setPosition) {
          setPosition([currentPos.x, currentPos.y, currentPos.z]);
        }
        if (onMoveComplete) onMoveComplete();
        return;
      }

      const target = movementState.path[currentPathIndex];
      const targetPos = new THREE.Vector3(target.x, target.y, currentPos.z);
      const distance = currentPos.distanceTo(targetPos);

      // Determinar a direção do movimento e atualizar a animação
      const dx = targetPos.x - currentPos.x;
      const dy = targetPos.y - currentPos.y;

      // Determinar a direção predominante e atualizar a animação global
      let newAnimation: AnimationType;
      if (Math.abs(dx) > Math.abs(dy)) {
        // Movimento horizontal
        if (dx > 0) {
          newAnimation = AnimationType.WALK_RIGHT;
        } else {
          newAnimation = AnimationType.WALK_LEFT;
        }
      } else {
        // Movimento vertical
        if (dy > 0) {
          newAnimation = AnimationType.WALK_UP;
        } else {
          newAnimation = AnimationType.WALK_DOWN;
        }
      }

      // Atualizar a animação apenas se mudou
      if (newAnimation !== animationRef.current) {
        animationRef.current = newAnimation;
        if (setAnimation) {
          setAnimation(newAnimation);
        }
        // Reset frame time accumulator to start the animation from the beginning
        setFrameTimeAccumulator(0);
        setCurrentFrame(0);
      }

      if (distance < 0.1) {
        if (setPosition) {
          setPosition([target.x, target.y, currentPos.z]);
        }
        setMovementState((prev) => ({
          ...prev,
          currentPathIndex: prev.currentPathIndex + 1,
        }));
        return;
      }

      // Calculate movement direction
      const direction = new THREE.Vector3()
        .subVectors(targetPos, currentPos)
        .normalize();

      // Move towards target
      const movement = direction.multiplyScalar(speed * delta);
      currentPos.add(movement);

      if (setPosition) {
        setPosition([currentPos.x, currentPos.y, currentPos.z]);
      }
    });

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
      frameTimeAccumulatorRef.current += delta * 1000;

      // Check if we need to advance to the next frame
      if (
        frameTimeAccumulatorRef.current >= frameTiming[currentFrameRef.current]
      ) {
        // Advance to next frame
        let newFrame = currentFrameRef.current + 1;
        currentFrameRef.current = newFrame;

        // Check if animation is complete
        if (newFrame >= animationFrames.length) {
          if (shouldLoop) {
            // Loop back to the beginning
            console.log("looping");
            newFrame = 0;
            currentFrameRef.current = 0;
          } else {
            // Animation is complete, stay at the last frame
            newFrame = animationFrames.length - 1;

            // Notify that animation is complete
            if (onAnimationComplete) {
              currentFrameRef.current = 0;
              onAnimationComplete(animationRef.current);
            }
          }
        }

        setCurrentFrame(newFrame);
        setTextureOffsetFromFrame(animationFrames[currentFrameRef.current]);

        // Reset accumulator
        frameTimeAccumulatorRef.current -= frameTiming[currentFrameRef.current];
      }

      setFrameTimeAccumulator(frameTimeAccumulatorRef.current);
    });

    const adjustedPosition: [number, number, number] = [
      position[0],
      position[1],
      zOffset,
    ];

    return (
      <mesh
        ref={meshRef}
        position={new THREE.Vector3(...adjustedPosition)}
        scale={scale}
      >
        <planeGeometry args={[1, 1]} />
        <meshStandardMaterial
          map={texture}
          transparent={true}
          roughness={0.5}
          metalness={0.0}
          side={THREE.DoubleSide}
        />
        <Text
          position={[0, -0.25, 0]}
          fontSize={0.08}
          color="white"
          anchorX="center"
          anchorY="middle"
        >
          {animationRef.current}
        </Text>
      </mesh>
    );
  }
);

// Exportar tudo em uma única linha
export type { MovementState, Point };
export default CharacterSprite;
