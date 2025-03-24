import { AnimationType } from "./animations";
import { CharacterType } from "./characters";

export interface Point {
  x: number;
  y: number;
}

export interface MovementState {
  path: Point[];
  currentPathIndex: number;
  isMoving: boolean;
}

export interface CharacterSpriteProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: AnimationType;
  frame?: number; // Optional specific frame to display
  characterType?: CharacterType; // Optional specific character type
  onAnimationComplete?: (animation: AnimationType) => void; // Callback when animation completes
  speed?: number;
  gridSize?: number;
  onMoveComplete?: () => void;
  setPosition?: (position: [number, number, number]) => void;
  setAnimation?: (animation: AnimationType) => void;
  zOffset?: number;
} 