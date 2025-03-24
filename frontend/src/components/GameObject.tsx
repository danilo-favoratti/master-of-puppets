import React from "react";
import { GameObjectConfig, GameObject as GameObjectType } from "../types/game";
import { AnimatedSprite } from "./AnimatedSprite";

interface GameObjectProps {
  config: GameObjectConfig;
  position: { x: number; y: number };
  state: GameObjectType["state"];
  variant: GameObjectType["variant"];
  entity: GameObjectType["entity"];
  onClick?: (event: React.MouseEvent) => void;
  onStateChange?: (newState: GameObjectType["state"]) => void;
}

const GameObject: React.FC<GameObjectProps> = ({
  config,
  position,
  state,
  entity,
  onClick,
  onStateChange,
}) => {
  return (
    <AnimatedSprite
      id={config.id}
      type="environment"
      name={config.name}
      position={position}
      imageUrl={config.imageUrl}
      spritesheetSize={config.spritesheetSize}
      animationConfig={config.animationConfig}
      state={state}
      size={config.size || 1}
      onClick={onClick}
    />
  );
};

export default GameObject;
