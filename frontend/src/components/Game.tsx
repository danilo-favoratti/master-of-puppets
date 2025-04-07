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
import { GameData, Position } from "../types/game";
import CharacterBody from "./character/CharacterBody.tsx";
import GameEntities from "./GameEntities";
import MapDisplay from "./MapDisplay";

interface GameProps {
  executeCommand: (commandName: string, result: string, params: any, onComplete: () => void) => void;
  registerCommandHandler: (
    handler: (cmd: string, result: string, params: any, onComplete: () => void) => void
  ) => void;
  characterRef: React.RefObject<{
    moveAlongPath: (path: Position[]) => void;
    move: (direction: string, steps?: number, onComplete?: () => void) => void;
  }>;
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
    gameData || (gameDataJSON as unknown as GameData)
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
    const handleCommand = (
      cmd: string,
      result: string,
      params: any,
      onComplete: () => void
    ) => {
      //console.log(`🚀 Handling command in Game.tsx: ${cmd}`, { params });

      switch (cmd) {
        case "update_map":
          // Update the map data with the new data from the server
          if (params && typeof params === "object") {
            setGameDataState(params);
          }
          onComplete(); // Non-animation command, complete immediately
          break;

        case "generate_world":
          //console.log("Handling generate_world command (no action)");
          onComplete(); // Non-animation command, complete immediately
          break;

        case "move":
        case "move_step":
          if (params.direction && characterRef.current) {
            console.log(
              `🎮 Animation command execution in Game.tsx: ${cmd}`,
              params
            );
            const direction = params.direction;
            // Extract steps, default to 1 if not provided
            const steps = typeof params.steps === 'number' && params.steps > 0 ? params.steps : 1;

            try {
              if (typeof characterRef.current.move === "function") {
                console.log(
                  `📣 Game.tsx: Calling move(${direction}, steps=${steps}) on character ref for ${cmd}, passing onComplete`
                );
                characterRef.current.move(direction, steps, onComplete);
              } else {
                console.error(
                  "🔴 Character ref doesn't have a move method:",
                  characterRef.current
                );
                onComplete(); // Complete immediately if no move method
              }
            } catch (error) {
              console.error(
                `🔴 Error executing character move/animation for ${cmd}:`,
                error
              );
              onComplete(); // Complete immediately on error
            }
          } else {
            console.warn(
              `🟠 Animation command ${cmd} missing direction or characterRef:`,
              { params, hasRef: !!characterRef.current }
            );
            onComplete(); // Complete immediately if params/ref missing
          }
          break;

        case "jump":
          console.log("🤸 Jump command received, needs implementation in Game.tsx handleCommand");
          onComplete(); // Complete immediately for now
          break;

        default:
          console.log(`Unknown command received in Game.tsx: ${cmd}. Calling onComplete.`);
          onComplete(); // Complete immediately for unhandled commands
      }
    };

    registerCommandHandler(handleCommand);

    // No cleanup needed for the handler itself
    // Return an empty function or handle specific cleanup if necessary
    return () => {
      // Optional: Unregister handler if App.tsx provides a way
    };
    // IMPORTANT: Remove executeCommand from dependencies if it causes infinite loops
  }, [registerCommandHandler, characterRef]); // Dependencies should be stable refs/functions

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
            entities={entities}
          />
        )}
    </>
  );
};

export default Game;
