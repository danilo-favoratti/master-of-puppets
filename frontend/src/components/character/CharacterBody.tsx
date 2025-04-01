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

const CharacterBody = forwardRef<
  { moveAlongPath: (path: Position[]) => void; move: (direction: string) => void },
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

    // Expor moveAlongPath através da ref
    useImperativeHandle(ref, () => ({
      moveAlongPath: (path: Position[]) => {
        setMovementState({
          path,
          currentPathIndex: 0,
          isMoving: true,
        });
      },
      // Add move method to handle direction-based movement
      move: (direction: string) => {
        // Get current position
        if (!meshRef.current) {
          console.error("📍 Move failed: meshRef.current is null");
          return;
        }
        
        console.log("📍 CharacterBody.move called with direction:", direction);
        
        const currentPos = meshRef.current.position;
        console.log("📍 Current position:", [currentPos.x, currentPos.y, currentPos.z]);
        
        let targetX = currentPos.x;
        let targetY = currentPos.y;
        
        // Calculate target position based on direction
        switch(direction.toLowerCase()) {
          case 'up':
            targetY += 1;
            break;
          case 'down':
            targetY -= 1;
            break;
          case 'left':
            targetX -= 1;
            break;
          case 'right':
            targetX += 1;
            break;
          default:
            console.warn(`Unknown direction: ${direction}`);
            return;
        }
        
        console.log("📍 Target position:", [targetX, targetY, currentPos.z]);
        
        // Create a path with just the target position
        const path: Position[] = [{ x: targetX, y: targetY }];
        
        // Set animation based on direction
        let newAnimation: CharacterAnimationType;
        switch(direction.toLowerCase()) {
          case 'up':
            newAnimation = CharacterAnimationType.WALK_UP;
            break;
          case 'down':
            newAnimation = CharacterAnimationType.WALK_DOWN;
            break;
          case 'left':
            newAnimation = CharacterAnimationType.WALK_LEFT;
            break;
          case 'right':
            newAnimation = CharacterAnimationType.WALK_RIGHT;
            break;
          default:
            newAnimation = CharacterAnimationType.WALK_DOWN;
        }
        
        // Update animation
        console.log("📍 Setting animation to:", newAnimation);
        if (setAnimation) {
          setAnimation(newAnimation);
        }
        
        // Use moveAlongPath to handle the movement
        console.log("📍 Setting movement state with path:", path);
        setMovementState({
          path,
          currentPathIndex: 0,
          isMoving: true,
        });
      }
    }));

    // Update movement in the animation frame
    useFrame((_, delta) => {
      if (!meshRef.current || !movementState.isMoving) return;

      const currentPos = meshRef.current.position;
      const currentPathIndex = movementState.currentPathIndex;

      if (currentPathIndex >= movementState.path.length) {
        console.log("📍 Movement complete - reached end of path");
        setMovementState((prev) => ({ ...prev, isMoving: false }));
        
        // Determine which idle animation to use based on current animation
        const currentAnimation = animationRef.current;
        let idleAnimation = CharacterAnimationType.IDLE_DOWN;
        
        if (currentAnimation === CharacterAnimationType.WALK_UP) {
          idleAnimation = CharacterAnimationType.IDLE_UP;
        } else if (currentAnimation === CharacterAnimationType.WALK_LEFT) {
          idleAnimation = CharacterAnimationType.IDLE_LEFT;
        } else if (currentAnimation === CharacterAnimationType.WALK_RIGHT) {
          idleAnimation = CharacterAnimationType.IDLE_RIGHT;
        }
        
        console.log("📍 Setting idle animation:", idleAnimation);
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
      const targetPos = new THREE.Vector3(target.x, target.y, currentPos.z);
      const distance = currentPos.distanceTo(targetPos);

      // Determinar a direção do movimento e atualizar a animação
      const dx = targetPos.x - currentPos.x;
      const dy = targetPos.y - currentPos.y;

      // Determinar a direção predominante e atualizar a animação global
      let newAnimation: CharacterAnimationType;
      if (Math.abs(dx) > Math.abs(dy)) {
        // Movimento horizontal
        if (dx > 0) {
          newAnimation = CharacterAnimationType.WALK_RIGHT;
        } else {
          newAnimation = CharacterAnimationType.WALK_LEFT;
        }
      } else {
        // Movimento vertical
        if (dy > 0) {
          newAnimation = CharacterAnimationType.WALK_UP;
        } else {
          newAnimation = CharacterAnimationType.WALK_DOWN;
        }
      }

      // Atualizar a animação apenas se mudou
      if (newAnimation !== animationRef.current) {
        console.log("📍 Updating animation during movement:", newAnimation);
        animationRef.current = newAnimation;
        if (setAnimation) {
          setAnimation(newAnimation);
        }
        // Reset frame time accumulator to start the animation from the beginning
        setFrameTimeAccumulator(0);
        setCurrentFrame(0);
      }

      if (distance < 0.1) {
        console.log("📍 Reached target", currentPathIndex, "moving to next target");
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
