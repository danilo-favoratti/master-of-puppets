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
import CharacterFace from "./CharacterFace";
import { CharacterPartRef } from "./CharacterCloak";

// Enable verbose movement logging
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

// Define the type for the mutable movement data stored in the ref
interface MovementData {
  path: Position[];
  currentPathIndex: number;
}

const CharacterBody = forwardRef<
  CharacterRefMethods,
  UpdatedCharacterBodyProps
>(
  (
    {
      position = [0, 0, 0],
      scale = [1, 1, 1],
      rows = 8,
      cols = 8,
      animation = CharacterAnimationType.IDLE_DOWN,
      characterType = undefined,
      onAnimationComplete,
      speed = 1,
      setPosition,
      setAnimation,
      zOffset = 0.03, 
    },
    ref
  ) => {
    const meshRef = useRef<THREE.Mesh>(null);
    // Refs for child components
    const outfitRef = useRef<CharacterPartRef>(null);
    const cloakRef = useRef<CharacterPartRef>(null);
    const faceRef = useRef<CharacterPartRef>(null);
    const hairRef = useRef<CharacterPartRef>(null);
    const hatRef = useRef<CharacterPartRef>(null);

    // Log initial prop value
    console.log("[CharacterBody] Initial animation prop:", animation);

    const [currentOnComplete, setCurrentOnComplete] = useState<(() => void) | null>(null);
    const [texture, setTexture] = useState<THREE.Texture | null>(null);
    const [currentFrame, setCurrentFrame] = useState(0);
    // Use ref for the time accumulator used within the animation useFrame
    const frameTimeAccumulatorRef = useRef(0);
    const animationRef = useRef(animation);
    // Log initial ref value
    console.log("[CharacterBody] Initial animationRef.current:", animationRef.current);
    const [selectedCharacter, setSelectedCharacter] = useState<{
      type: CharacterBodyType;
      sprite: string;
    } | null>(null);

    // Use useRef for mutable movement data accessed within useFrame
    const movementRef = useRef<MovementData>({ path: [], currentPathIndex: 0 });
    // Use useState for isMoving to trigger renders and useFrame execution
    const [isMoving, setIsMoving] = useState(false);

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
          movementLog("✅ Base body texture loaded successfully:", selectedCharacter.sprite);
          loadedTexture.magFilter = THREE.NearestFilter;
          loadedTexture.minFilter = THREE.NearestFilter;
          loadedTexture.wrapS = loadedTexture.wrapT = THREE.RepeatWrapping;
          loadedTexture.repeat.set(1 / cols, 1 / rows);
          setTexture(loadedTexture);
        },
        undefined, // Optional progress callback
        (error) => {
          // Add explicit error logging
          console.error(
            `🚨 Error loading base body texture: ${selectedCharacter.sprite}`,
            error
          );
          setTexture(null); // Ensure texture is null on error
        }
      );
    }, [selectedCharacter, rows, cols]);

    // Update animation ref when animation prop changes
    useEffect(() => {
      animationRef.current = animation;
      // Reset frame time accumulator ref
      frameTimeAccumulatorRef.current = 0;
      setCurrentFrame(0); // Reset visible frame state too
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
        // Update the ref directly
        movementRef.current = { path, currentPathIndex: 0 };
        // Trigger movement start
        setIsMoving(true);
        movementLog("📍 Setting movement ref (moveAlongPath):", movementRef.current);
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
            // Use array format for Position
            path.push([targetX, targetY]);
            movementLog(`📍 Adding step ${i}/${steps} to path:`, [targetX, targetY]);
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

        // Update the ref directly
        movementRef.current = { path, currentPathIndex: 0 };
        // Trigger movement start
        setIsMoving(true);
        movementLog("📍 Setting movement ref (move):", movementRef.current);
      },
    }));

    // Update movement in the animation frame
    useFrame((_, delta) => {
      // Read isMoving state to determine if loop should run
      if (!isMoving) return;

      // Access mutable data via ref
      const moveData = movementRef.current;

      // Add START log - Read index from ref
      movementLog("-> Frame Start", {
        pathLen: moveData.path?.length,
        idx: moveData.currentPathIndex,
      });

      if (!meshRef.current) return;

      const currentPos = meshRef.current.position;
      const currentPathIndex = moveData.currentPathIndex;

      // Check if path is valid and index is within bounds
      if (
        !moveData.path ||
        currentPathIndex < 0 ||
        currentPathIndex >= moveData.path.length
      ) {
        movementLog("📍 Path exhausted or index invalid. Stopping movement.");
        // Update ref and state to stop
        moveData.path = [];
        moveData.currentPathIndex = 0;
        // Only set isMoving state here if it wasn't already set by reaching final target
        if (isMoving) { 
            setIsMoving(false);
        }

        // DO NOT call onComplete here, it was called when the final target was reached
        // if (currentOnComplete) { ... }
        // Reset the stored callback defensively
        setCurrentOnComplete(null); 

        // Don't set idle animation again if we just finished
        // setAnimation?.(idleAnimation); 

        // Don't set position again
        // if (setPosition) { ... } 

        return; // Exit frame immediately after stopping
      }

      // --- Target Calculation --- 
      const target = moveData.path[currentPathIndex];
      const targetPos = new THREE.Vector3(target[0], target[1], currentPos.z); // Use current Z
      const distance = currentPos.distanceTo(targetPos);
      // Add TARGET log
      movementLog("  Targeting:", { target, dist: distance.toFixed(3) });

      // --- Check if Current Target Reached --- 
      if (distance < 0.01) {
        movementLog(`📍 Reached target ${currentPathIndex}:`, target);
        // Snap to target position using array indexing
        currentPos.x = target[0];
        currentPos.y = target[1];
        if (setPosition) {
          // Use array indexing for Position
          setPosition([target[0], target[1], currentPos.z]); // Update store with exact target
        }

        // --- Advance to Next Path Index --- 
        const nextPathIndex = currentPathIndex + 1;

        // --- Check if Entire Path Completed --- 
        if (nextPathIndex >= moveData.path.length) {
          movementLog("🏁 Reached FINAL target in path. Stopping movement.");
          // Update ref and state to stop
          moveData.path = [];
          moveData.currentPathIndex = 0;
          setIsMoving(false); // Set state to stop rendering loop

          if (currentOnComplete) {
            movementLog("✅ Calling stored onComplete callback (final target).");
            currentOnComplete();
            setCurrentOnComplete(null);
          }

          const completedAnimation = animationRef.current;
          let idleAnimation = CharacterAnimationType.IDLE_DOWN;
          if (completedAnimation === CharacterAnimationType.WALK_UP)
            idleAnimation = CharacterAnimationType.IDLE_UP;
          else if (completedAnimation === CharacterAnimationType.WALK_LEFT)
            idleAnimation = CharacterAnimationType.IDLE_LEFT;
          else if (completedAnimation === CharacterAnimationType.WALK_RIGHT)
            idleAnimation = CharacterAnimationType.IDLE_RIGHT;
          movementLog("📍 Setting idle animation (final target):", idleAnimation);
          setAnimation?.(idleAnimation);

          return; // Exit frame immediately after stopping and completing
        } else {
          // --- More Steps Remain: Update Index and Continue --- 
          movementLog(`📍 Advancing to next target index: ${nextPathIndex}`);
          // Directly mutate the ref's current value
          movementLog("  BEFORE mutating movementRef.current.currentPathIndex", { nextIdx: nextPathIndex });
          moveData.currentPathIndex = nextPathIndex;
          movementLog("  AFTER mutating movementRef.current.currentPathIndex", { currentIdx: moveData.currentPathIndex });
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

        // Use array indexing for Position in log
        movementLog(`  Moving towards target ${currentPathIndex} (${target[0].toFixed(2)}, ${target[1].toFixed(2)}). Dist: ${distance.toFixed(3)}`);
        // Add log for calculated new position
        movementLog("    Calculated move:", { movement: { x: movement.x.toFixed(3), y: movement.y.toFixed(3) }, newPos: { x: newPosition.x.toFixed(3), y: newPosition.y.toFixed(3) } });

        // Explicitly update the mesh position for this frame
        meshRef.current.position.copy(newPosition);

        // Update position state store as well (if applicable)
        if (setPosition) {
          // Add log BEFORE store update
          movementLog("    BEFORE setPosition (store)", { pos: [newPosition.x, newPosition.y, newPosition.z] });
          setPosition([newPosition.x, newPosition.y, newPosition.z]);
          // Add log AFTER store update
          movementLog("    AFTER setPosition (store)");
        }
      }
       // Add END log
       movementLog("<- Frame End")
    });

    // Keep the separate useFrame for texture animation
    useFrame((_, delta) => {
      if (!texture) {
        // If texture is null, don't try to animate
        return;
      }

      const animationConfig = ANIMATIONS[animationRef.current];
      if (!animationConfig || !animationConfig.frames || animationConfig.frames.length === 0) {
        movementLog(" Anim Frame: No valid config/frames for", animationRef.current);
        // Optionally set a default static frame if config is bad
        // setTextureOffsetFromFrame(0); 
        return;
      }

      const animationFrames = animationConfig.frames;
      const frameTiming =
        animationConfig.frameTiming || animationFrames.map(() => 150); // Default timing if missing
      const shouldLoop = animationConfig.loop !== false;

      // If only one frame defined, just display it and return
      if (animationFrames.length === 1) {
        const frameToShow = animationFrames[0];
        movementLog(" Anim Frame: Single frame", frameToShow);
        if (currentFrame !== frameToShow) { 
          setCurrentFrame(frameToShow);
          setTextureOffsetFromFrame(frameToShow);
        }
        return;
      }

      // Accumulate time using ref
      frameTimeAccumulatorRef.current += delta * 1000;
      const currentAccumulator = frameTimeAccumulatorRef.current;
      
      let timeSum = 0;
      let frameIndex = 0;
      const totalDuration = frameTiming.reduce((sum, time) => sum + time, 0);

      if (!shouldLoop && currentAccumulator >= totalDuration) {
        frameIndex = animationFrames.length - 1; // Stay on the last frame
      } else {
        const normalizedTime = shouldLoop
          ? currentAccumulator % totalDuration
          : currentAccumulator; // No need for Math.min if checking >= totalDuration above

        for (let i = 0; i < frameTiming.length; i++) {
          timeSum += frameTiming[i];
          if (normalizedTime < timeSum) {
            frameIndex = i;
            break;
          }
           // Handle edge case where time lands exactly on boundary
          if (i === frameTiming.length - 1 && normalizedTime >= timeSum) {
            frameIndex = i;
          }
        }
      }

      const frameToShow = animationFrames[frameIndex];
      movementLog(" Anim Frame: Calculated", { anim: animationRef.current, idx: frameIndex, frame: frameToShow, current: currentFrame, accum: currentAccumulator });

      // Update the main body texture offset FIRST
      setTextureOffsetFromFrame(frameToShow);
      if (texture) texture.needsUpdate = true;

      // Imperatively update children 
      outfitRef.current?.setFrame(frameToShow);
      cloakRef.current?.setFrame(frameToShow);
      faceRef.current?.setFrame(frameToShow);
      hairRef.current?.setFrame(frameToShow);
      hatRef.current?.setFrame(frameToShow);

      if (!shouldLoop && frameIndex === animationFrames.length - 1) {
        movementLog(" Anim Frame: Non-loop complete", animationRef.current);
        onAnimationComplete?.(animationRef.current);
        // No return here, let it display the last frame
      }
    });

    // Base position uses zOffset prop
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
        // Control visibility based on texture loaded state
        visible={!!texture} 
      >
        {/* --- Attach Refs to Children (remove frame prop) --- */}
        <CharacterOutfit ref={outfitRef} animation={animationRef.current} />
        <CharacterCloak ref={cloakRef} animation={animationRef.current} />
        <CharacterFace ref={faceRef} animation={animationRef.current} />
        {random > 0.5 ? (
          <CharacterHair ref={hairRef} animation={animationRef.current} />
        ) : (
          <CharacterHat ref={hatRef} animation={animationRef.current} />
        )}
        
        {/* Base Body Plane (at relative z=0 within the group) */}
        <planeGeometry args={[1, 1]} />
        {/* Ensure ONLY the standard material is active */}
        {/* <meshBasicMaterial color="red" side={THREE.DoubleSide} /> */}
        <meshStandardMaterial
          map={texture}          // Base texture
          transparent={true}     // Needed if spritesheet has alpha
          side={THREE.DoubleSide} // Render backface if needed
          roughness={0.5}      // Adjust appearance
          metalness={0.0}
          // depthWrite={false} // Keep commented out
        />
      </mesh>
    );
  }
);

// Exportar tudo em uma única linha
export type { Position };
export default CharacterBody;
