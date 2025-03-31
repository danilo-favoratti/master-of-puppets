import { OrbitControls } from "@react-three/drei";
import { useFrame, useThree } from "@react-three/fiber";
import React, { useEffect, useRef, useState } from "react";
import gameDataJSON from "../config/gameData.json";
import { useGameStore } from "../store/gameStore";
import { CharacterAnimationType } from "../types/animations";
import {
  CampFireEntity,
  GameEntity,
  PigEntity,
  PotEntity,
} from "../types/entities";
import { GameData } from "../types/game";
import CharacterBody from "./character/CharacterBody.tsx";
import GameEntities from "./GameEntities";
import MapDisplay from "./MapDisplay";

interface GameProps {
  executeCommand: (commandName: string, result: string, params: any) => void;
  registerCommandHandler: (
    handler: (cmd: string, result: string, params: any) => void
  ) => void;
  characterRef: React.RefObject<{ moveAlongPath: (path: Point[]) => void }>;
  lightIntensity: number;
  lightDistance: number;
  lightDecay: number;
  ambientLightIntensity?: number;
  gameData?: GameData | null; // Updated type to GameData | null
}

const Game = ({
  executeCommand,
  registerCommandHandler,
  characterRef,
  lightIntensity,
  lightDistance,
  lightDecay,
  ambientLightIntensity = 0,
  gameData = null, // Default to null if not provided
}: GameProps) => {
  const { camera } = useThree();
  const position = useGameStore((state) => state.position);
  const setPosition = useGameStore((state) => state.setPosition);
  const currentAnimation = useGameStore((state) => state.currentAnimation);
  const setAnimation = useGameStore((state) => state.setAnimation);
  const isManualAnimation = useGameStore((state) => state.isManualAnimation);
  const setManualAnimation = useGameStore((state) => state.setManualAnimation);
  const [isPushing, setIsPushing] = useState(false);
  const [isPulling, setIsPulling] = useState(false);
  const [isJumping, setIsJumping] = useState(false);

  // Use provided gameData if available, otherwise use the default from JSON
  const [gameDataState, setGameDataState] = useState<GameData>(
    gameData || (gameDataJSON as GameData)
  );

  // Initialize entities from gameDataState with fallback to empty array
  const [entities, setEntities] = useState<GameEntity[]>(
    gameDataState?.entities || []
  );

  // Update gameData when it changes
  useEffect(() => {
    if (gameData) {
      setGameDataState(gameData);
      // Only update entities if they exist in gameData
      if (gameData.entities) {
        setEntities(gameData.entities);
      }
    }
  }, [gameData]);

  // Speed constants
  const walkSpeed = 0.05; // unused now
  const runSpeed = 0.1; // unused now

  // Movement interpolation ref
  const movementRef = useRef<null | {
    start: [number, number, number];
    end: [number, number, number];
    duration: number;
    elapsedTime: number;
  }>(null);
  const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

  const animateMovement = (
    delta: number,
    duration: number,
    direction: string
  ) => {
    const currentPos = position;
    let dx = 0,
      dy = 0,
      dz = 0;
    if (direction === "up") dy = delta;
    else if (direction === "down") dy = -delta;
    else if (direction === "left") dx = -delta;
    else if (direction === "right") dx = delta;
    const target: [number, number, number] = [
      currentPos[0] + dx,
      currentPos[1] + dy,
      currentPos[2] + dz,
    ];
    movementRef.current = {
      start: currentPos,
      end: target,
      duration: duration,
      elapsedTime: 0,
    };
  };

  // Smoothly update position based on movementRef using useFrame
  useFrame((_, delta) => {
    if (movementRef.current) {
      movementRef.current.elapsedTime += delta;
      let t = movementRef.current.elapsedTime / movementRef.current.duration;
      if (t > 1) t = 1;
      setPosition([
        lerp(movementRef.current.start[0], movementRef.current.end[0], t),
        lerp(movementRef.current.start[1], movementRef.current.end[1], t),
        lerp(movementRef.current.start[2], movementRef.current.end[2], t),
      ]);
      if (t === 1) {
        movementRef.current = null;
      }
    }
  });

  // Execute animation commands received from websocket
  useEffect(() => {
    // Define a mapping of commands to animation functions
    const commandMap: Record<string, (params: any) => void> = {
      jump: (params) => {
        const direction = params?.direction || "down";
        let animation: CharacterAnimationType;
        const originalPos = position;
        switch (direction) {
          case "up":
            animation = CharacterAnimationType.JUMP_UP;
            animateMovement(0.2, 0.5, "up");
            break;
          case "left":
            animation = CharacterAnimationType.JUMP_LEFT;
            animateMovement(0.2, 0.5, "left");
            break;
          case "right":
            animation = CharacterAnimationType.JUMP_RIGHT;
            animateMovement(0.2, 0.5, "right");
            break;
          default:
            animation = CharacterAnimationType.JUMP_DOWN;
            animateMovement(0.2, 0.5, "down");
        }
        setAnimation(animation);
        setIsJumping(true);
        // After first phase (0.5 sec), animate back to original position
        setTimeout(() => {
          movementRef.current = {
            start: position,
            end: originalPos,
            duration: 0.5,
            elapsedTime: 0,
          };
          setIsJumping(false);
        }, 500);
      },

      walk: (params) => {
        const direction = params?.direction || "down";
        let animation: CharacterAnimationType;
        const moveDistance = 1.0; // Distance to move
        switch (direction) {
          case "up":
            animation = CharacterAnimationType.WALK_UP;
            animateMovement(1.0, 1.0, "up");
            break;
          case "left":
            animation = CharacterAnimationType.WALK_LEFT;
            animateMovement(1.0, 1.0, "left");
            break;
          case "right":
            animation = CharacterAnimationType.WALK_RIGHT;
            animateMovement(1.0, 1.0, "right");
            break;
          default:
            animation = CharacterAnimationType.WALK_DOWN;
            animateMovement(1.0, 1.0, "down");
        }
        setAnimation(animation);
        // After walking duration, revert to idle animation
        setTimeout(() => {
          if (animation === CharacterAnimationType.WALK_UP) {
            setAnimation(CharacterAnimationType.IDLE_UP);
          } else if (animation === CharacterAnimationType.WALK_LEFT) {
            setAnimation(CharacterAnimationType.IDLE_LEFT);
          } else if (animation === CharacterAnimationType.WALK_RIGHT) {
            setAnimation(CharacterAnimationType.IDLE_RIGHT);
          } else {
            setAnimation(CharacterAnimationType.IDLE_DOWN);
          }
        }, 1000);
      },

      run: (params) => {
        const direction = params?.direction || "down";
        let animation: CharacterAnimationType;
        const moveDistance = 2.0; // Distance to move when running
        switch (direction) {
          case "up":
            animation = CharacterAnimationType.RUN_UP;
            animateMovement(2.0, 0.6, "up");
            break;
          case "left":
            animation = CharacterAnimationType.RUN_LEFT;
            animateMovement(2.0, 0.6, "left");
            break;
          case "right":
            animation = CharacterAnimationType.RUN_RIGHT;
            animateMovement(2.0, 0.6, "right");
            break;
          default:
            animation = CharacterAnimationType.RUN_DOWN;
            animateMovement(2.0, 0.6, "down");
        }
        setAnimation(animation);
        // After running, revert to idle
        setTimeout(() => {
          if (animation === CharacterAnimationType.RUN_UP) {
            setAnimation(CharacterAnimationType.IDLE_UP);
          } else if (animation === CharacterAnimationType.RUN_LEFT) {
            setAnimation(CharacterAnimationType.IDLE_LEFT);
          } else if (animation === CharacterAnimationType.RUN_RIGHT) {
            setAnimation(CharacterAnimationType.IDLE_RIGHT);
          } else {
            setAnimation(CharacterAnimationType.IDLE_DOWN);
          }
        }, 600);
      },

      // Other commands (push, pull) remain unchanged
      push: (params) => {
        const direction = params?.direction || "down";
        let animation: CharacterAnimationType;
        switch (direction) {
          case "up":
            animation = CharacterAnimationType.PUSH_UP;
            break;
          case "left":
            animation = CharacterAnimationType.PUSH_LEFT;
            break;
          case "right":
            animation = CharacterAnimationType.PUSH_RIGHT;
            break;
          default:
            animation = CharacterAnimationType.PUSH_DOWN;
        }
        setAnimation(animation);
        setIsPushing(true);
        setTimeout(() => {
          setIsPushing(false);
          if (animation === CharacterAnimationType.PUSH_UP) {
            setAnimation(CharacterAnimationType.IDLE_UP);
          } else if (animation === CharacterAnimationType.PUSH_LEFT) {
            setAnimation(CharacterAnimationType.IDLE_LEFT);
          } else if (animation === CharacterAnimationType.PUSH_RIGHT) {
            setAnimation(CharacterAnimationType.IDLE_RIGHT);
          } else {
            setAnimation(CharacterAnimationType.IDLE_DOWN);
          }
        }, 800);
      },

      pull: (params) => {
        const direction = params?.direction || "down";
        let animation: CharacterAnimationType;
        switch (direction) {
          case "up":
            animation = CharacterAnimationType.PULL_UP;
            break;
          case "left":
            animation = CharacterAnimationType.PULL_LEFT;
            break;
          case "right":
            animation = CharacterAnimationType.PULL_RIGHT;
            break;
          default:
            animation = CharacterAnimationType.PULL_DOWN;
        }
        setAnimation(animation);
        setIsPulling(true);
        setTimeout(() => {
          setIsPulling(false);
          if (animation === CharacterAnimationType.PULL_UP) {
            setAnimation(CharacterAnimationType.IDLE_UP);
          } else if (animation === CharacterAnimationType.PULL_LEFT) {
            setAnimation(CharacterAnimationType.IDLE_LEFT);
          } else if (animation === CharacterAnimationType.PULL_RIGHT) {
            setAnimation(CharacterAnimationType.IDLE_RIGHT);
          } else {
            setAnimation(CharacterAnimationType.IDLE_DOWN);
          }
        }, 800);
      },
    };

    const handleCommand = (cmd: string, result: string, params: any) => {
      console.log(`Handling command: ${cmd}`, params);

      switch (cmd) {
        case "update_map":
          // Update the map data with the new data from the server
          if (params && typeof params === "object") {
            setGameDataState(params);
          }
          break;

        case "generate_world":
          console.log("Handling generate_world command");
          // This command is sent to request map generation
          // We'll just acknowledge it here since actual generation happens on the server
          break;

        case "move":
          // Handle character movement
          if (params.direction && characterRef.current) {
            const direction = params.direction;
            characterRef.current.move(direction);
          }
          break;

        default:
          console.log(`Unknown command received: ${cmd}`);
      }
    };

    registerCommandHandler(handleCommand);

    return () => {
      // Cleanup
    };
  }, [executeCommand, setAnimation, registerCommandHandler, position]);

  // Make camera follow the character
  useEffect(() => {
    camera.position.x = position[0];
    camera.position.y = position[1];
    // Don't reset the z position to preserve zoom level
  }, [camera, position]);

  const handleEntityStateChange = (entityId: string, newState: string) => {
    setEntities((prevEntities) =>
      prevEntities.map((entity) => {
        if (entity.id === entityId) {
          switch (entity.type) {
            case "pot":
              return { ...entity, state: newState as PotEntity["state"] };
            case "campfire":
              return { ...entity, state: newState as CampFireEntity["state"] };
            case "pig":
              return { ...entity, state: newState as PigEntity["state"] };
            default:
              return entity;
          }
        }
        return entity;
      })
    );
  };

  const handleEntityClick = (entityId: string, event: React.MouseEvent) => {
    const entity = entities.find((e) => e.id === entityId);
    if (entity) {
      console.log(`Clicked entity: ${entity.name}`);
      // Handle entity click logic here
    }
  };

  return (
    <>
      <ambientLight intensity={ambientLightIntensity} />
      <pointLight
        position={[position[0], position[1], 2]}
        intensity={lightIntensity}
        distance={lightDistance}
        decay={lightDecay}
      />

      <OrbitControls
        enableZoom={true}
        enablePan={true}
        enableRotate={false}
        minDistance={5}
        maxDistance={20}
        target={[position[0], position[1], 0]}
        makeDefault
      />

      {/* Only render entities if they exist */}
      {entities.length > 0 && (
        <GameEntities
          entities={entities}
          onEntityStateChange={handleEntityStateChange}
          onEntityClick={handleEntityClick}
        />
      )}

      <CharacterBody
        ref={characterRef}
        position={position}
        scale={[2, 2, 2]}
        rows={8}
        cols={8}
        animation={currentAnimation}
        setAnimation={setAnimation}
        setPosition={setPosition}
        onMoveComplete={() => {
          // Converter a animação de movimento para a respectiva animação idle
          switch (currentAnimation) {
            case CharacterAnimationType.WALK_UP:
              setAnimation(CharacterAnimationType.IDLE_UP);
              break;
            case CharacterAnimationType.WALK_LEFT:
              setAnimation(CharacterAnimationType.IDLE_LEFT);
              break;
            case CharacterAnimationType.WALK_RIGHT:
              setAnimation(CharacterAnimationType.IDLE_RIGHT);
              break;
            default:
              setAnimation(CharacterAnimationType.IDLE_DOWN);
          }
        }}
        zOffset={0.03}
      />

      {/* Only render map if grid, width, and height exist */}
      {gameDataState?.map?.grid &&
        gameDataState.map.width &&
        gameDataState.map.height && (
          <MapDisplay
            mapGridData={gameDataState.map.grid}
            width={gameDataState.map.width}
            height={gameDataState.map.height}
          />
        )}
    </>
  );
};

export default Game;
