import { CharacterAnimationType } from "./animations";
import { Position } from "./game";

// Import the sprite sheets
import char_demn_v01 from "/src/assets/spritesheets/characters/char_a_p1_0bas_demn_v01.png";
import char_demn_v02 from "/src/assets/spritesheets/characters/char_a_p1_0bas_demn_v02.png";
import char_gbln_v01 from "/src/assets/spritesheets/characters/char_a_p1_0bas_gbln_v01.png";
import char_humn_v00 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v00.png";
import char_humn_v01 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v01.png";
import char_humn_v02 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v02.png";
import char_humn_v03 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v03.png";
import char_humn_v04 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v04.png";
import char_humn_v05 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v05.png";
import char_humn_v06 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v06.png";
import char_humn_v07 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v07.png";
import char_humn_v08 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v08.png";
import char_humn_v09 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v09.png";
import char_humn_v10 from "/src/assets/spritesheets/characters/char_a_p1_0bas_humn_v10.png";
// Define character types
export enum CharacterBodyType {
  HUMAN = "human",
  GOBLIN = "goblin",
  DEMON = "demon",
}

// Group character sprites by type
export const CHARACTERS_BODY = {
  [CharacterBodyType.HUMAN]: [
    char_humn_v00,
    char_humn_v01,
    char_humn_v02,
    char_humn_v03,
    char_humn_v04,
    char_humn_v05,
    char_humn_v06,
    char_humn_v07,
    char_humn_v08,
    char_humn_v09,
    char_humn_v10,
  ],
  [CharacterBodyType.GOBLIN]: [char_gbln_v01],
  [CharacterBodyType.DEMON]: [char_demn_v01, char_demn_v02],
} as const;

// Function to get a random character sprite

export interface CharacterBodyConfType {
  type: CharacterBodyType;
  sprite: string;
  spritesheetSize: { columns: number; rows: number };
}

export const getRandomCharacterBody = (): CharacterBodyConfType => {
  // Get random character type
  const types = Object.values(CharacterBodyType);
  const randomType = types[Math.floor(Math.random() * types.length)];

  // Get random variant from that type
  const variants = CHARACTERS_BODY[randomType];
  const randomVariant = variants[Math.floor(Math.random() * variants.length)];

  return {
    type: randomType,
    sprite: randomVariant,
    spritesheetSize: { columns: 8, rows: 8 },
  };
};

export interface MovementState {
  path: Position[];
  currentPathIndex: number;
  isMoving: boolean;
}

export interface CharacterBodyProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: CharacterAnimationType;
  frame?: number; // Optional specific frame to display
  characterType?: CharacterBodyType; // Optional specific character type
  onAnimationComplete?: (animation: CharacterAnimationType) => void; // Callback when animation completes
  speed?: number;
  gridSize?: number;
  onMoveComplete?: () => void;
  setPosition?: (position: [number, number, number]) => void;
  setAnimation?: (animation: CharacterAnimationType) => void;
  zOffset?: number;
} 