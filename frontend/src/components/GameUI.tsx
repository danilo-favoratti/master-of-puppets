import React, { useState } from "react";
import { useGameStore } from "../store/gameStore";
import { Point } from "./CharacterSprite";
import LightControls from "./LightControls";

interface GameUIProps {
  characterRef: React.RefObject<{ moveAlongPath: (path: Point[]) => void }>;
  lightIntensity: number;
  lightDistance: number;
  lightDecay: number;
  onLightIntensityChange: (value: number) => void;
  onLightDistanceChange: (value: number) => void;
  onLightDecayChange: (value: number) => void;
}

const GameUI = ({
  characterRef,
  lightIntensity,
  lightDistance,
  lightDecay,
  onLightIntensityChange,
  onLightDistanceChange,
  onLightDecayChange,
}: GameUIProps) => {
  const position = useGameStore((state) => state.position);
  const [isMoving, setIsMoving] = useState(false);
  const [targetPosition, setTargetPosition] = useState<Point>({ x: 0, y: 0 });

  const moveToPosition = () => {
    if (isMoving || !characterRef.current) return;

    console.log("Tentando mover para:", targetPosition); // Debug

    // Criar um caminho simples
    const path = [targetPosition];

    setIsMoving(true);
    characterRef.current.moveAlongPath(path);

    // Resetar o estado de movimento após um tempo
    setTimeout(() => {
      setIsMoving(false);
    }, 1000);
  };

  return (
    <div
      style={{
        position: "fixed",
        top: "4px",
        left: "4px",
        backgroundColor: "black",
        opacity: 0.7,
        padding: "8px",
        borderRadius: "4px",
        zIndex: 50,
      }}
      className="flex flex-col gap-4 bg-black/70 p-4 rounded-lg z-50"
    >
      <div className="text-white text-sm">
        Posição Atual: ({position[0]}, {position[1]})
      </div>

      <div className="flex flex-col gap-2">
        <div className="text-white text-sm">Ir para posição:</div>
        <div className="flex gap-2">
          <input
            type="number"
            value={targetPosition.x}
            onChange={(e) =>
              setTargetPosition((prev) => ({
                ...prev,
                x: Number(e.target.value),
              }))
            }
            className="w-20 px-2 py-1 rounded bg-white/10 text-white"
            placeholder="X"
          />
          <input
            type="number"
            value={targetPosition.y}
            onChange={(e) =>
              setTargetPosition((prev) => ({
                ...prev,
                y: Number(e.target.value),
              }))
            }
            className="w-20 px-2 py-1 rounded bg-white/10 text-white"
            placeholder="Y"
          />
        </div>

        <button
          onClick={moveToPosition}
          disabled={isMoving}
          className={`px-4 py-2 rounded ${
            isMoving
              ? "bg-gray-500 cursor-not-allowed"
              : "bg-blue-500 hover:bg-blue-600"
          } text-white`}
        >
          {isMoving ? "Movendo..." : "Mover"}
        </button>
      </div>

      <LightControls
        intensity={lightIntensity}
        distance={lightDistance}
        decay={lightDecay}
        onIntensityChange={onLightIntensityChange}
        onDistanceChange={onLightDistanceChange}
        onDecayChange={onLightDecayChange}
      />
    </div>
  );
};

export default GameUI;
