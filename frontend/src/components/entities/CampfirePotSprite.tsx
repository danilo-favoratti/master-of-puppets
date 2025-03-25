import React, {useEffect, useState} from "react";
import {Entity} from "../../types/entity";
import {Position} from "../../types/game";
import {AnimatedSprite} from "../AnimatedSprite";

interface CampfirePotSpriteProps {
  position: Position;
  state?: "empty" | "cooking" | "cooked";
  entity: Entity;
  onStateChange?: (newState: "empty" | "cooking" | "cooked") => void;
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

export const CampfirePotSprite: React.FC<CampfirePotSpriteProps> = ({
  position,
  state = "empty",
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
      id="campfire-pot-1"
      type="environment"
      name="Camp Fire Pot"
      position={position}
      imageUrl="/src/assets/travelers_camp.png"
      spritesheetSize={{ columns: 5, rows: 3 }}
      animationConfig={{
        empty: {
          frame: { x: 0, y: 2 },
          frameDuration: 200,
        },
        idle: {
          frame: { x: 0, y: 2 },
          frameDuration: 200,
        },
      }}
      state={"idle"}
      size={1}
    />
  );
};

export default CampfirePotSprite;
