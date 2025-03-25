import { Canvas } from "@react-three/fiber";
import React, { useRef, useState, useEffect } from "react";
import { Point } from "./CharacterSprite";
import Game from "./Game";
import GameUI from "./GameUI";
import '../LoadingSpinner.css';

interface GameContainerProps {
  executeCommand: (commandName: string, result: string, params: any) => void;
  registerCommandHandler: (
      handler: (cmd: string, result: string, params: any) => void
  ) => void;
  mapData: any;
  isMapReady: boolean;
  characterRef: React.RefObject<any>;
  websocket?: WebSocket | null;
}

const GameContainer = ({
                         executeCommand,
                         registerCommandHandler,
                         mapData,
                         isMapReady,
                         characterRef,
                         websocket
                       }: GameContainerProps) => {
  const [lightIntensity, setLightIntensity] = useState(1.3);
  const [lightDistance, setLightDistance] = useState(4);
  const [lightDecay, setLightDecay] = useState(0.5);
  const [ambientLightIntensity, setAmbientLightIntensity] = useState(0);
  const [gameData, setGameData] = useState<any>(null);
  const [localMapData, setLocalMapData] = useState<any>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [hasTriedGenerateWorld, setHasTriedGenerateWorld] = useState(false);
  const [mapInitialized, setMapInitialized] = useState(false);

  // Log mapData changes from props
  useEffect(() => {
    if (mapData) {
      console.log('MapData prop changed:', mapData);
      setLocalMapData(mapData);

      // If we received valid map data, initialize the game
      if (!mapData.error && mapData.map) {
        setGameData(mapData);
        setIsLoading(false);
        setMapInitialized(true);
        console.log('Game initialized with valid map data from props');
      }
    }
  }, [mapData]);

  // WebSocket handler for direct map update events
  useEffect(() => {
    if (websocket) {
      const handleWebSocketMessage = (event: MessageEvent) => {
        try {
          const data = JSON.parse(event.data);
          if (data.type === 'map_created') {
            console.log('Map created event received in GameContainer:', data);

            // If we have valid map data in the event
            if (data.map_data && !data.map_data.error) {
              console.log('Valid map data received in WebSocket event, updating game');
              setLocalMapData(data.map_data);
              setGameData(data.map_data);
              setIsLoading(false);
              setMapInitialized(true);
              setHasTriedGenerateWorld(false);
            }
          }
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
        }
      };

      websocket.addEventListener('message', handleWebSocketMessage);

      return () => {
        websocket.removeEventListener('message', handleWebSocketMessage);
      };
    }
  }, [websocket]);

  // Only try to generate world if necessary and once
  useEffect(() => {
    // Don't do anything if we already have good map data
    if (mapInitialized) {
      console.log('Map already initialized, no need to generate world');
      return;
    }

    if (localMapData) {
      console.log('Processing localMapData:', localMapData);

      if (localMapData.error) {
        console.error('Map data error detected:', localMapData.error);

        // Only try to generate world once to prevent infinite loops
        if (!hasTriedGenerateWorld && websocket && websocket.readyState === WebSocket.OPEN) {
          console.log('Attempting to generate world (first attempt)');
          // Try directly asking the server for a map
          websocket.send(JSON.stringify({
            type: 'create_map',
            theme: 'abandoned prisioner'
          }));
          setHasTriedGenerateWorld(true);

          // Since we're waiting for the server, show loading indicator
          setIsLoading(true);
        } else if (hasTriedGenerateWorld) {
          console.log('Already attempted to generate world, showing fallback data');
          // After one attempt, use fallback data to avoid blocking UI
          setGameData({
            grid: [],
            entities: [],
            environment: { theme: "Lost Arch" }
          });
          setIsLoading(false);
        }
      } else {
        // We have valid map data
        console.log('Valid map data found in localMapData');
        setGameData(localMapData);
        setIsLoading(false);
        setMapInitialized(true);
      }
    }
  }, [localMapData, hasTriedGenerateWorld, websocket, mapInitialized]);

  // Initial world generation request - try once on mount
  useEffect(() => {
    if (!mapInitialized && !hasTriedGenerateWorld && websocket && websocket.readyState === WebSocket.OPEN) {
      console.log('Initial mount - requesting map generation');
      websocket.send(JSON.stringify({
        type: 'create_map',
        theme: 'abandoned prisioner'
      }));
      setHasTriedGenerateWorld(true);
    }
  }, [websocket, hasTriedGenerateWorld, mapInitialized]);

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
                  lightIntensity={1.5}
                  lightDistance={10}
                  lightDecay={1.5}
                  ambientLightIntensity={0.3}
              />
            </Canvas>
        )}
        <GameUI
            characterRef={characterRef}
            lightIntensity={lightIntensity}
            lightDistance={lightDistance}
            lightDecay={lightDecay}
            ambientLightIntensity={ambientLightIntensity}
            onLightIntensityChange={setLightIntensity}
            onLightDistanceChange={setLightDistance}ws:
            onAmbientLightIntensityChange={setAmbientLightIntensity}
        />
      </div>
  );
};

export default GameContainer;