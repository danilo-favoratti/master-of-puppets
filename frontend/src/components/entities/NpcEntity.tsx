// NpcEntity.tsx

import {Text} from "@react-three/drei";
import {ThreeEvent, useFrame} from "@react-three/fiber";
import React, {useEffect, useRef, useState} from "react";
import {useGameStore} from "../../store/gameStore";
import {CharacterAnimationType} from "../../types/animations";
import {CharacterBodyConfType, getRandomCharacterBody,} from "../../types/characters-body";
import {Entity, Position} from "../../types/game";
import CharacterBody from "../character/CharacterBody";

interface NpcEntityProps {
  id: string;
  entity?: Entity;
  position: Position;
  onClick?: (event: ThreeEvent<MouseEvent>) => void;
  state?: string;
  scale?: number;
  type?: string;
  name?: string;
  body?: CharacterBodyConfType;
  canMove?: boolean;
  moveInterval?: number;
}

const animationConfig = {
  idleUp: {
    frames: [{ x: 0, y: 1 }],
    frameDuration: 1600,
  },
  idleDown: {
    frames: [{ x: 0, y: 0 }],
    frameDuration: 1600,
  },
  idleLeft: {
    frames: [{ x: 0, y: 3 }],
    frameDuration: 1600,
  },
  idleRight: {
    frames: [{ x: 0, y: 2 }],
    frameDuration: 1600,
  },
  walkLeft: {
    frames: [
      { x: 0, y: 7 },
      { x: 1, y: 7 },
      { x: 2, y: 7 },
      { x: 3, y: 7 },
      { x: 4, y: 7 },
      { x: 5, y: 7 },
    ],
    frameDuration: 200,
  },
  walkRight: {
    frames: [
      { x: 0, y: 6 },
      { x: 1, y: 6 },
      { x: 2, y: 6 },
      { x: 3, y: 6 },
      { x: 4, y: 6 },
      { x: 5, y: 6 },
    ],
    frameDuration: 200,
  },
  walkUp: {
    frames: [
      { x: 0, y: 5 },
      { x: 1, y: 5 },
      { x: 2, y: 5 },
      { x: 3, y: 5 },
      { x: 4, y: 5 },
      { x: 5, y: 5 },
    ],
    frameDuration: 200,
  },
  walkDown: {
    frames: [
      { x: 0, y: 4 },
      { x: 1, y: 4 },
      { x: 2, y: 4 },
      { x: 3, y: 4 },
      { x: 4, y: 4 },
      { x: 5, y: 4 },
    ],
    frameDuration: 200,
  },
};

export const NpcEntity = ({
  id,
  type = "npc",
  name = "NPC",
  entity,
  position,
  onClick,
  state,
  scale,
  body = getRandomCharacterBody(),
  canMove = true,
  moveInterval = 1000,
}: NpcEntityProps) => {
  const initialPosition = useRef(position);
  const imageUrl = body.sprite;
  const [currentPosition, setCurrentPosition] = useState<Position>(position);

  const { gameData } = useGameStore();

  if (!gameData || !gameData.map.grid) return null;

  const entities = gameData.entities;

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
      const currentPosition = movementRef.current.start;
      movementRef.current.elapsedTime += delta;

      const currentPositionFloor = {
        x: Math.floor(currentPosition.x),
        y: Math.floor(currentPosition.y),
      };
      let t = movementRef.current.elapsedTime / movementRef.current.duration;
      if (t > 1) t = 1;

      // Calculate current position
      const newPosition = {
        x: lerp(movementRef.current.start.x, movementRef.current.end.x, t),
        y: lerp(movementRef.current.start.y, movementRef.current.end.y, t),
      };

      setCurrentPosition(newPosition);

      if (isMoving && !movementRef.current.elapsedTime) {
        const direction = movementRef.current.direction;
        setCurrentState(
          `walk${direction.charAt(0).toUpperCase() + direction.slice(1)}` as any
        );
      }

      if (t === 1) {
        stopMovement(movementRef.current.direction);
      }
    }
  });

  const stopMovement = (direction: "up" | "down" | "left" | "right") => {
    setCurrentState(
      `idle${direction.charAt(0).toUpperCase() + direction.slice(1)}` as any
    );
    setCurrentPosition(currentPosition);
    setIsMoving(false);
    movementRef.current = null;
  };

  useEffect(() => {
    if (!canMove) return;

    const moveNPC = () => {
      if (isMoving) return;

      const directions = [
        { dx: 0, dy: 1, state: "walkUp", direction: "up" },
        { dx: 0, dy: -1, state: "walkDown", direction: "down" },
        { dx: 1, dy: 0, state: "walkRight", direction: "right" },
        { dx: -1, dy: 0, state: "walkLeft", direction: "left" },
      ];

      const randomDirection =
        directions[Math.floor(Math.random() * directions.length)];

      const newPos = {
        x: currentPosition.x + randomDirection.dx,
        y: currentPosition.y + randomDirection.dy,
      };

      const entity = entities.find(
        (e) =>
          e.position?.x === Math.floor(newPos.x) &&
          e.position?.y === Math.floor(newPos.y)
      );
      if (entity && entity.type !== "npc") {
        console.log("entity", entity.type);
        return;
      }

      // Checa se a nova posição está no limite de 5 tiles
      const dx = Math.abs(newPos.x - initialPosition.current.x);
      const dy = Math.abs(newPos.y - initialPosition.current.y);
      if (dx > 5 || dy > 5) return;

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

    const interval = setInterval(moveNPC, moveInterval + Math.random() * 1000);

    return () => clearInterval(interval);
  }, [canMove, moveInterval, isMoving, currentPosition]);

  return (
    <>
      <CharacterBody
        animation={currentState as CharacterAnimationType}
        position={[
          currentPosition.x,
          currentPosition.y,
          currentPosition.z || 0.02,
        ]}
        scale={[2, 2, 2]}
      />
      <Text
        position={[
          currentPosition.x,
          currentPosition.y - 0.6,
          currentPosition.z || 0.02,
        ]}
        fontSize={0.15}
        color="white"
        anchorX="center"
        anchorY="middle"
      >
        <meshStandardMaterial attach="material" color="white" />
        {name}
      </Text>
    </>
  );
};
