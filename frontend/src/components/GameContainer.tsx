import { Canvas } from "@react-three/fiber";
import React, { useRef, useState } from "react";
import { Position } from "../types/game";
import Game from "./Game";
import GameUI from "./GameUI";
interface GameContainerProps {
  executeCommand: (commandName: string, result: string, params: any) => void;
  registerCommandHandler: (
    handler: (cmd: string, result: string, params: any) => void
  ) => void;
}

const GameContainer: React.FC<GameContainerProps> = ({
  executeCommand,
  registerCommandHandler,
}) => {
  const characterRef = useRef<{ moveAlongPath: (path: Position[]) => void }>(
    null
  );
  const [lightIntensity, setLightIntensity] = useState(1.3);
  const [lightDistance, setLightDistance] = useState(4);
  const [lightDecay, setLightDecay] = useState(0.5);
  const [ambientLightIntensity, setAmbientLightIntensity] = useState(0);

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
          lightIntensity={lightIntensity}
          lightDistance={lightDistance}
          lightDecay={lightDecay}
          ambientLightIntensity={ambientLightIntensity}
        />
      </Canvas>
      <GameUI
        characterRef={characterRef}
        lightIntensity={lightIntensity}
        lightDistance={lightDistance}
        lightDecay={lightDecay}
        ambientLightIntensity={ambientLightIntensity}
        onLightIntensityChange={setLightIntensity}
        onLightDistanceChange={setLightDistance}
        onLightDecayChange={setLightDecay}
        onAmbientLightIntensityChange={setAmbientLightIntensity}
      />
    </div>
  );
};

export default GameContainer;
