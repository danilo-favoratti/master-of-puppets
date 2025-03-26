// Import animation types from CharacterBody
import { CharacterAnimationType } from "./animations";

// Import all face sprites
// Goggles (gogl)
import V01 from "/src/assets/spritesheets/animals/duck/livestock_duck_v01.png";
import V02 from "/src/assets/spritesheets/animals/duck/livestock_duck_v02.png";
import V03 from "/src/assets/spritesheets/animals/duck/livestock_duck_v03.png";
import V04 from "/src/assets/spritesheets/animals/duck/livestock_duck_v04.png";
import V05 from "/src/assets/spritesheets/animals/duck/livestock_duck_v05.png";
import V06 from "/src/assets/spritesheets/animals/duck/livestock_duck_v06.png";
import V07 from "/src/assets/spritesheets/animals/duck/livestock_duck_v07.png";
import V08 from "/src/assets/spritesheets/animals/duck/livestock_duck_v08.png";

// Define face styles
export enum AnimalDuckType {
  NONE = "none",
}

// Group face sprites by style
export const ANIMALS_DUCK = {
  [AnimalDuckType.NONE]: [V01, V02, V03, V04, V05, V06, V07, V08],
};

export interface AnimalDuckConfType {
  type: AnimalDuckType;
  sprite: string;
  spritesheetSize: { columns: number; rows: number };
}

// Function to get a random face or none (with a certain probability)
export const getRandomDuck = (): AnimalDuckConfType => {
  // Get random style type (excluding NONE)
  const styles = [AnimalDuckType.NONE];
  const randomStyleType = styles[Math.floor(Math.random() * styles.length)];

  // Get random color variant from that style
  const styleVariants =
    ANIMALS_DUCK[randomStyleType as keyof typeof ANIMALS_DUCK];
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
  faceStyle?: AnimalDuckType; // Optional specific face style
  zOffset?: number; // Optional Z offset to position the face relative to the character
  chanceOfNoAnimal?: number; // Percentage chance (0-100) that no face accessory will be shown
  onAnimationComplete?: (animation: CharacterAnimationType) => void;
}
