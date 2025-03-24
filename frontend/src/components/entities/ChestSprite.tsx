import React, { useEffect, useState } from "react";
import { Entity } from "../../types/entity";
import { Position } from "../../types/game";
import { AnimatedSprite } from "../AnimatedSprite";

interface ChestSpriteProps {
  position: Position;
  state?: "closed" | "open";
  variant?: "wooden" | "silver" | "golden" | "magical";
  entity: Entity;
  onStateChange?: (newState: "closed" | "open") => void;
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

export const ChestSprite: React.FC<ChestSpriteProps> = ({
  position,
  state = "closed",
  variant = "wooden",
  entity = defaultEntity,
  onStateChange,
  onClick,
}) => {
  const [currentState, setCurrentState] = useState(state);
  const [randomRow] = useState(() => Math.floor(Math.random() * 3) * 2);

  useEffect(() => {
    setCurrentState(state);
  }, [state]);

  const changeState = (newState: "open" | "closed") => {
    setCurrentState(newState);
    if (onStateChange) {
      onStateChange(newState);
    }
  };

  //change state
  const handleClick = () => {
    // go through the states in order
    switch (currentState) {
      case "closed":
        changeState("open");
        break;
      default:
        changeState("closed");
        break;
    }
  };

  // Calculate sprite positions based on variant
  const getVariantColumn = (variant: string): number => {
    switch (variant) {
      case "wooden":
        return 0;
      case "silver":
        return 1;
      case "golden":
        return 2;
      case "magical":
        return 3;
      default:
        return 0;
    }
  };

  const column = getVariantColumn(variant);

  return (
    <AnimatedSprite
      id={`chest-${variant}`}
      type="environment"
      name="Chest"
      position={position}
      imageUrl="/src/assets/spritesheets/chests/treasure_chests.png"
      spritesheetSize={{ columns: 5, rows: 6 }}
      animationConfig={{
        idle: {
          frame: { x: column, y: randomRow },
          frameDuration: 200,
        },
        open: {
          frames: [{ x: column, y: randomRow + 1 }],
          frameDuration: 100,
        },
        closed: {
          frames: [{ x: column, y: randomRow }],
          frameDuration: 200,
        },
      }}
      state={currentState as "open" | "closed"}
      size={1}
      onClick={handleClick}
    />
  );
};

export default ChestSprite;
