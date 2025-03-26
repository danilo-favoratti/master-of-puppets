// ChatBubble.tsx

import React from "react";
import { useGameStore } from "../store/gameStore";
import { GameEntity } from "../types/entities";

interface ChatBubbleProps {
  entity?: GameEntity;
}

export const ChatBubble = ({ entity }: ChatBubbleProps) => {
  const { gameData } = useGameStore();

  return (
    <mesh position={[0, 0, 0.4]}>
      <planeGeometry args={[1, 1]} />
      <meshStandardMaterial color="red" transparent={true} />
    </mesh>
  );
};
