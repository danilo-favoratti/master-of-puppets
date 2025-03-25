import React, { useState } from "react";
import { useGameStore } from "../store/gameStore";
import { Position } from "../types/game";
import LightControls from "./LightControls";

interface GameUIProps {
  characterRef: React.RefObject<{ moveAlongPath: (path: Position[]) => void }>;
  lightIntensity: number;
  lightDistance: number;
  lightDecay: number;
  ambientLightIntensity: number;
  onLightIntensityChange: (value: number) => void;
  onLightDistanceChange: (value: number) => void;
  onLightDecayChange: (value: number) => void;
  onAmbientLightIntensityChange: (value: number) => void;
}

const GameUI = ({
  characterRef,
  lightIntensity,
  lightDistance,
  lightDecay,
  ambientLightIntensity,
  onLightIntensityChange,
  onLightDistanceChange,
  onLightDecayChange,
  onAmbientLightIntensityChange,
}: GameUIProps) => {
  const position = useGameStore((state) => state.position);
  const [isMoving, setIsMoving] = useState(false);
  const [targetPosition, setTargetPosition] = useState<Position>({
    x: 10,
    y: 10,
  });

  const moveToPosition = () => {
    if (isMoving || !characterRef.current) return;

    // Criar um caminho simples
    const path = [targetPosition];

    setIsMoving(true);
    characterRef.current.moveAlongPath(path);

    // Resetar o estado de movimento após um tempo
    setTimeout(() => {
      setIsMoving(false);
    }, 1000);
  };

  const moveDirection = (dx: number, dy: number) => {
    if (isMoving || !characterRef.current) return;

    const newTarget = {
      x: position[0] + dx,
      y: position[1] + dy,
    };

    setTargetPosition(newTarget);

    const path = [newTarget];

    setIsMoving(true);
    characterRef.current.moveAlongPath(path);

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

      <div className="flex flex-col gap-2" style={{ display: "flex" }}>
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
            className="w-20 p-2 rounded bg-white/10 text-white text-lg"
            placeholder="X"
            style={{ fontSize: "1.5rem", padding: "10px", width: "80px" }}
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
            style={{ fontSize: "1.5rem", padding: "10px", width: "80px" }}
          />
        </div>

        <button
          onClick={moveToPosition}
          disabled={isMoving}
          style={{ fontSize: "1.5rem" }}
          className={`px-4 py-2 rounded ${
            isMoving
              ? "bg-gray-500 cursor-not-allowed"
              : "bg-blue-500 hover:bg-blue-600"
          } text-white`}
        >
          {isMoving ? "Movendo..." : "Mover"}
        </button>
      </div>

      <div className="mt-4">
        <div className="flex justify-center mb-2">
          <button
            onClick={() => moveDirection(0, 1)}
            disabled={isMoving}
            className={`w-16 h-16 flex items-center justify-center rounded ${
              isMoving
                ? "bg-gray-500 cursor-not-allowed"
                : "bg-blue-500 hover:bg-blue-600"
            } text-white text-2xl`}
          >
            ↑
          </button>
        </div>
        <div className="flex justify-between">
          <button
            onClick={() => moveDirection(-1, 0)}
            disabled={isMoving}
            className={`w-16 h-16 flex items-center justify-center rounded ${
              isMoving
                ? "bg-gray-500 cursor-not-allowed"
                : "bg-blue-500 hover:bg-blue-600"
            } text-white text-2xl`}
          >
            ←
          </button>
          <button
            onClick={() => moveDirection(1, 0)}
            disabled={isMoving}
            className={`w-16 h-16 flex items-center justify-center rounded ${
              isMoving
                ? "bg-gray-500 cursor-not-allowed"
                : "bg-blue-500 hover:bg-blue-600"
            } text-white text-2xl`}
          >
            →
          </button>
        </div>
        <div className="flex justify-center mt-2">
          <button
            onClick={() => moveDirection(0, -1)}
            disabled={isMoving}
            className={`w-16 h-16 flex items-center justify-center rounded ${
              isMoving
                ? "bg-gray-500 cursor-not-allowed"
                : "bg-blue-500 hover:bg-blue-600"
            } text-white text-2xl`}
          >
            ↓
          </button>
        </div>
      </div>

      <LightControls
        intensity={lightIntensity}
        distance={lightDistance}
        decay={lightDecay}
        ambientLightIntensity={ambientLightIntensity}
        onIntensityChange={onLightIntensityChange}
        onDistanceChange={onLightDistanceChange}
        onDecayChange={onLightDecayChange}
        onAmbientLightIntensityChange={onAmbientLightIntensityChange}
      />
    </div>
  );
};

export default GameUI;
