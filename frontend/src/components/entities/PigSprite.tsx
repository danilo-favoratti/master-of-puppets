import { ThreeEvent, useFrame } from "@react-three/fiber";
import React, { useEffect, useRef, useState } from "react";
import { Entity } from "../../types/entity";
import { Position } from "../../types/game";
import { AnimatedSprite } from "../AnimatedSprite";

interface PigSpriteProps {
  position: Position;
  state?:
    | "idleUp"
    | "idleDown"
    | "idleLeft"
    | "idleRight"
    | "walkLeft"
    | "walkRight"
    | "walkUp"
    | "walkDown";
  entity: Entity;
  onStateChange?: (
    newState:
      | "idleUp"
      | "idleDown"
      | "idleLeft"
      | "idleRight"
      | "walkLeft"
      | "walkRight"
      | "walkUp"
      | "walkDown"
  ) => void;
  onClick?: (event: ThreeEvent<MouseEvent>) => void;
  canMove?: boolean;
  moveInterval?: number;
}

export const PigSprite = (props: PigSpriteProps) => {
  const [currentPosition, setCurrentPosition] = useState<Position>(
    props.position
  );
  const [currentState, setCurrentState] = useState<
    | "idleUp"
    | "idleDown"
    | "idleLeft"
    | "idleRight"
    | "walkLeft"
    | "walkRight"
    | "walkUp"
    | "walkDown"
  >("idleDown");
  const [isMoving, setIsMoving] = useState(false);

  // Movement interpolation ref
  const movementRef = useRef<null | {
    start: Position;
    end: Position;
    duration: number;
    elapsedTime: number;
    direction: "up" | "down" | "left" | "right";
  }>(null);

  const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

  // Smoothly update position based on movementRef using useFrame
  useFrame((_, delta) => {
    if (movementRef.current) {
      movementRef.current.elapsedTime += delta;
      let t = movementRef.current.elapsedTime / movementRef.current.duration;
      if (t > 1) t = 1;

      // Calculate current position
      const newPosition = {
        x: lerp(movementRef.current.start.x, movementRef.current.end.x, t),
        y: lerp(movementRef.current.start.y, movementRef.current.end.y, t),
      };

      // Update position
      setCurrentPosition(newPosition);

      // Update animation based on movement direction

      //

      if (isMoving && !movementRef.current.elapsedTime) {
        const direction = movementRef.current.direction;
        setCurrentState(
          `walk${direction.charAt(0).toUpperCase() + direction.slice(1)}` as any
        );
      }

      if (t === 1) {
        // When movement is complete, set idle animation
        const direction = movementRef.current.direction;
        setCurrentState(
          `idle${direction.charAt(0).toUpperCase() + direction.slice(1)}` as any
        );
        setIsMoving(false);
        movementRef.current = null;
      }
    }
  });

  useEffect(() => {
    if (!props.canMove) return;

    const movePig = () => {
      if (isMoving) return;

      const directions = [
        { dx: 0, dy: 1, state: "walkUp", direction: "up" },
        { dx: 0, dy: -1, state: "walkDown", direction: "down" },
        { dx: 1, dy: 0, state: "walkRight", direction: "right" },
        { dx: -1, dy: 0, state: "walkLeft", direction: "left" },
      ];

      const randomDirection =
        directions[Math.floor(Math.random() * directions.length)];

      // Set animation state immediately when movement starts
      setCurrentState(
        `walk${
          randomDirection.direction.charAt(0).toUpperCase() +
          randomDirection.direction.slice(1)
        }` as any
      );

      setIsMoving(true);

      // Set up movement interpolation
      movementRef.current = {
        start: currentPosition,
        end: {
          x: currentPosition.x + randomDirection.dx,
          y: currentPosition.y + randomDirection.dy,
        },
        duration: 1, // 1 second movement duration
        elapsedTime: 0,
        direction: randomDirection.direction as
          | "up"
          | "down"
          | "left"
          | "right",
      };
    };

    const interval = setInterval(movePig, props.moveInterval);

    return () => clearInterval(interval);
  }, [props.canMove, props.moveInterval, isMoving, currentPosition]);

  return (
    <AnimatedSprite
      id="pig-1"
      type="mob"
      name="Pig"
      position={currentPosition}
      imageUrl="/src/assets/spritesheets/animals/livestock_pig_A_v01.png"
      spritesheetSize={{ columns: 8, rows: 8 }}
      state={currentState}
      size={2}
      zOffset={0.04}
      animationConfig={{
        idleUp: {
          frames: [
            { x: 0, y: 1 },
            { x: 1, y: 1 },
          ],
          frameDuration: 1600,
        },
        idleDown: {
          frames: [
            { x: 0, y: 0 },
            { x: 1, y: 0 },
          ],
          frameDuration: 1600,
        },
        idleLeft: {
          frames: [
            { x: 0, y: 3 },
            { x: 1, y: 3 },
          ],
          frameDuration: 1600,
        },
        idleRight: {
          frames: [
            { x: 0, y: 2 },
            { x: 1, y: 2 },
          ],
          frameDuration: 1600,
        },
        walkLeft: {
          frames: [
            { x: 2, y: 3 },
            { x: 3, y: 3 },
            { x: 4, y: 3 },
            { x: 5, y: 3 },
          ],
          frameDuration: 200,
        },
        walkRight: {
          frames: [
            { x: 2, y: 2 },
            { x: 3, y: 2 },
            { x: 4, y: 2 },
            { x: 5, y: 2 },
          ],
          frameDuration: 200,
        },
        walkUp: {
          frames: [
            { x: 2, y: 1 },
            { x: 3, y: 1 },
            { x: 4, y: 1 },
            { x: 5, y: 1 },
          ],
          frameDuration: 200,
        },
        walkDown: {
          frames: [
            { x: 2, y: 0 },
            { x: 3, y: 0 },
            { x: 4, y: 0 },
            { x: 5, y: 0 },
          ],
          frameDuration: 200,
        },
      }}
      onClick={props.onClick}
    />
  );
};

export default PigSprite;
