import React, { useEffect, useState } from "react";
import { Entity } from "../../types/entity";
import { Position } from "../../types/game";
import { AnimatedSprite } from "../AnimatedSprite";

interface TombStoneSpriteProps {
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

export const TombStoneSprite: React.FC<TombStoneSpriteProps> = ({
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

  const variantNum = parseInt(variant, 3) - 1;

  return (
    <AnimatedSprite
      id={`pot-${variant}`}
      type="environment"
      name="Pot"
      position={position}
      imageUrl="/src/assets/spritesheets/tombstone.png"
      spritesheetSize={{ columns: 3, rows: 1 }}
      animationConfig={{
        idle: {
          frame: { x: variant - 1, y: 0 },
          frameDuration: 200,
        },
      }}
      state={currentState as "idle"}
      size={1}
    />
  );
};

export default TombStoneSprite;
