import React, { useEffect, useState } from "react";
import { Entity } from "../../types/entity";
import { Position } from "../../types/game";
import { AnimatedSprite } from "../AnimatedSprite";

interface LogStoolSpriteProps {
  position: Position;
  state?: "idle";
  entity: Entity;
  onStateChange?: (newState: "idle") => void;
  onClick?: (event: React.MouseEvent) => void;
  variant?: string;
}

const defaultEntity: Entity = {
  is_movable: false,
  is_jumpable: false,
  is_usable_alone: false,
  is_collectable: false,
  is_wearable: false,
  weight: 1,
  usable_with: [],
  possible_alone_actions: [],
};

export const LogStoolSprite: React.FC<LogStoolSpriteProps> = ({
  position,
  state = "idle",
  entity = defaultEntity,
  onStateChange,
  onClick,
  variant = "1",
}) => {
  const [currentState, setCurrentState] = useState(state);

  useEffect(() => {
    setCurrentState(state);
  }, [state]);

  return (
    <AnimatedSprite
      id="campfire-1"
      type="environment"
      name="Camp Fire"
      position={position}
      imageUrl="/src/assets/log_stool.png"
      animationConfig={{
        idle: {
          frame: { x: 0, y: 0 },
          frameDuration: 200,
        },
      }}
      state={currentState}
      size={0.6}
    />
  );
};

export default LogStoolSprite;
