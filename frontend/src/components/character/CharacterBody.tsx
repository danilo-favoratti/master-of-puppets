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

// Disable verbose movement logging
const VERBOSE_MOVEMENT_LOGGING = false;

// Helper function for conditional movement logging
const movementLog = (message: string, ...args: any[]) => {
  if (VERBOSE_MOVEMENT_LOGGING) {
    console.log(message, ...args);
  }
};

// Define the type for the ref methods including steps
export interface CharacterRefMethods {
  moveAlongPath: (path: Position[]) => void;
  move: (direction: string, steps?: number, onComplete?: () => void) => void;
}

// Remove onMoveComplete from props definition
interface UpdatedCharacterBodyProps extends Omit<CharacterBodyProps, 'onMoveComplete'> {}

const CharacterBody = forwardRef<
  // Use the defined type here
  CharacterRefMethods,
  // Use the updated props type
  UpdatedCharacterBodyProps 
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
      // Replace the existing move method with the updated logic below
      move: (direction: string, steps: number = 1, onComplete?: () => void) => {
        movementLog(`📍 CharacterBody.move called with direction: ${direction}, steps: ${steps}`);
        // Store the final onComplete callback to be called only when the *entire* path is traversed
        setCurrentOnComplete(() => onComplete || null);

        const currentLogicalX = position[0];
        const currentLogicalY = position[1];
        const currentZ = position[2] || 0.03; // Use prop Z or default Z offset
        movementLog("📍 Current logical position:", [currentLogicalX, currentLogicalY, currentZ]);

        const path: Position[] = [];
        let deltaX = 0;
        let deltaY = 0;

        // Determine the change per step based on direction
        switch (direction.toLowerCase()) {
          case 'up': deltaY = 1; break;
          case 'down': deltaY = -1; break;
          case 'left': deltaX = -1; break;
          case 'right': deltaX = 1; break;
          default:
            console.warn(`Unknown direction: ${direction}`);
            setCurrentOnComplete(null); // Clear callback
            onComplete?.(); // Call immediately as the command is invalid
            return;
        }

        // Generate intermediate path points for each step requested
        for (let i = 1; i <= steps; i++) {
            const targetX = currentLogicalX + deltaX * i;
            const targetY = currentLogicalY + deltaY * i;
            path.push({ x: targetX, y: targetY });
            movementLog(`📍 Adding step ${i}/${steps} to path:`, { x: targetX, y: targetY });
        }

        movementLog("📍 Final path calculated:", path);

        // If no steps were generated (steps <= 0), complete immediately
        if (path.length === 0) {
             movementLog("📍 Path is empty (steps <= 0?), completing immediately.");
             setCurrentOnComplete(null); // Clear callback
             onComplete?.(); // Call immediately
             return;
        }

        // Set the appropriate walking animation based on direction
        // This animation will persist for the duration of the path traversal
        let newAnimation: CharacterAnimationType;
        switch(direction.toLowerCase()) {
          case 'up': newAnimation = CharacterAnimationType.WALK_UP; break;
          case 'down': newAnimation = CharacterAnimationType.WALK_DOWN; break;
          case 'left': newAnimation = CharacterAnimationType.WALK_LEFT; break;
          case 'right': newAnimation = CharacterAnimationType.WALK_RIGHT; break;
          default: newAnimation = CharacterAnimationType.WALK_DOWN; // Sensible default
        }

        animationRef.current = newAnimation; // Update the ref used by useFrame animation logic
        movementLog("📍 Setting animation ref for movement:", newAnimation);
        if (setAnimation) {
          // Update state to potentially trigger immediate visual change
          setAnimation(newAnimation);
        }

        // Start the movement process using the generated multi-point path
        movementLog("📍 Setting movement state with multi-step path:", path);
        setMovementState({
          path,
          currentPathIndex: 0, // Start at the first step in the path
          isMoving: true,
        });
        // onComplete is NOT called here; it's stored in currentOnComplete
        // and will be called by useFrame when the *last* point in the path is reached.
      },
    }));

    // Update movement in the animation frame
    useFrame((_, delta) => {
      if (!meshRef.current || !movementState.isMoving) return;

      const currentPos = meshRef.current.position; // Still use live position for animation
      const currentPathIndex = movementState.currentPathIndex;

      // Check if path is valid and index is within bounds BEFORE accessing path[index]
      if (!movementState.path || currentPathIndex < 0 || currentPathIndex >= movementState.path.length) {
        // Path completed or invalid index - Stop movement
        movementLog("📍 Path exhausted or index invalid. Stopping movement.");
        setMovementState((prev) => ({ ...prev, isMoving: false, currentPathIndex: 0, path: [] })); // Reset path state

        // Call final completion callback if it exists
        if (currentOnComplete) {
          movementLog("✅ Calling stored onComplete callback (path exhausted).");
          currentOnComplete();
          setCurrentOnComplete(null);
        }

        // Set idle animation
        const completedAnimation = animationRef.current;
        let idleAnimation = CharacterAnimationType.IDLE_DOWN;
        if (completedAnimation === CharacterAnimationType.WALK_UP) idleAnimation = CharacterAnimationType.IDLE_UP;
        else if (completedAnimation === CharacterAnimationType.WALK_LEFT) idleAnimation = CharacterAnimationType.IDLE_LEFT;
        else if (completedAnimation === CharacterAnimationType.WALK_RIGHT) idleAnimation = CharacterAnimationType.IDLE_RIGHT;
        movementLog("📍 Setting idle animation (path exhausted):", idleAnimation);
        setAnimation?.(idleAnimation);

        // Update final position in store
        if (setPosition) {
          setPosition([currentPos.x, currentPos.y, currentPos.z]);
        }
        return; // Exit frame processing for this movement cycle
      }

      // --- Target Calculation --- 
      const target = movementState.path[currentPathIndex];
      const targetPos = new THREE.Vector3(target.x, target.y, currentPos.z); // Use current Z
      const distance = currentPos.distanceTo(targetPos);

      // --- Check if Current Target Reached --- 
      if (distance < 0.01) {
        movementLog(`📍 Reached target ${currentPathIndex}:`, target);
        // Snap to target position
        currentPos.x = target.x;
        currentPos.y = target.y;
        if (setPosition) {
          setPosition([target.x, target.y, currentPos.z]); // Update store with exact target
        }

        // --- Advance to Next Path Index --- 
        const nextPathIndex = currentPathIndex + 1;

        // --- Check if Entire Path Completed --- 
        if (nextPathIndex >= movementState.path.length) {
          movementLog("🏁 Reached FINAL target in path. Stopping movement.");
          setMovementState((prev) => ({ ...prev, isMoving: false, currentPathIndex: 0, path: [] })); // Reset path state

          // Call final completion callback
          if (currentOnComplete) {
            movementLog("✅ Calling stored onComplete callback (final target).");
            currentOnComplete();
            setCurrentOnComplete(null);
          }

          // Set idle animation based on the direction of the completed walk
          const completedAnimation = animationRef.current;
          let idleAnimation = CharacterAnimationType.IDLE_DOWN;
          if (completedAnimation === CharacterAnimationType.WALK_UP) idleAnimation = CharacterAnimationType.IDLE_UP;
          else if (completedAnimation === CharacterAnimationType.WALK_LEFT) idleAnimation = CharacterAnimationType.IDLE_LEFT;
          else if (completedAnimation === CharacterAnimationType.WALK_RIGHT) idleAnimation = CharacterAnimationType.IDLE_RIGHT;
          movementLog("📍 Setting idle animation (final target):", idleAnimation);
          setAnimation?.(idleAnimation);
          
          return; // Exit frame processing for this movement cycle
        } else {
          // --- More Steps Remain: Update Index and Continue --- 
          movementLog(`📍 Advancing to next target index: ${nextPathIndex}`);
          setMovementState((prev) => ({ ...prev, currentPathIndex: nextPathIndex }));
          // Do NOT return here, let the next frame handle movement towards the new target
        }

      } else {
        // --- Move Towards Current Target ---
        const moveDirection = new THREE.Vector3()
          .subVectors(targetPos, currentPos)
          .normalize();
        let movement = moveDirection.clone().multiplyScalar(speed * delta);

        // Prevent overshooting the target
        if (movement.length() >= distance) {
          movement.setLength(distance);
        }

        const newPosition = currentPos.clone().add(movement);

        movementLog(`📍 Moving towards target ${currentPathIndex} (${target.x.toFixed(2)}, ${target.y.toFixed(2)}). Dist: ${distance.toFixed(3)}`);

        // Explicitly update the mesh position for this frame
        meshRef.current.position.copy(newPosition);

        // Update position state store as well (if applicable)
        if (setPosition) {
          setPosition([newPosition.x, newPosition.y, newPosition.z]);
        }
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
