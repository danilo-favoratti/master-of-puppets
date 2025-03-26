import React, { useEffect, useState } from "react";
import { Entity } from "../../types/entity";
import { Position } from "../../types/game";
import { AnimatedSprite } from "../AnimatedSprite";

interface StoneSpriteProps {
  position: Position;
  state?: "idle";
  variant?: string;
  entity: Entity;
  onStateChange?: (newState: "idle") => void;
  onClick?: (event: React.MouseEvent) => void;
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

export const StoneSprite: React.FC<StoneSpriteProps> = ({
  position,
  state = "idle",
  variant = "1",
  entity = defaultEntity,
  onStateChange,
  onClick,
}) => {
  const [currentState, setCurrentState] = useState(state);

  useEffect(() => {
    if (state === "idle") {
      setCurrentState("idle");
    } else {
      setCurrentState(state);
    }
  }, [state]);

  const variantNum = parseInt(variant, 6) - 1;

  return (
    <AnimatedSprite
      id={`pot-${variant}`}
      type="environment"
      name="Pot"
      position={position}
      imageUrl="/src/assets/spritesheets/stones.png"
      spritesheetSize={{ columns: 5, rows: 1 }}
      animationConfig={{
        idle: {
          frame: { x: variantNum, y: 0 },
          frameDuration: 200,
        },
      }}
      state={currentState as "idle"}
      size={1}
    />
  );
};

export default StoneSprite;
