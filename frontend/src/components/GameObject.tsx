import React from "react";
import {GameObject as GameObjectType, GameObjectConfig} from "../types/game";
import { positionToXY, xyToPosition } from "../utils/positionUtils";
import {AnimatedSprite} from "./AnimatedSprite";

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
  // Convert position from {x,y} object to Position tuple
  const positionTuple = xyToPosition(position);
  
  return (
    <AnimatedSprite
      id={config.id}
      type={config.type}
      name={config.name}
      position={positionTuple}
      imageUrl={config.imageUrl}
      spritesheetSize={config.spritesheetSize}
      animationConfig={config.animationConfig}
      state={state}
      size={config.size || 1}
      onClick={onClick as any}
    />
  );
};

export default GameObject;
