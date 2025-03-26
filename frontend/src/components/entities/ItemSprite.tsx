import React, { useEffect, useState } from "react";
import { Entity } from "../../types/entity";
import { Position } from "../../types/game";
import { AnimatedSprite } from "../AnimatedSprite";

interface ItemSpriteProps {
  position: Position;
  state?: "idle";
  variant?: string;
  entity: Entity;
  onStateChange?: (newState: "idle") => void;
  onClick?: (event: React.MouseEvent) => void;
}

const itensTable = {
  key: {
    frames: [
      { x: 3, y: 10 },
      { x: 4, y: 10 },
      { x: 5, y: 10 },
      { x: 6, y: 10 },
      { x: 7, y: 10 },
      { x: 8, y: 10 },
      { x: 9, y: 10 },
      { x: 10, y: 10 },
      { x: 11, y: 10 },
      { x: 12, y: 10 },
    ],
  },
  small_potion: {
    frames: [
      { x: 1, y: 12 },
      { x: 2, y: 12 },
      { x: 3, y: 12 },
      { x: 4, y: 12 },
      { x: 5, y: 12 },
      { x: 6, y: 12 },
      { x: 7, y: 12 },
      { x: 8, y: 12 },
    ],
  },
  big_potion: {
    frames: [
      { x: 1, y: 13 },
      { x: 2, y: 13 },
      { x: 3, y: 13 },
      { x: 4, y: 13 },
      { x: 5, y: 13 },
      { x: 6, y: 13 },
      { x: 7, y: 13 },
      { x: 8, y: 13 },
    ],
  },
  book: {
    frames: [
      { x: 15, y: 0 },
      { x: 0, y: 1 },
      { x: 1, y: 1 },
      { x: 2, y: 1 },
      { x: 3, y: 1 },
      { x: 4, y: 1 },
      { x: 5, y: 1 },
      { x: 6, y: 1 },
      { x: 7, y: 1 },
      { x: 8, y: 1 },
      { x: 9, y: 1 },
      { x: 10, y: 1 },
      { x: 11, y: 1 },
      { x: 12, y: 1 },
      { x: 13, y: 1 },
      { x: 14, y: 1 },
      { x: 15, y: 1 },
      { x: 0, y: 2 },
      { x: 1, y: 2 },
      { x: 2, y: 2 },
      { x: 3, y: 2 },
      { x: 4, y: 2 },
      { x: 5, y: 2 },
      { x: 6, y: 2 },
      { x: 7, y: 2 },
      { x: 8, y: 2 },
      { x: 9, y: 2 },
      { x: 10, y: 2 },
      { x: 11, y: 2 },
      { x: 12, y: 2 },
      { x: 13, y: 2 },
      { x: 14, y: 2 },
      { x: 15, y: 2 },
      { x: 0, y: 3 },
      { x: 1, y: 3 },
      { x: 2, y: 3 },
      { x: 3, y: 3 },
      { x: 4, y: 3 },
      { x: 5, y: 3 },
      { x: 6, y: 3 },
      { x: 7, y: 3 },
    ],
  },
  sword: {
    frames: [
      { x: 13, y: 17 },
      { x: 14, y: 17 },
      { x: 15, y: 17 },
      { x: 0, y: 18 },
      { x: 1, y: 18 },
      { x: 2, y: 18 },
      { x: 3, y: 18 },
      { x: 4, y: 18 },
      { x: 5, y: 18 },
      { x: 6, y: 18 },
      { x: 7, y: 18 },
      { x: 8, y: 18 },
      { x: 9, y: 18 },
      { x: 10, y: 18 },
      { x: 11, y: 18 },
    ],
  },
  spell_book: {
    frames: [
      { x: 8, y: 14 },
      { x: 9, y: 14 },
      { x: 10, y: 14 },
      { x: 11, y: 14 },
      { x: 12, y: 14 },
      { x: 13, y: 14 },
      { x: 14, y: 14 },
      { x: 15, y: 14 },
    ],
  },
  diamond: {
    frames: [
      { x: 0, y: 7 },
      { x: 1, y: 7 },
      { x: 2, y: 7 },
      { x: 3, y: 7 },
      { x: 4, y: 7 },
      { x: 5, y: 7 },
      { x: 6, y: 7 },
      { x: 7, y: 7 },
      { x: 8, y: 7 },
    ],
  },
};
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

export const ItemSprite: React.FC<ItemSpriteProps> = ({
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

  const randomFrame = Math.floor(
    Math.random() * itensTable[variant].frames.length
  );

  return (
    <AnimatedSprite
      id={`pot-${variant}`}
      type="environment"
      name="Pot"
      position={position}
      imageUrl="/src/assets/spritesheets/items-32x32.png"
      spritesheetSize={{ columns: 16, rows: 19 }}
      animationConfig={{
        idle: {
          frame: itensTable[variant].frames[randomFrame],
          frameDuration: 200,
        },
      }}
      state={currentState as "idle"}
      size={0.5}
    />
  );
};

export default ItemSprite;
