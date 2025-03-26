// Import animation types from CharacterBody
import { CharacterAnimationType } from "./animations";

// Import all face sprites
// Goggles (gogl)
import pigV01 from "/src/assets/spritesheets/animals/pig/livestock_pig_A_v01.png";
import pigV02 from "/src/assets/spritesheets/animals/pig/livestock_pig_A_v02.png";
import pigV03 from "/src/assets/spritesheets/animals/pig/livestock_pig_A_v03.png";
import pigV04 from "/src/assets/spritesheets/animals/pig/livestock_pig_A_v04.png";
import pigV05 from "/src/assets/spritesheets/animals/pig/livestock_pig_B_v01.png";
import pigV06 from "/src/assets/spritesheets/animals/pig/livestock_pig_B_v02.png";
import pigV07 from "/src/assets/spritesheets/animals/pig/livestock_pig_B_v03.png";
import pigV08 from "/src/assets/spritesheets/animals/pig/livestock_pig_B_v04.png";

// Define face styles
export enum AnimalPigType {
  NONE = "none",
}

// Group face sprites by style
export const ANIMALS_PIG = {
  [AnimalPigType.NONE]: [
    pigV01,
    pigV02,
    pigV03,
    pigV04,
    pigV05,
    pigV06,
    pigV07,
    pigV08,
  ],
};

export interface AnimalPigConfType {
  type: AnimalPigType;
  sprite: string;
  spritesheetSize: { columns: number; rows: number };
}

// Function to get a random face or none (with a certain probability)
export const getRandomPig = (): AnimalPigConfType => {
  // Get random style type (excluding NONE)
  const styles = [AnimalPigType.NONE];
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants =
    ANIMALS_PIG[randomStyleType as keyof typeof ANIMALS_PIG];
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
  faceStyle?: AnimalPigType; // Optional specific face style
  zOffset?: number; // Optional Z offset to position the face relative to the character
  chanceOfNoAnimal?: number; // Percentage chance (0-100) that no face accessory will be shown
  onAnimationComplete?: (animation: CharacterAnimationType) => void;
}
