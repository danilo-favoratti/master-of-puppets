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
import { addToPosition, getX, getY, getZ, lerpPosition } from "../utils/positionUtils";
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
  
  // Movement state tracking - using useRef for immediate updates
  const movementStateRef = useRef<{
    lastSignature: string;
    lastTimestamp: number;
    continuousDirections: Record<string, boolean>;
  }>({
    lastSignature: "",
    lastTimestamp: 0,
    continuousDirections: {}
  });

  // Movement command buffering
  const moveBuffer = useRef<{
    active: boolean,
    direction: string,
    isRunning: boolean,
    steps: number,
    timer: ReturnType<typeof setTimeout> | null,
    callbacks: (() => void)[],
    execute: () => void
  }>({
    active: false,
    direction: '',
    isRunning: false,
    steps: 0,
    timer: null,
    callbacks: [],
    execute: () => {}
  });

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
    const target: Position = [
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
      
      // Use lerpPosition utility for consistent position interpolation
      const newPosition = lerpPosition(
        movementRef.current.start,
        movementRef.current.end,
        t
      );
      
      // Convert to [number, number, number] if needed
      setPosition([
        newPosition[0],
        newPosition[1],
        newPosition[2] || 0,
      ]);
      
      if (t === 1) {
        movementRef.current = null;
      }
    }
  });

  // Execute animation commands received from websocket
  useEffect(() => {
    // Function to flush the movement buffer and execute the consolidated command
    const flushMoveBuffer = () => {
      if (moveBuffer.current.active && characterRef.current) {
        const { direction, steps, isRunning, execute, callbacks } = moveBuffer.current;
        console.log(`🔄 Executing buffered move: ${direction}, steps=${steps}, running=${isRunning}, callbacks=${callbacks.length}`);
        execute();
        
        // Reset buffer
        moveBuffer.current.active = false;
        moveBuffer.current.steps = 0;
        moveBuffer.current.callbacks = [];
        
        if (moveBuffer.current.timer) {
          clearTimeout(moveBuffer.current.timer);
          moveBuffer.current.timer = null;
        }
      }
    };

    const handleCommand = (
      cmd: string,
      result: string,
      params: any,
      onComplete: () => void
    ) => {
      console.log(`🎮 Animation command execution in Game.tsx: ${cmd}`, params);

      switch (cmd) {
        case "update_map":
          // Update the map data with the new data from the server
          if (params && typeof params === "object") {
            setGameDataState(params);
          }
          onComplete(); // Non-animation command, complete immediately
          break;

        case "generate_world":
          onComplete(); // Non-animation command, complete immediately
          break;

        case "move":
        case "move_step":
          if (params.direction && characterRef.current) {
            const direction = params.direction;
            const steps = typeof params.steps === 'number' && params.steps > 0 ? params.steps : 1;
            const isContinuous = params.continuous === true;
            const isRunning = params.is_running === true;

            // For continuous movement, execute immediately without buffering
            if (isContinuous) {
              if (moveBuffer.current.active) {
                // Flush any pending buffered commands first
                flushMoveBuffer();
              }
              
              try {
                // Clear existing movement state reference if needed
                if (movementStateRef.current.continuousDirections[direction] && !isContinuous) {
                  delete movementStateRef.current.continuousDirections[direction];
                  console.log(`🛑 Clearing continuous movement state for ${direction}`);
                }
                
                // Set continuous movement state
                movementStateRef.current.continuousDirections[direction] = true;
                console.log(`📣 Game.tsx: Starting continuous movement in direction ${direction}`);
                
                // For continuous movement, use empty callback
                characterRef.current.move(direction, steps, () => {});
              } catch (error) {
                console.error(`🔴 Error executing continuous movement: ${error}`);
              }
              onComplete();
              return;
            }

            // CRITICAL FIX: Force move commands to execute immediately if there's only one command
            // This ensures single commands are never delayed
            if (!moveBuffer.current.active) {
              // Start a new buffer
              moveBuffer.current = {
                active: true,
                direction,
                isRunning,
                steps,
                callbacks: [onComplete],
                timer: setTimeout(flushMoveBuffer, 50), // 50ms buffer window
                execute: () => {
                  try {
                    if (characterRef.current) {
                      console.log(`📣 Game.tsx: Calling move(${direction}, steps=${steps}, continuous=${isContinuous})`);
                      characterRef.current.move(direction, steps, () => {
                        // Call all buffered callbacks after movement completes
                        console.log(`🏁 Move completed: ${direction}, steps=${steps}`);
                        moveBuffer.current.callbacks.forEach(cb => cb());
                      });
                    } else {
                      // If character ref is missing, still call all callbacks
                      moveBuffer.current.callbacks.forEach(cb => cb());
                    }
                  } catch (error) {
                    console.error(`🔴 Error executing movement: ${error}`);
                    moveBuffer.current.callbacks.forEach(cb => cb());
                  }
                }
              };
            } else if (moveBuffer.current.direction === direction && moveBuffer.current.isRunning === isRunning) {
              // If we already have commands queued, force flush the buffer and execute immediately
              // if we have more than 1 command buffered already
              if (moveBuffer.current.callbacks.length >= 1) {
                flushMoveBuffer();
                
                // Now create a new buffer with this command
                moveBuffer.current = {
                  active: true,
                  direction,
                  isRunning,
                  steps,
                  callbacks: [onComplete],
                  timer: setTimeout(flushMoveBuffer, 50),
                  execute: () => {
                    try {
                      if (characterRef.current) {
                        console.log(`📣 Game.tsx: Calling move(${direction}, steps=${steps}, continuous=${isContinuous})`);
                        characterRef.current.move(direction, steps, () => {
                          console.log(`🏁 Move completed: ${direction}, steps=${steps}`);
                          moveBuffer.current.callbacks.forEach(cb => cb());
                        });
                      } else {
                        moveBuffer.current.callbacks.forEach(cb => cb());
                      }
                    } catch (error) {
                      console.error(`🔴 Error executing movement: ${error}`);
                      moveBuffer.current.callbacks.forEach(cb => cb());
                    }
                  }
                };
              } else {
                // Add to existing buffer if same direction and running state
                moveBuffer.current.steps += steps;
                moveBuffer.current.callbacks.push(onComplete);
                
                // Update the execute function to use the new total
                moveBuffer.current.execute = () => {
                  try {
                    if (characterRef.current) {
                      const totalSteps = moveBuffer.current.steps;
                      console.log(`📣 Game.tsx: Calling consolidated move(${direction}, steps=${totalSteps}, continuous=${isContinuous})`);
                      characterRef.current.move(direction, totalSteps, () => {
                        // Call all buffered callbacks after movement completes
                        console.log(`🏁 Move completed: ${direction}, steps=${totalSteps}`);
                        moveBuffer.current.callbacks.forEach(cb => cb());
                      });
                    } else {
                      // If character ref is missing, still call all callbacks
                      moveBuffer.current.callbacks.forEach(cb => cb());
                    }
                  } catch (error) {
                    console.error(`🔴 Error executing consolidated movement: ${error}`);
                    moveBuffer.current.callbacks.forEach(cb => cb());
                  }
                };
                
                // Reset the timer
                if (moveBuffer.current.timer) {
                  clearTimeout(moveBuffer.current.timer);
                }
                moveBuffer.current.timer = setTimeout(flushMoveBuffer, 30); // Use shorter time for more responsiveness
              }
            } else {
              // Different direction or running state, flush current buffer and start new one
              flushMoveBuffer();
              
              // Start a new buffer
              moveBuffer.current = {
                active: true,
                direction,
                isRunning,
                steps,
                callbacks: [onComplete],
                timer: setTimeout(flushMoveBuffer, 50),
                execute: () => {
                  try {
                    if (characterRef.current) {
                      console.log(`📣 Game.tsx: Calling move(${direction}, steps=${steps}, continuous=${isContinuous})`);
                      characterRef.current.move(direction, steps, () => {
                        // Call all buffered callbacks after movement completes
                        console.log(`🏁 Move completed: ${direction}, steps=${steps}`);
                        moveBuffer.current.callbacks.forEach(cb => cb());
                      });
                    } else {
                      // If character ref is missing, still call all callbacks
                      moveBuffer.current.callbacks.forEach(cb => cb());
                    }
                  } catch (error) {
                    console.error(`🔴 Error executing movement: ${error}`);
                    moveBuffer.current.callbacks.forEach(cb => cb());
                  }
                }
              };
            }
          } else {
            console.warn(`🟠 Animation command ${cmd} missing direction or characterRef:`, { params, hasRef: !!characterRef.current });
            onComplete();
          }
          break;

        case "jump":
          // Flush any buffered movement first
          if (moveBuffer.current.active) {
            flushMoveBuffer();
          }
          
          console.log("🤸 Jump command received, needs implementation in Game.tsx handleCommand");
          onComplete(); // Complete immediately for now
          break;

        default:
          // Flush any buffered movement first
          if (moveBuffer.current.active) {
            flushMoveBuffer();
          }
          
          console.log(`Unknown command received in Game.tsx: ${cmd}. Calling onComplete.`);
          onComplete(); // Complete immediately for unhandled commands
      }
    };

    registerCommandHandler(handleCommand);

    // Clean up any pending buffer on unmount
    return () => {
      if (moveBuffer.current.timer) {
        clearTimeout(moveBuffer.current.timer);
      }
    };
  }, [registerCommandHandler, characterRef]);

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
        maxDistance={10}
        target={[position[0], position[1], 0]}
        makeDefault
        zoomSpeed={0.5}
        panSpeed={0.5}
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
