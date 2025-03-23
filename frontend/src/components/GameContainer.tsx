import { Canvas } from "@react-three/fiber";
import React, { useRef, useState } from "react";
import { Point } from "./CharacterSprite";
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
  const characterRef = useRef<{ moveAlongPath: (path: Point[]) => void }>(null);
  const [lightIntensity, setLightIntensity] = useState(1);
  const [lightDistance, setLightDistance] = useState(5);
  const [lightDecay, setLightDecay] = useState(2);

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
        />
      </Canvas>
      <GameUI
        characterRef={characterRef}
        lightIntensity={lightIntensity}
        lightDistance={lightDistance}
        lightDecay={lightDecay}
        onLightIntensityChange={setLightIntensity}
        onLightDistanceChange={setLightDistance}
        onLightDecayChange={setLightDecay}
      />
    </div>
  );
};

export default GameContainer;
