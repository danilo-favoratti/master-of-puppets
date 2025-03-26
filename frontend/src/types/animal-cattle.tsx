// Import animation types from CharacterBody
import { CharacterAnimationType } from "./animations";

// Import all face sprites
// Goggles (gogl)
import pigV01 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_A_v01.png";
import pigV02 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_A_v02.png";
import pigV03 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_A_v03.png";
import pigV04 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_A_v04.png";
import pigV05 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_A_v05.png";
import pigV06 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_A_v06.png";
import pigV07 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_B_v01.png";
import pigV08 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_B_v02.png";
import pigV09 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_B_v03.png";
import pigV10 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_B_v04.png";
import pigV11 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_B_v05.png";
import pigV12 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-bull_B_v06.png";
import pigV13 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_A_v01.png";
import pigV14 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_A_v02.png";
import pigV15 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_A_v03.png";
import pigV16 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_A_v04.png";
import pigV17 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_A_v05.png";
import pigV18 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_A_v06.png";
import pigV19 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_B_v01.png";
import pigV20 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_B_v02.png";
import pigV21 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_B_v03.png";
import pigV22 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_B_v04.png";
import pigV23 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_B_v05.png";
import pigV24 from "/src/assets/spritesheets/animals/cattle/livestock_cattle-cow_B_v06.png";

// Define face styles
export enum AnimalCattleType {
  NONE = "none",
}

// Group face sprites by style
export const ANIMALS_CATTLE = {
  [AnimalCattleType.NONE]: [
    pigV01,
    pigV02,
    pigV03,
    pigV04,
    pigV05,
    pigV06,
    pigV07,
    pigV08,
    pigV09,
    pigV10,
    pigV11,
    pigV12,
    pigV13,
    pigV14,
    pigV15,
    pigV16,
    pigV17,
    pigV18,
    pigV19,
    pigV20,
    pigV21,
    pigV22,
    pigV23,
    pigV24,
  ],
};

export interface AnimalCattleConfType {
  type: AnimalCattleType;
  sprite: string;
  spritesheetSize: { columns: number; rows: number };
}

// Function to get a random face or none (with a certain probability)
export const getRandomCattle = (): AnimalCattleConfType => {
  // Get random style type (excluding NONE)
  const styles = [AnimalCattleType.NONE];
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants =
    ANIMALS_CATTLE[randomStyleType as keyof typeof ANIMALS_CATTLE];
  const randomVariant =
    styleVariants[Math.floor(Math.random() * styleVariants.length)];

  return {
    type: randomStyleType,
    sprite: randomVariant,
    spritesheetSize: { columns: 8, rows: 8 },
  };
};

export interface CharacterAnimalProps {
  position?: [number, number, number];
  scale?: [number, number, number];
  rows?: number;
  cols?: number;
  animation?: CharacterAnimationType;
  frame?: number;
  faceStyle?: AnimalCattleType; // Optional specific face style
  zOffset?: number; // Optional Z offset to position the face relative to the character
  chanceOfNoAnimal?: number; // Percentage chance (0-100) that no face accessory will be shown
  onAnimationComplete?: (animation: CharacterAnimationType) => void;
}
