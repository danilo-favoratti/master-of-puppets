import {useFrame} from "@react-three/fiber";
import React, {forwardRef, useEffect, useImperativeHandle, useRef, useState,} from "react";
import * as THREE from "three";
import {ANIMATIONS, CharacterAnimationType} from "../../types/animations";
import {
    CharacterBodyProps,
    CharacterBodyType,
    CHARACTERS_BODY,
    getRandomCharacterBody,
    MovementState,
} from "../../types/characters-body";
import {Position} from "../../types/game";
import CharacterCloak from "./CharacterCloak";
import CharacterHair from "./CharacterHair";
import CharacterHat from "./CharacterHat";
import CharacterOutfit from "./CharacterOutfit";

// Define the type for the ref methods including steps
export interface CharacterRefMethods {
  moveAlongPath: (path: Position[]) => void;
  move: (direction: string, steps?: number, onComplete?: () => void) => void;
}

const CharacterBody = forwardRef<
  // Use the defined type here
  CharacterRefMethods,
  CharacterBodyProps
>(
  (
    {
      position = [0, 0, 0],
      scale = [1, 1, 1],
      rows = 8,
      cols = 8,
      animation = CharacterAnimationType.IDLE_DOWN,
      frame = undefined, // If specified, will override the animation
      characterType = undefined, // If not specified, will pick randomly
      onAnimationComplete,
      speed = 1, // Units per second
      onMoveComplete,
      setPosition,
      setAnimation,
      zOffset = 0.1,
    },
    ref
  ) => {
    const meshRef = useRef<THREE.Mesh>(null);
    const [currentOnComplete, setCurrentOnComplete] = useState<(() => void) | null>(null);
    const [texture, setTexture] = useState<THREE.Texture | null>(null);
    const [currentFrame, setCurrentFrame] = useState(0);
    const [frameTimeAccumulator, setFrameTimeAccumulator] = useState(0);
    const animationRef = useRef(animation);
    const [selectedCharacter, setSelectedCharacter] = useState<{
      type: CharacterBodyType;
      sprite: string;
    } | null>(null);
    const [movementState, setMovementState] = useState<MovementState>({
      path: [],
      currentPathIndex: 0,
      isMoving: false,
    });
    const [random, setRandom] = useState(Math.random());

    // Set random character on first render
    useEffect(() => {
      if (!characterType) {
        setSelectedCharacter(getRandomCharacterBody());
      } else {
        // Use the specified type with a random variant
        const typeVariants = CHARACTERS_BODY[characterType];
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

    // Update useImperativeHandle to match the new move signature
    useImperativeHandle(ref, (): CharacterRefMethods => ({
      moveAlongPath: (path: Position[]) => {
        setCurrentOnComplete(null); // Clear any pending move callbacks
        setMovementState({
          path,
          currentPathIndex: 0,
          isMoving: true,
        });
      },
      // Update move method signature here
      move: (direction: string, steps: number = 1, onComplete?: () => void) => {
        console.log(`📍 CharacterBody.move called with direction: ${direction}, steps: ${steps}`);
        setCurrentOnComplete(() => onComplete || null);

        // --- Use logical position prop for calculation --- 
        // Instead of: const currentPos = meshRef.current.position;
        const currentLogicalX = position[0];
        const currentLogicalY = position[1];
        const currentZ = position[2] || 0.03; // Use prop Z or default
        
        console.log("📍 Current logical position:", [currentLogicalX, currentLogicalY, currentZ]);

        let targetX = currentLogicalX;
        let targetY = currentLogicalY;
        // --- End position change ---

        // Calculate target offset based on direction and steps
        switch (direction.toLowerCase()) {
          case 'up':
            console.log("📍 MOVE HITTING 'UP'");
            targetY += steps;
            break;
          case 'down':
            console.log("📍 MOVE HITTING 'DOWN'");
            targetY -= steps;
            break;
          case 'left':
            console.log("📍 MOVE HITTING 'LEFT'");
            targetX -= steps;
            break;
          case 'right':
            console.log("📍 MOVE HITTING 'RIGHT'");
            targetX += steps;
            break;
          default:
            console.warn(`Unknown direction: ${direction}`);
            setCurrentOnComplete(null);
            onComplete?.();
            return;
        }
        
        const targetPosition = { x: targetX, y: targetY };
        // Use currentZ for the target log
        console.log("📍 Final target position calculated:", [targetPosition.x, targetPosition.y, currentZ]);

        const path: Position[] = [targetPosition];

        // Set animation based on direction
        let newAnimation: CharacterAnimationType;
        switch(direction.toLowerCase()) {
          case 'up': newAnimation = CharacterAnimationType.WALK_UP; break;
          case 'down': newAnimation = CharacterAnimationType.WALK_DOWN; break;
          case 'left': newAnimation = CharacterAnimationType.WALK_LEFT; break;
          case 'right': newAnimation = CharacterAnimationType.WALK_RIGHT; break;
          default: newAnimation = CharacterAnimationType.WALK_DOWN;
        }
        
        // --- Store the intended animation for the whole move --- 
        animationRef.current = newAnimation; // Update the ref directly
        console.log("📍 Setting animation ref to:", newAnimation);
        if (setAnimation) {
          // Also update the state to trigger immediate visual change if needed
          setAnimation(newAnimation);
        }
        // --- End animation change ---

        console.log("📍 Setting movement state with final path:", path);
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

      const currentPos = meshRef.current.position; // Still use live position for animation
      const currentPathIndex = movementState.currentPathIndex;

      if (!movementState.path || currentPathIndex >= movementState.path.length) {
        // This case should ideally be hit when path is completed
        console.log("📍 Movement complete - path index out of bounds or path empty");
        setMovementState((prev) => ({ ...prev, isMoving: false }));

        // --- Call the stored onComplete callback --- 
        if (currentOnComplete) {
            console.log("✅ Calling stored onComplete callback");
            currentOnComplete();
            setCurrentOnComplete(null); // Clear after calling
        }
        // --- End onComplete call ---

        // --- Fix Idle Animation Logic --- 
        const completedAnimation = animationRef.current;
        let idleAnimation = CharacterAnimationType.IDLE_DOWN;
        if (completedAnimation === CharacterAnimationType.WALK_UP) {
          idleAnimation = CharacterAnimationType.IDLE_UP;
        } else if (completedAnimation === CharacterAnimationType.WALK_LEFT) {
          idleAnimation = CharacterAnimationType.IDLE_LEFT;
        } else if (completedAnimation === CharacterAnimationType.WALK_RIGHT) {
          idleAnimation = CharacterAnimationType.IDLE_RIGHT;
        } // Defaults to IDLE_DOWN otherwise
        
        console.log("📍 Setting idle animation:", idleAnimation);
        // --- End Idle Animation Fix ---
        setAnimation?.(idleAnimation);
        
        setCurrentFrame(0);
        setFrameTimeAccumulator(0);
        if (setPosition) {
          setPosition([currentPos.x, currentPos.y, currentPos.z]);
        }
        if (onMoveComplete) onMoveComplete();
        return;
      }

      const target = movementState.path[currentPathIndex];
      // Ensure Z position is maintained correctly if needed
      const targetPos = new THREE.Vector3(target.x, target.y, currentPos.z);
      const distance = currentPos.distanceTo(targetPos);

      // Check if target is reached
      if (distance < 0.01) {
        console.log("📍 Reached target", currentPathIndex, ". Final position:", [target.x, target.y, currentPos.z]);
        // Snap to target position
        currentPos.x = target.x;
        currentPos.y = target.y;
        if (setPosition) {
          setPosition([target.x, target.y, currentPos.z]);
        }
        
        setMovementState((prev) => ({ ...prev, isMoving: false }));

        if (currentOnComplete) {
          console.log("✅ Calling stored onComplete callback after reaching target");
          currentOnComplete();
          setCurrentOnComplete(null);
        }

        // --- Fix Idle Animation Logic (Copied from above block) --- 
        const completedAnimation = animationRef.current;
        let idleAnimation = CharacterAnimationType.IDLE_DOWN;
        if (completedAnimation === CharacterAnimationType.WALK_UP) {
          idleAnimation = CharacterAnimationType.IDLE_UP;
        } else if (completedAnimation === CharacterAnimationType.WALK_LEFT) {
          idleAnimation = CharacterAnimationType.IDLE_LEFT;
        } else if (completedAnimation === CharacterAnimationType.WALK_RIGHT) {
          idleAnimation = CharacterAnimationType.IDLE_RIGHT;
        }
        console.log("📍 Setting idle animation:", idleAnimation);
        // --- End Idle Animation Fix --- 
        setAnimation?.(idleAnimation);
        
        setCurrentFrame(0);
        setFrameTimeAccumulator(0);
        if (onMoveComplete) onMoveComplete();
        return;
      }

      // Calculate movement vector towards the single target in the path
      const moveDirection = new THREE.Vector3()
        .subVectors(targetPos, currentPos)
        .normalize();
      let movement = moveDirection.clone().multiplyScalar(speed * delta);
      
      if (movement.length() >= distance) {
        movement.setLength(distance);
      }
      
      const newPosition = currentPos.clone().add(movement);
      
      console.log(`📍 Moving character. Delta: ${delta.toFixed(4)}, Speed: ${speed}, Target: [${target.x.toFixed(2)}, ${target.y.toFixed(2)}], Dist: ${distance.toFixed(4)}, Movement:`, [movement.x.toFixed(4), movement.y.toFixed(4)], "New Pos:", [newPosition.x.toFixed(4), newPosition.y.toFixed(4)]);
      
      // Update state ONLY
      if (setPosition) {
        setPosition([newPosition.x, newPosition.y, newPosition.z]);
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
        {random > 0.5 ? (
          <CharacterHair animation={animationRef.current} />
        ) : (
          <CharacterHat animation={animationRef.current} />
        )}

        <CharacterOutfit animation={animationRef.current} />
        <CharacterCloak animation={animationRef.current} />
        <planeGeometry args={[1, 1]} />
        <meshStandardMaterial
          map={texture}
          transparent={true}
          roughness={0.5}
          metalness={0.0}
          side={THREE.DoubleSide}
        />
      </mesh>
    );
  }
);

// Exportar tudo em uma única linha
export type { MovementState, Position };
export default CharacterBody;
