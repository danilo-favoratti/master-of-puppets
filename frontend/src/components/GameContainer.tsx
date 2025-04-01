import { Canvas } from "@react-three/fiber";
import React, { useEffect, useState } from "react";
import "../LoadingSpinner.css";
import { GameData, Position } from "../types/game";
import Game from "./Game";
import GameDebugUI from "./GameDebugUI";
import { CharacterRefMethods } from "./character/CharacterBody";
import { ToolCall } from "../App";

interface GameContainerProps {
  executeCommand: (commandName: string, result: string, params: any, onComplete: () => void) => void;
  registerCommandHandler: (
    handler: (cmd: string, result: string, params: any, onComplete: () => void) => void
  ) => void;
  mapData: GameData | null;
  isMapReady: boolean;
  characterRef: React.RefObject<CharacterRefMethods>;
  websocket?: WebSocket | null;
  toolCalls: ToolCall[];
}

// Disable verbose logging
const VERBOSE_LOGGING = false;

// Helper function for conditional logging
const log = (message: string, ...args: any[]) => {
    if (VERBOSE_LOGGING) {
        console.log(message, ...args);
    }
};

const GameContainer = ({
  executeCommand,
  registerCommandHandler,
  mapData,
  isMapReady,
  characterRef,
  websocket,
  toolCalls,
}: GameContainerProps) => {
  const [ambientLightIntensity, setAmbientLightIntensity] = useState(0.1);
  const [lightIntensity, setLightIntensity] = useState(1.2);
  const [lightDistance, setLightDistance] = useState(6);
  const [lightDecay, setLightDecay] = useState(0.5);
  const [gameData, setGameData] = useState<any>(null);
  const [localMapData, setLocalMapData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasTriedGenerateWorld, setHasTriedGenerateWorld] = useState(false);
  const [mapInitialized, setMapInitialized] = useState(false);
  const [showDebugUi, setShowDebugUi] = useState(false);

  // change debug ui to true when key is pressed
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "l") {
        setShowDebugUi((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  // Log mapData changes from props
  useEffect(() => {
    if (mapData && isMapReady) {
      log("MapData prop changed and ready:", mapData);
      if (mapData.map && mapData.entities) {
        setGameData(mapData);
        setIsLoading(false);
        setMapInitialized(true);
        log("Game initialized with valid map data from props");
      } else {
        log(
          "Received mapData prop is missing map or entities:",
          mapData
        );
      }
    }
  }, [mapData, isMapReady]);

  // WebSocket handler for direct map update events
  useEffect(() => {
    if (websocket) {
      const handleWebSocketMessage = (event: MessageEvent) => {
        if (typeof event.data === "string") {
          try {
            const message = JSON.parse(event.data);
            if (VERBOSE_LOGGING) {
              log("GameContainer received message:", message);
            }
            if (message.type === "map_created") {
              log("Map created event received in GameContainer:", message);

              if (
                message.environment &&
                message.entities &&
                !message.environment.error &&
                message.environment.grid
              ) {
                const newMapData: GameData = {
                  map: {
                    width: message.environment.width,
                    height: message.environment.height,
                    grid: message.environment.grid,
                  },
                  entities: message.entities,
                };

                log(
                  "Valid map data received in WebSocket event, updating game:",
                  newMapData
                );
                setGameData(newMapData);
                setIsLoading(false);
                setMapInitialized(true);
                setHasTriedGenerateWorld(false);
              } else {
                log(
                  "Received map_created event via WebSocket missing expected properties or contains error:",
                  message
                );
              }
            }
          } catch (error) {
            log("GameContainer Error parsing WebSocket message:", error);
          }
        } else if (event.data instanceof ArrayBuffer) {
          // Handle binary messages (audio)
          if (VERBOSE_LOGGING) {
            log("GameContainer: Ignoring binary WebSocket message.");
          }
        }
      };

      websocket.addEventListener("message", handleWebSocketMessage);

      return () => {
        websocket.removeEventListener("message", handleWebSocketMessage);
      };
    }
  }, [websocket]);

  // Only try to generate world if necessary and once
  useEffect(() => {
    // Don't do anything if we already have good map data
    if (mapInitialized) {
      log("Map already initialized, no need to generate world");
      return;
    }

    if (localMapData) {
      log("Processing localMapData:", localMapData);

      if (localMapData.error) {
        log("Map data error detected:", localMapData.error);

        // Only try to generate world once to prevent infinite loops
        if (
          !hasTriedGenerateWorld &&
          websocket &&
          websocket.readyState === WebSocket.OPEN
        ) {
          log("Attempting to generate world (first attempt)");
          websocket.send(
            JSON.stringify({
              type: "text",
              content: "abandoned prisioner",
            })
          );
          setHasTriedGenerateWorld(true);

          // Since we're waiting for the server, show loading indicator
          setIsLoading(true);
        } else if (hasTriedGenerateWorld) {
          log(
            "Already attempted to generate world, showing fallback data"
          );
          // After one attempt, use fallback data to avoid blocking UI
          setGameData({
            map: { width: 0, height: 0, grid: [] },
            entities: [],
          });
          setIsLoading(false);
          setMapInitialized(true);
        }
      } else if (localMapData) {
        // We have valid map data
        log("Valid map data found in localMapData");
        setIsLoading(false);
        setMapInitialized(true);
      }
    }
  }, [localMapData, hasTriedGenerateWorld, websocket, mapInitialized]);

  // Initial world generation request - adjusted
  useEffect(() => {
    if (
      !mapInitialized &&
      !hasTriedGenerateWorld &&
      websocket &&
      websocket.readyState === WebSocket.OPEN
    ) {
      log("Initial mount - requesting map generation");
      websocket.send(
        JSON.stringify({
          type: "text",
          content: "abandoned prisioner",
        })
      );
      setHasTriedGenerateWorld(true);
      setIsLoading(true);
    }
  }, [websocket, hasTriedGenerateWorld, mapInitialized]);

  log("gameData", gameData);
  return (
    <div className="relative w-full h-full">
      {isLoading ? (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Creating your adventure world...</p>
        </div>
      ) : (
        <Canvas
          style={{
            width: "100%",
            height: "100%",
            position: "absolute",
            top: 0,
            left: 0,
          }}
          camera={{ position: [0, 0, 5], fov: 75 }}
          gl={{ antialias: true }}
        >
          <Game
            executeCommand={executeCommand}
            registerCommandHandler={registerCommandHandler}
            characterRef={characterRef}
            gameData={gameData}
            lightIntensity={lightIntensity}
            lightDistance={lightDistance}
            lightDecay={lightDecay}
            ambientLightIntensity={ambientLightIntensity}
          />
        </Canvas>
      )}

      {showDebugUi && (
        <GameDebugUI
          characterRef={characterRef}
          lightIntensity={lightIntensity}
          lightDistance={lightDistance}
          lightDecay={lightDecay}
          ambientLightIntensity={ambientLightIntensity}
          onLightIntensityChange={setLightIntensity}
          onLightDistanceChange={setLightDistance}
          onAmbientLightIntensityChange={setAmbientLightIntensity}
          onLightDecayChange={setLightDecay}
          toolCalls={toolCalls}
        />
      )}
    </div>
  );
};

export default GameContainer;
