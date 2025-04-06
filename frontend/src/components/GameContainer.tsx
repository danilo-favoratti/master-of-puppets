import { Canvas } from "@react-three/fiber";
import React, { useEffect, useState, forwardRef } from "react";
import { ToolCall } from "../App";
import "../LoadingSpinner.css";
import { GameData } from "../types/game";
import Game from "./Game";
import GameDebugUI from "./GameDebugUI";
import { CharacterRefMethods } from "./character/CharacterBody";

interface GameContainerProps {
  executeCommand: (
    commandName: string,
    result: string,
    params: any,
    onComplete: () => void
  ) => void;
  registerCommandHandler: (
    handler: (
      cmd: string,
      result: string,
      params: any,
      onComplete: () => void
    ) => void
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

// Use forwardRef to allow passing ref to the component
const GameContainer = forwardRef<any, GameContainerProps>((
  {
    executeCommand,
    registerCommandHandler,
    mapData,
    isMapReady,
    characterRef,
    websocket,
    toolCalls,
  },
  ref
) => {
  const [ambientLightIntensity, setAmbientLightIntensity] = useState(0.1);
  const [lightIntensity, setLightIntensity] = useState(1.2);
  const [lightDistance, setLightDistance] = useState(6);
  const [lightDecay, setLightDecay] = useState(0.5);
  const [showDebugUi, setShowDebugUi] = useState(false);

  // Toggle Debug UI
  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "F8") {
        setShowDebugUi((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => {
      window.removeEventListener("keydown", handleKeyDown);
    };
  }, []);

  // Log when mapData is received and valid
  useEffect(() => {
    if (mapData?.map && mapData?.entities) {
      log("GameContainer received valid mapData prop:", mapData);
      // Try to find the player entity ("game-char") in the mapData entities
      const playerEntity = mapData.entities.find(entity => entity.id === 'game-char');
      if (playerEntity?.position) {
        const charInitialX = playerEntity.position[0]; 
        const charInitialY = playerEntity.position[1]; 
        console.log(`Player found in mapData. Initial Position: [${charInitialX}, ${charInitialY}]`);
      }
    } else if (mapData) {
        log("GameContainer received mapData prop, but it's missing map or entities:", mapData);
    } else {
        log("GameContainer mapData prop is null.");
    }
  }, [mapData]);

  // Directly render based on mapData prop
  // If mapData is null (meaning App.tsx hasn't received it yet), this component won't render anyway
  // due to the logic in App.tsx. If it *is* rendered, we assume mapData is valid.
  if (!mapData) {
    // This case should ideally not happen if App.tsx logic is correct,
    // but provides a fallback just in case.
    log("GameContainer rendered without mapData - showing fallback/nothing.")
    return (
        <div className="loading-container">
          <div className="loading-spinner"></div>
          <p>Waiting for map data...</p>
        </div>
    ); 
  }

  // Render the game canvas if mapData is present
  return (
    <div className="relative w-full h-full">
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
          gameData={mapData}
          lightIntensity={lightIntensity}
          lightDistance={lightDistance}
          lightDecay={lightDecay}
          ambientLightIntensity={ambientLightIntensity}
        />
      </Canvas>

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
});

export default GameContainer;
