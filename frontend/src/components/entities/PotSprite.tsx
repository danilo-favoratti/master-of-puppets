import React, {useEffect, useState} from "react";
import {Entity} from "../../types/entity";
import {Position} from "../../types/game";
import {AnimatedSprite} from "../AnimatedSprite";

interface PotSpriteProps {
  position: Position;
  state?: "idle" | "breaking" | "broken";
  variant?: string;
  entity: Entity;
  onStateChange?: (newState: "idle" | "breaking" | "broken") => void;
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

export const PotSprite: React.FC<PotSpriteProps> = ({
  position,
  state = "idle",
  variant = "1",
  entity = defaultEntity,
  onStateChange,
  onClick,
}) => {
  const [currentState, setCurrentState] = useState(state);

  useEffect(() => {
    if (state === "default") {
      setCurrentState("idle");
    } else {
      setCurrentState(state);
    }
  }, [state]);

  const changeState = (newState: "idle" | "breaking" | "broken") => {
    setCurrentState(newState);
    if (onStateChange) {
      onStateChange(newState);
    }
  };

  //change state
  const handleClick = () => {
    // go through the states in order
    switch (currentState) {
      case "idle":
        changeState("breaking");
        break;
      case "breaking":
        changeState("broken");
        break;
      default:
        changeState("idle");
        break;
    }
  };

  const variantNum = parseInt(variant, 10) - 1;

  return (
    <AnimatedSprite
      id={`pot-${variant}`}
      type="environment"
      name="Pot"
      position={position}
      imageUrl="/src/assets/spritesheets/pots/breakable_pots_gray.png"
      spritesheetSize={{ columns: 5, rows: 4 }}
      animationConfig={{
        idle: {
          frame: { x: 0, y: variantNum },
          frameDuration: 200,
        },
        breaking: {
          frames: [
            { x: 1, y: variantNum },
            { x: 2, y: variantNum },
            { x: 3, y: variantNum },
          ],
          frameDuration: 100,
        },
        broken: {
          frames: [{ x: 4, y: variantNum }],
          frameDuration: 200,
        },
      }}
      state={currentState as "idle" | "breaking" | "broken"}
      size={1}
      onClick={handleClick}
      onAnimationComplete={(currentState) => {
        if (currentState === "breaking") {
          setCurrentState("broken");
        }
      }}
    />
  );
};

export default PotSprite;
