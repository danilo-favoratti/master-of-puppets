import React, {useEffect, useState} from "react";
import {Entity} from "../../types/entity";
import {Position} from "../../types/game";
import {AnimatedSprite} from "../AnimatedSprite";

interface CampfireSpitSpriteProps {
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

export const CampfireSpitSprite: React.FC<CampfireSpitSpriteProps> = ({
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
      imageUrl="/src/assets/travelers_camp.png"
      spritesheetSize={{ columns: 5, rows: 3 }}
      animationConfig={{
        idle: {
          frame: { x: 3, y: 2 },
          frameDuration: 200,
        },
      }}
      state={currentState}
      size={1}
    />
  );
};

export default CampfireSpitSprite;
