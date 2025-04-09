import {useFrame} from "@react-three/fiber";
import React, {useEffect, useRef, useState} from "react";
import {Entity} from "../../types/entity";
import {Position} from "../../types/game";
import {AnimatedSprite} from "../AnimatedSprite";

interface CampFireSpriteProps {
  position: Position;
  state?: "unlit" | "burning" | "dying" | "extinguished";
  entity: Entity;
  onStateChange?: (
    newState: "unlit" | "burning" | "dying" | "extinguished"
  ) => void;
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

export const CampFireSprite: React.FC<CampFireSpriteProps> = ({
  position,
  state = "unlit",
  entity = defaultEntity,
  onStateChange,
  onClick,
}) => {
  const [currentState, setCurrentState] = useState(state);
  const [lightIntensity, setLightIntensity] = useState(0);
  const lightFlickerRef = useRef(1);

  useEffect(() => {
    setCurrentState(state);
  }, [state]);

  // Add flickering effect to the light without causing re-renders
  useFrame(() => {
    if (currentState === "burning") {
      // Random flickering effect for the campfire
      lightFlickerRef.current = Math.random() * 0.3 + 0.7; // Values between 0.7 and 1.0
    }
  });

  // Update light intensity based on state
  useEffect(() => {
    if (currentState === "burning") {
      setLightIntensity(1.5);
    } else if (currentState === "dying") {
      setLightIntensity(0.5);
    } else {
      setLightIntensity(0);
    }
  }, [currentState]);

  const changeState = (
    newState: "unlit" | "burning" | "dying" | "extinguished"
  ) => {
    setCurrentState(newState);
    if (onStateChange) {
      onStateChange(newState);
    }
  };

  //change state
  const handleClick = () => {
    // go through the states in order
    switch (currentState) {
      case "unlit":
        changeState("burning");
        break;
      case "burning":
        changeState("dying");
        break;
      case "dying":
        changeState("extinguished");
        break;
      case "extinguished":
        changeState("unlit");
        break;
      default:
        changeState("unlit");
        break;
    }
  };

  return (
    <>
      <pointLight
        position={[position[0], position[1], 0.5]}
        intensity={lightIntensity * lightFlickerRef.current}
        distance={8}
        decay={1}
        color="#ff7300"
      />
      <AnimatedSprite
        id="campfire-1"
        type="environment"
        name="Camp Fire"
        position={position}
        tileSize={{ width: 64, height: 64 }}
        imageUrl="/src/assets/travelers_camp.png"
        spritesheetSize={{ columns: 5, rows: 3 }}
        animationConfig={{
          unlit: {
            frame: { x: 0, y: 0 },
            frameDuration: 200,
          },
          burning: {
            frames: [
              { x: 1, y: 0 },
              { x: 2, y: 0 },
              { x: 3, y: 0 },
              { x: 4, y: 0 },
            ],
            frameDuration: 200,
          },
          dying: {
            frames: [
              { x: 1, y: 1 },
              { x: 2, y: 1 },
              { x: 3, y: 1 },
              { x: 4, y: 1 },
            ],
            frameDuration: 200,
          },
          extinguished: {
            frames: [{ x: 0, y: 1 }],
            frameDuration: 150,
          },
        }}
        state={currentState}
        size={1}
        onClick={handleClick}
        onAnimationComplete={(currentState) => {
          if (currentState === "dying") {
            setCurrentState("extinguished");
          }
        }}
      />
    </>
  );
};

export default CampFireSprite;
